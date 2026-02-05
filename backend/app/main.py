from fastapi import FastAPI, Depends, UploadFile, File, BackgroundTasks, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional, List
import json
import logging
import time
from datetime import datetime
import pandas as pd
from fastapi.responses import FileResponse
import tempfile
import shutil
import random
from concurrent.futures import ThreadPoolExecutor, as_completed

from .database import engine, Base, get_db
from .models import Facility, Job, JobLog
from .schemas import FacilityResponse, JobResponse, JobLogResponse, DiscoveryRequest, EmailRequest, FacilityUpload
from .services import discovery, crawler

# Init DB
Base.metadata.create_all(bind=engine)

# Setup Logger
logger = logging.getLogger("uvicorn")

# Global Debug Storage (Temporary)
DEBUG_LAST_UPLOAD = {
    "detected_format": "none",
    "sample_keys": [],
    "sample_row": {}
}

app = FastAPI(title="Hotel Lead Builder")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,  # <-- önemli
    allow_methods=["*"],
    allow_headers=["*"],
)

def pick(row: dict, keys: list, default=None):
    """Helper to pick first available non-empty key from row"""
    for k in keys:
        val = row.get(k)
        if val:
            return str(val).strip()
    return default

def normalize_belge_turu(raw_value: str) -> str:
    """
    Normalize BelgeTuru (document type) to 5 canonical categories.
    Maps raw JSON values to standard categories.
    """
    if not raw_value:
        return "BASİT KONAKLAMA"
    
    raw = str(raw_value).strip()
    
    # Canonical categories (from raw_tga.txt analysis)
    canonical_1 = "BASİT KONAKLAMA" 
    canonical_2 = "Turizm İşletmesi Belgesi"
    canonical_3 = "PLAJ İŞLETMESİ"
    canonical_4 = "Turizm Yatırımı Belgesi"
    canonical_5 = "Kısmi Turizm İşletmesi Belgesi"
    
    # Direct 1:1 mapping from raw_tga.json values
    if raw == canonical_1:
        return canonical_1
    elif raw == canonical_2:
        return canonical_2
    elif raw == canonical_3:
        return canonical_3
    elif raw == canonical_4:
        return canonical_4
    elif raw == canonical_5:
        return canonical_5
    
    # Fallback: keyword matching for edge cases or alternate encodings
    raw_lower = raw.lower()
    if "basit" in raw_lower:
        return canonical_1
    elif "yatir" in raw_lower:
        return canonical_4
    elif ("kismi" in raw_lower or "kısmi" in raw_lower):
        return canonical_5
    elif "plaj" in raw_lower:
        return canonical_3
    elif "turizm" in raw_lower and ("isletmesi" in raw_lower or "işletmesi" in raw_lower):
        return canonical_2
    
    # Default fallback
    logger.warning(f"[NORMALIZE] Unknown BelgeTuru: {raw}, defaulting to {canonical_1}")
    return canonical_1

# --- TASKS ---

def run_discovery_task(job_id: str, uids: List[str], mode: str, rate_limit: float, db: Session):
    """
    Optimized discovery task with batch processing and rate limiting.
    - Batch size: 500 items per worker round
    - Concurrency: 3 workers
    - Rate limit: random 0.8-1.8 sec between requests
    """
    from .database import SessionLocal
    
    job = db.query(Job).filter(Job.id == job_id).first()
    job.status = "running"
    db.commit()

    if mode == "selected" and uids:
        targets = db.query(Facility).filter(Facility.id.in_(uids)).all()
    else:
        # Default: Process missing websites
        targets = db.query(Facility).filter(
            or_(Facility.website == None, Facility.website == ""),
            Facility.website_status != "not_found"
        ).all()
    
    job.total_items = len(targets)
    db.commit()
    
    logger.info(f"[DISCOVERY] Starting batch process for {len(targets)} facilities")
    
    # Batch configuration
    batch_size = 500
    max_workers = 3
    
    def process_facility(facility_id):
        """Process single facility with rate limiting."""
        db_session = SessionLocal()
        try:
            facility = db_session.query(Facility).filter(Facility.id == facility_id).first()
            if not facility:
                return None
            
            # Random rate limit (0.8-1.8 sec)
            delay = random.uniform(0.8, 1.8)
            time.sleep(delay)
            
            logger.info(f"[DISCOVERY] Processing: {facility.name} ({facility.sehir})")

            # Log current item for live UI updates
            db_session.add(JobLog(job_id=job_id, level="INFO", message=f"Processing: {facility.name} ({facility.sehir})"))
            db_session.commit()
            
            # Search for website
            result = discovery.find_website(facility.name, facility.sehir)
            
            if result and result.get('url'):
                facility.website = result['url']
                facility.website_score = result['score']
                facility.website_status = "found"
                facility.website_source = result.get('source', 'unknown')
                status = "SUCCESS"
                message = f"Found: {result['url']} (score: {result['score']:.0f}, source: {result.get('source', 'unknown')})"
                logger.info(f"[DISCOVERY] SUCCESS: {facility.name} -> {result['url']}")
            else:
                facility.website_status = "not_found"
                reason = result.get('reason') if result else "unknown"
                status = "WARNING"
                message = f"Not found: {facility.name} | reason: {reason}"
                logger.warning(f"[DISCOVERY] NOT FOUND: {facility.name}")
            
            # Save result
            db_session.add(facility)
            
            # Log
            log = JobLog(job_id=job_id, level=status, message=message)
            db_session.add(log)
            db_session.commit()
            
            return {"facility_id": facility_id, "status": status}
                
        except Exception as e:
            logger.error(f"[DISCOVERY] Error for {facility_id}: {str(e)}")
            try:
                log = JobLog(job_id=job_id, level="ERROR", message=f"Error: {str(e)}")
                db_session.add(log)
                db_session.commit()
            except:
                pass
            return {"facility_id": facility_id, "status": "ERROR"}
        finally:
            db_session.close()
    
    # Process in batches with thread pool
    facility_ids = [f.id for f in targets]
    processed = 0
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {}
        
        for fid in facility_ids:
            future = executor.submit(process_facility, fid)
            futures[future] = fid
        
        for future in as_completed(futures):
            # Check if job is cancelled before processing next result
            job_check = db.query(Job).filter(Job.id == job_id).first()
            if job_check and job_check.status == "cancelled":
                logger.info(f"[DISCOVERY] Job {job_id} cancelled, stopping task")
                # Cancel remaining futures
                for f in futures:
                    f.cancel()
                break
            
            try:
                result = future.result()
                if result:
                    processed += 1
                    # Update job progress
                    job = db.query(Job).filter(Job.id == job_id).first()
                    job.processed_items = processed
                    db.commit()
            except Exception as e:
                logger.error(f"[DISCOVERY] Future error: {str(e)}")
    
    # Mark as completed or cancelled
    job = db.query(Job).filter(Job.id == job_id).first()
    if job.status != "cancelled":
        job.status = "completed"
    job.finished_at = datetime.utcnow()
    db.commit()
    
    logger.info(f"[DISCOVERY] Task completed. Processed: {processed}/{len(targets)}")

def run_email_task(job_id: str, uids: List[str], mode: str, max_pages: int, rate_limit: float, db: Session):
    job = db.query(Job).filter(Job.id == job_id).first()
    job.status = "running"
    db.commit()

    if mode == "selected" and uids:
        targets = db.query(Facility).filter(Facility.id.in_(uids)).all()
    else:
        targets = db.query(Facility).filter(
            Facility.website != None,
            or_(Facility.email == None, Facility.email == ""),
            Facility.email_status != "not_found"
        ).all()
    
    job.total_items = len(targets)
    db.commit()
    
    for facility in targets:
        # Check if job is cancelled
        job_check = db.query(Job).filter(Job.id == job_id).first()
        if job_check and job_check.status == "cancelled":
            logger.info(f"[EMAIL_CRAWL] Job {job_id} cancelled, stopping task")
            break
        
        if not facility.website:
             job.processed_items += 1
             continue

        try:
            log = JobLog(job_id=job.id, level="INFO", message=f"Crawling {facility.website}...")
            db.add(log)
            db.commit()

            time.sleep(max(0.1, rate_limit))
            
            email = crawler.crawl_for_email(facility.website, max_pages=max_pages)
            
            if email:
                facility.email = email
                facility.email_status = "found"
                facility.email_source = "scrape"
                db.add(JobLog(job_id=job.id, level="SUCCESS", message=f"Found email: {email}"))
            else:
                facility.email_status = "not_found"
                db.add(JobLog(job_id=job.id, level="WARNING", message="No email found."))
                
            job.processed_items += 1
            db.commit()
            
        except Exception as e:
            job.error_count += 1
            db.add(JobLog(job_id=job.id, level="ERROR", message=str(e)))
            db.commit()
            
    job_final = db.query(Job).filter(Job.id == job_id).first()
    if job_final.status != "cancelled":
        job_final.status = "completed"
    job_final.finished_at = datetime.utcnow()
    db.commit()

# --- ENDPOINTS ---

@app.post("/api/upload")
async def upload_file(
    data: List[dict] = Body(...),
    reset_db: bool = False,
    db: Session = Depends(get_db)
):
    """
    Upload facilities (raw otel data).
    - POST JSON array directly as body
    - Example: POST /api/upload?reset_db=true with JSON list in body
    """
    global DEBUG_LAST_UPLOAD
    
    if reset_db:
        # Drop tables to ensure schema changes are applied if model changed
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
    
    # data is request body JSON list
    rows = data if data else []
    
    try:
        # --- DEBUG LOGGING ---
        logger.info(f"UPLOAD DEBUG: data type={type(data)}, data length={len(data) if data else 0}")
        
        if rows:
            logger.info(f"UPLOAD DEBUG: rows count={len(rows)}")
            sample = rows[0]
            keys = list(sample.keys())
            sample_pretty = json.dumps(sample, indent=2, ensure_ascii=False)
            if len(sample_pretty) > 1500:
                sample_pretty = sample_pretty[:1500] + "...(truncated)"
            
            logger.info(f"UPLOAD DEBUG: First row keys: {keys}")

            DEBUG_LAST_UPLOAD = {
                "sample_keys": keys,
                "sample_row": sample
            }
        else:
            logger.warning(f"UPLOAD DEBUG: rows is empty!")
        
        inserted = 0
        updated = 0
        sample_mapped = None

        for row in rows:
            # Composite ID strategy
            raw_id = str(row.get("BelgeNo") or row.get("id") or row.get("ID") or row.get("Id") or row.get("raw_id") or "")
            
            # Robust Mapping
            name = pick(row, ["TesisAdi", "adi", "ADI", "tesis_adi", "name"], "Bilinmeyen Tesis")
            sehir = pick(row, ["Sehir", "Şehir", "Il", "İl", "city", "il"], "Bilinmiyor")
            ilce = pick(row, ["Ilce", "İlçe", "district", "ilce"], "Bilinmiyor")
            typ_raw = pick(row, ["BelgeTuru", "belge_turu", "tur", "TUR", "type"], "")
            typ = normalize_belge_turu(typ_raw)  # Normalize to canonical category
            addr = pick(row, ["adres", "ADRES", "address"], "")

            # Upsert
            existing = db.query(Facility).filter(Facility.raw_id == raw_id).first() if raw_id else None
            
            if existing:
                existing.name = name
                existing.sehir = sehir
                existing.ilce = ilce
                existing.type = typ
                existing.address = addr
                updated += 1
                if not sample_mapped:
                    sample_mapped = {"raw_id": raw_id, "name": name, "sehir": sehir, "ilce": ilce}
            else:
                facility = Facility(
                    raw_id=raw_id,
                    name=name,
                    sehir=sehir,
                    ilce=ilce,
                    type=typ,
                    address=addr
                )
                db.add(facility)
                inserted += 1
                if not sample_mapped:
                    sample_mapped = {"raw_id": raw_id, "name": name, "sehir": sehir, "ilce": ilce}
        
        db.commit()
        return {
            "status": "success", 
            "reset_applied": reset_db,
            "total_rows": len(rows),
            "inserted": inserted,
            "updated": updated,
            "sample_mapped_row": sample_mapped,
            "message": f"Imported {inserted} new facilities"
        }
        
    except json.JSONDecodeError:
        raise HTTPException(400, "Invalid JSON")

@app.get("/api/debug/sample-row")
def get_debug_sample():
    return DEBUG_LAST_UPLOAD

@app.get("/api/facilities", response_model=dict)
def get_facilities(
    page: int = 1, 
    limit: int = 50, 
    city: Optional[str] = None, 
    search: Optional[str] = None,
    type: Optional[str] = None,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get facilities with optional filters.
    
    status_filter options:
    - "pending": Henüz aranmamış tesisler
    - "not_found": Aranmış ama website bulunamayan tesisler
    - "has_website": Website bulunan tesisler (email yok)
    - "has_email": Hem website hem email bulunan tesisler
    - None: Tüm tesisler
    """
    query = db.query(Facility)
    
    # Status filter (tab-based filtering)
    if status_filter == "pending":
        # Henüz aranmamış (website boş VE status not_found değil)
        query = query.filter(
            or_(Facility.website == None, Facility.website == ""),
            or_(Facility.website_status == None, Facility.website_status == "", Facility.website_status == "pending")
        )
    elif status_filter == "not_found":
        # Arandı ama bulunamadı
        query = query.filter(Facility.website_status == "not_found")
    elif status_filter == "has_website":
        # Website var, email yok
        query = query.filter(
            Facility.website != None,
            Facility.website != "",
            or_(Facility.email == None, Facility.email == "")
        )
    elif status_filter == "has_email":
        # Hem website hem email var
        query = query.filter(
            Facility.website != None,
            Facility.website != "",
            Facility.email != None,
            Facility.email != ""
        )
    
    # Filter by sehir (DB column) using city param (API)
    if city:
        query = query.filter(Facility.sehir == city)
    
    # Filter by type (Belge Türü)
    if type:
        query = query.filter(Facility.type == type)
    
    if search:
        search_fmt = f"%{search}%"
        # Search in name and sehir
        query = query.filter(or_(Facility.name.ilike(search_fmt), Facility.sehir.ilike(search_fmt)))
        
    total = query.count()
    items = query.offset((page - 1) * limit).limit(limit).all()
    
    # Convert ORM objects to Pydantic models
    facility_data = [FacilityResponse.model_validate(item) for item in items]
    
    return {"data": facility_data, "total": total, "page": page}

@app.get("/api/facilities/stats")
def get_facilities_stats(db: Session = Depends(get_db)):
    """Get counts for each category: pending, not_found, has_website, has_email"""
    
    # Total count
    total = db.query(Facility).count()
    
    # Pending: Henüz aranmamış (website boş VE status not_found değil)
    pending = db.query(Facility).filter(
        or_(Facility.website == None, Facility.website == ""),
        or_(Facility.website_status == None, Facility.website_status == "", Facility.website_status == "pending")
    ).count()
    
    # Not found: Arandı ama bulunamadı
    not_found = db.query(Facility).filter(
        Facility.website_status == "not_found"
    ).count()
    
    # Has website but no email
    has_website = db.query(Facility).filter(
        Facility.website != None,
        Facility.website != "",
        or_(Facility.email == None, Facility.email == "")
    ).count()
    
    # Has both website and email
    has_email = db.query(Facility).filter(
        Facility.website != None,
        Facility.website != "",
        Facility.email != None,
        Facility.email != ""
    ).count()
    
    return {
        "total": total,
        "pending": pending,
        "not_found": not_found,
        "has_website": has_website,
        "has_email": has_email
    }

@app.get("/api/filters/types")
def get_document_types(db: Session = Depends(get_db)):
    """Get all unique Belge Türü values with counts"""
    from sqlalchemy import func
    
    results = db.query(
        Facility.type, 
        func.count(Facility.id).label('count')
    ).filter(
        Facility.type.isnot(None)
    ).group_by(
        Facility.type
    ).order_by(
        func.count(Facility.id).desc()
    ).all()
    
    return {
        "types": [
            {"name": r[0], "count": r[1]} 
            for r in results
        ]
    }

@app.post("/api/jobs/website-discovery")
def start_discovery(req: DiscoveryRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    job = Job(job_type="discovery", status="queued")
    db.add(job)
    db.commit()
    db.refresh(job)
    
    background_tasks.add_task(run_discovery_task, job.id, req.uids, req.mode, req.settings.rate_limit, db)
    return {"job_id": job.id}

@app.post("/api/jobs/email-crawl")
def start_crawl(req: EmailRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    job = Job(job_type="email_crawl", status="queued")
    db.add(job)
    db.commit()
    db.refresh(job)
    
    background_tasks.add_task(run_email_task, job.id, req.uids, req.mode, 10, req.settings.rate_limit, db)
    return {"job_id": job.id}

@app.get("/api/jobs", response_model=dict)
def list_jobs(db: Session = Depends(get_db)):
    # Query: running jobs first, then by creation date desc
    from sqlalchemy import case
    status_order = case(
        (Job.status == "running", 0),
        (Job.status == "queued", 1),
        else_=2
    )
    jobs = db.query(Job).order_by(status_order, Job.created_at.desc()).limit(100).all()
    results = []

    for job in jobs:
        websites_found = db.query(JobLog).filter(
            JobLog.job_id == job.id,
            JobLog.level == "SUCCESS",
            JobLog.message.like("Found:%")
        ).count()
        websites_not_found = db.query(JobLog).filter(
            JobLog.job_id == job.id,
            JobLog.level == "WARNING",
            JobLog.message.like("Not found:%")
        ).count()

        elapsed = 0
        if job.created_at:
            end_time = job.finished_at if job.finished_at else datetime.now()
            elapsed = int((end_time - job.created_at).total_seconds())

        results.append({
            "job_id": job.id,
            "job_type": job.job_type,
            "status": job.status,
            "total": job.total_items,
            "done": job.processed_items,
            "errors": job.error_count,
            "websites_found": websites_found,
            "websites_not_found": websites_not_found,
            "success_rate": round((websites_found / max(job.processed_items, 1)) * 100, 1),
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "finished_at": job.finished_at.isoformat() if job.finished_at else None,
            "elapsed_seconds": elapsed
        })

    return {"jobs": results}

@app.delete("/api/jobs/{job_id}", response_model=dict)
def cancel_job(job_id: str, db: Session = Depends(get_db)):
    """Cancel a running or queued job"""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(404, "Job not found")
    
    if job.status in ["completed", "failed", "cancelled"]:
        raise HTTPException(400, f"Cannot cancel job with status: {job.status}")
    
    # Mark as cancelled
    job.status = "cancelled"
    job.finished_at = datetime.utcnow()
    db.commit()
    
    logger.info(f"[JOB_CANCEL] Job {job_id} marked as cancelled")
    
    return {
        "success": True,
        "job_id": job_id,
        "status": "cancelled",
        "message": "Job cancellation requested. The job will stop after current item."
    }

@app.get("/api/jobs/{job_id}", response_model=dict)
def get_job_status(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(404, "Job not found")
    
    # Count per-job results using logs
    websites_found = db.query(JobLog).filter(
        JobLog.job_id == job_id,
        JobLog.level == "SUCCESS",
        JobLog.message.like("Found:%")
    ).count()
    websites_not_found = db.query(JobLog).filter(
        JobLog.job_id == job_id,
        JobLog.level == "WARNING",
        JobLog.message.like("Not found:%")
    ).count()
    
    # Fetch logs ordered by time
    log_rows = db.query(JobLog).filter(
        JobLog.job_id == job_id
    ).order_by(JobLog.timestamp.desc()).limit(200).all()
    logs = [JobLogResponse.model_validate(log) for log in reversed(log_rows)]

    # Calculate elapsed time using first log as start if available
    elapsed = 0
    start_time = None
    if log_rows:
        start_time = log_rows[-1].timestamp
    if not start_time and job.created_at:
        start_time = job.created_at
    if start_time:
        end_time = job.finished_at if job.finished_at else datetime.now()
        elapsed = int((end_time - start_time).total_seconds())

    # Estimate remaining time using recent completion logs
    estimated_remaining = 0
    completion_logs = db.query(JobLog).filter(
        JobLog.job_id == job_id,
        JobLog.level.in_(["SUCCESS", "WARNING", "ERROR"])
    ).order_by(JobLog.timestamp.desc()).limit(20).all()
    if len(completion_logs) >= 2 and job.total_items > job.processed_items:
        newest = completion_logs[0].timestamp
        oldest = completion_logs[-1].timestamp
        delta = (newest - oldest).total_seconds()
        avg_time_per_item = max(delta / (len(completion_logs) - 1), 0.1)
        remaining_items = job.total_items - job.processed_items
        estimated_remaining = int(avg_time_per_item * remaining_items)
    elif job.processed_items > 0 and job.total_items > job.processed_items:
        avg_time_per_item = max(elapsed / job.processed_items, 0.1)
        remaining_items = job.total_items - job.processed_items
        estimated_remaining = int(avg_time_per_item * remaining_items)

    # Current action and last results
    current_action = None
    current_item = None
    last_success = None
    last_warning = None
    for row in log_rows:
        if not current_action and row.message.startswith("Processing:"):
            current_action = "processing"
            current_item = row.message.replace("Processing:", "").strip()
        if not last_success and row.level == "SUCCESS":
            last_success = row.message
        if not last_warning and row.level == "WARNING":
            last_warning = row.message
        if current_action and last_success and last_warning:
            break

    reason_counts = {}
    for log in logs:
        if log.level == "WARNING" and "reason:" in log.message:
            reason = log.message.split("reason:", 1)[1].strip()
            reason_counts[reason] = reason_counts.get(reason, 0) + 1

    return {
        "job_id": job.id,
        "status": job.status,
        "total": job.total_items,
        "done": job.processed_items,
        "errors": job.error_count,
        "websites_found": websites_found,
        "websites_not_found": websites_not_found,
        "success_rate": round((websites_found / max(job.processed_items, 1)) * 100, 1),
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
        "elapsed_seconds": elapsed,
        "estimated_remaining_seconds": estimated_remaining,
        "logs": logs,
        "current_action": current_action,
        "current_item": current_item,
        "last_success": last_success,
        "last_warning": last_warning,
        "not_found_reasons": [
            {"reason": key, "count": value}
            for key, value in sorted(reason_counts.items(), key=lambda x: x[1], reverse=True)
        ]
    }

@app.get("/api/export/csv")
def export_csv(city: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Facility)
    if city:
        query = query.filter(Facility.sehir == city)
        
    df = pd.read_sql(query.statement, db.bind)
    
    # Create temp file
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
    df.to_csv(tmp.name, index=False)
    
    return FileResponse(tmp.name, filename="facilities_export.csv", media_type="text/csv")

@app.get("/api/export/sqlite")
def export_sqlite():
    return FileResponse("../data/leads.db", filename="leads.db", media_type="application/vnd.sqlite3")
