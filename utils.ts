import { Hotel } from './types';

// Simple UUID generator
export const uuidv4 = () => {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
};

export const parseTGAFile = (content: string): any[] => {
  try {
    const json = JSON.parse(content);
    // TGA files sometimes have { data: { rows: [...] } } or just [...]
    if (Array.isArray(json)) return json;
    if (json.data && Array.isArray(json.data.rows)) return json.data.rows;
    if (json.rows && Array.isArray(json.rows)) return json.rows;
    // Fallback: try to find the first array in the object
    const keys = Object.keys(json);
    for (const key of keys) {
      if (Array.isArray(json[key])) return json[key];
    }
    throw new Error("Uygun veri formatı bulunamadı.");
  } catch (e) {
    console.error("Parse Error", e);
    throw new Error("JSON parse edilemedi.");
  }
};

export const mapRawDataToHotel = (raw: any): Hotel => {
  return {
    id: uuidv4(),
    rawId: raw.id || raw.ID || raw.Id,
    ad: raw.adi || raw.ADI || raw.tesis_adi || raw.TesisAdi || "Bilinmeyen Tesis",
    il: raw.il || raw.IL || raw.sehir || "Bilinmiyor",
    ilce: raw.ilce || raw.ILCE || "Bilinmiyor",
    sinif: raw.sinif || raw.SINIF || "",
    tur: raw.tur || raw.TUR || raw.belge_turu || "",
    adres: raw.adres || raw.ADRES || "",
    status: 'idle'
  };
};

export const exportToCSV = (hotels: Hotel[]) => {
  const headers = ['ID', 'Tesis Adı', 'Şehir', 'İlçe', 'Tür', 'Website', 'Email', 'Durum'];
  const csvContent = [
    headers.join(','),
    ...hotels.map(h => [
      h.rawId || h.id,
      `"${(h.ad || '').replace(/"/g, '""')}"`,
      h.il,
      h.ilce,
      h.tur,
      h.website || '',
      h.email || '',
      h.status
    ].join(','))
  ].join('\n');

  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement("a");
  const url = URL.createObjectURL(blob);
  link.setAttribute("href", url);
  link.setAttribute("download", `hotel_leads_${new Date().toISOString().slice(0,10)}.csv`);
  link.style.visibility = 'hidden';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
};

export const exportToSQL = (hotels: Hotel[]) => {
  // Generate a .sql dump file content
  let sql = `CREATE TABLE IF NOT EXISTS hotels (
    id TEXT PRIMARY KEY,
    name TEXT,
    city TEXT,
    district TEXT,
    type TEXT,
    website TEXT,
    email TEXT
);\n\n`;

  sql += "INSERT INTO hotels (id, name, city, district, type, website, email) VALUES \n";
  
  const values = hotels.map(h => {
    const sanitize = (str?: string) => str ? `'${str.replace(/'/g, "''")}'` : 'NULL';
    return `(${sanitize(h.rawId?.toString() || h.id)}, ${sanitize(h.ad)}, ${sanitize(h.il)}, ${sanitize(h.ilce)}, ${sanitize(h.tur)}, ${sanitize(h.website)}, ${sanitize(h.email)})`;
  }).join(",\n");

  sql += values + ";";

  const blob = new Blob([sql], { type: 'application/sql;charset=utf-8;' });
  const link = document.createElement("a");
  const url = URL.createObjectURL(blob);
  link.setAttribute("href", url);
  link.setAttribute("download", `hotel_leads_${new Date().toISOString().slice(0,10)}.sql`);
  link.style.visibility = 'hidden';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
};
