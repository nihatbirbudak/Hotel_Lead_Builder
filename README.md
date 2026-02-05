# Hotel Lead Builder

A full-stack application for discovering hotel websites and extracting contact information (emails) from Turkish tourism facilities.

## Features

- **Excel/JSON Upload**: Import facility data from TGA (Turkish Tourism Agency) exports
- **Automated Website Discovery**: Find hotel websites using multiple strategies:
  - Smart domain guessing (hotel name → domain patterns)
  - DuckDuckGo search integration
  - Alternative TLD checking (.com, .com.tr, .net, .org)
- **Email Crawler**: Extract emails from discovered websites with obfuscation detection
- **DNS Pre-check**: Fast DNS validation before HTTP requests (95%+ filtering)
- **Smart Caching**: SQLite-based caching with 7-day TTL
- **Circuit Breaker Pattern**: Prevents cascading failures from rate limiting
- **Real-time Progress**: WebSocket-based job progress tracking
- **4-Tab Interface**: Organize facilities by status (Pending, Not Found, Has Website, Has Email)

## Tech Stack

### Backend
- **FastAPI** - Modern Python web framework
- **SQLAlchemy** - ORM for SQLite database
- **aiohttp** - Async HTTP client
- **dnspython** - DNS resolution
- **BeautifulSoup** - HTML parsing

### Frontend
- **Next.js 14** - React framework with App Router
- **React Query** - Data fetching and caching
- **TailwindCSS** - Utility-first CSS
- **Lucide Icons** - Icon library

## Project Structure

```
Hotel_Lead_Builder/
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI routes & job management
│   │   ├── models.py         # SQLAlchemy models
│   │   ├── schemas.py        # Pydantic schemas
│   │   ├── database.py       # Database configuration
│   │   └── services/
│   │       ├── discovery.py  # Website discovery logic
│   │       ├── crawler.py    # Email extraction
│   │       ├── cache.py      # SQLite caching
│   │       ├── dns_check.py  # DNS pre-validation
│   │       └── circuit_breaker.py
│   └── requirements.txt
├── frontend/
│   ├── app/
│   │   ├── page.tsx          # Main page with tabs
│   │   ├── layout.tsx
│   │   └── jobs/             # Job history pages
│   ├── components/
│   │   ├── HotelTable.tsx    # Facility table
│   │   ├── JobControl.tsx    # Start/stop jobs
│   │   ├── UploadSection.tsx # File upload
│   │   └── LogPanel.tsx      # Real-time logs
│   └── lib/
│       └── api.ts            # API client
└── data/                     # SQLite databases
```

## Installation

### Prerequisites
- Python 3.11+
- Node.js 18+

### Backend Setup

```bash
cd backend
pip install -r requirements.txt
```

### Frontend Setup

```bash
cd frontend
npm install
```

## Running the Application

### Start Backend (Port 8000)

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Start Frontend (Port 3001)

```bash
cd frontend
npm run dev -- -p 3001
```

Open [http://localhost:3001](http://localhost:3001) in your browser.

## Usage

1. **Upload Data**: Import an Excel or JSON file with facility information
2. **Select Facilities**: Choose which facilities to process
3. **Start Discovery Job**: Click "Start Discovery" to find websites
4. **Start Email Crawl**: After websites are found, crawl for emails
5. **Export Results**: Download results as Excel/CSV

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/facilities` | List facilities with filters |
| GET | `/api/facilities/stats` | Get counts by status |
| POST | `/api/upload` | Upload facility data |
| POST | `/api/jobs/discovery` | Start website discovery |
| POST | `/api/jobs/email-crawl` | Start email crawling |
| GET | `/api/jobs/{id}` | Get job status |
| GET | `/api/jobs/{id}/logs` | Get job logs |

## Discovery Algorithm

1. **Domain Generation**: Generate ~160 candidate URLs from hotel name
   - Name variations (with/without spaces, Turkish chars)
   - Common patterns (hotelname.com, hotelnamehotel.com)
   - Multiple TLDs (.com, .com.tr, .net, .org, .tr)

2. **DNS Pre-check**: Batch DNS resolution filters 95%+ non-existent domains

3. **HTTP Validation**: Check remaining domains for:
   - Valid HTTP response
   - Content containing hotel-related keywords
   - Domain-name similarity scoring

4. **DuckDuckGo Search**: If no high-confidence match, search the web

5. **Scoring**: Validate results with confidence scoring (0-100)

## Configuration

Environment variables (optional):

```env
DATABASE_URL=sqlite:///./data/facilities.db
CACHE_TTL_DAYS=7
MAX_CONCURRENT_REQUESTS=10
```

## License

MIT

## Contributing

Pull requests are welcome. For major changes, please open an issue first.
