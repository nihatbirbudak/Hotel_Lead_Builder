import { GoogleGenAI } from "@google/genai";
import { CORS_PROXY } from '../constants';

// Initialize Gemini Client
const getGeminiClient = () => {
  const apiKey = process.env.API_KEY;
  if (!apiKey) {
    throw new Error("API Anahtarı bulunamadı.");
  }
  return new GoogleGenAI({ apiKey });
};

/**
 * Strategy 1: Use Gemini with Google Search Grounding (Highly Recommended)
 * This bypasses CORS and parsing issues.
 */
export const findWebsiteWithGemini = async (hotelName: string, city: string): Promise<string | null> => {
  try {
    const client = getGeminiClient();
    const response = await client.models.generateContent({
      model: 'gemini-3-flash-preview',
      contents: `Find the official website for the hotel "${hotelName}" located in "${city}", Turkey. Return ONLY the URL starting with http/https. If not found, return NULL.`,
      config: {
        tools: [{ googleSearch: {} }],
        temperature: 0.1
      }
    });

    const text = response.text?.trim() || '';
    
    // Extract URL from text if the model is chatty
    const urlMatch = text.match(/https?:\/\/[^\s]+/);
    if (urlMatch) return urlMatch[0];
    
    // Check grounding chunks if text is empty/generic
    const chunks = response.candidates?.[0]?.groundingMetadata?.groundingChunks;
    if (chunks && chunks.length > 0) {
        // Return the first web source
        for(const chunk of chunks) {
            if(chunk.web?.uri) return chunk.web.uri;
        }
    }

    if (text.includes("NULL")) return null;
    return text.startsWith("http") ? text : null;

  } catch (error) {
    console.warn("Gemini Discovery Failed:", error);
    return null;
  }
};

/**
 * Strategy 2: "DuckDuckGo" HTML Scraping via Proxy (As requested, but brittle)
 * Uses a public CORS proxy to fetch DDG HTML results.
 */
export const findWebsiteWithDDG = async (hotelName: string, city: string): Promise<string | null> => {
  try {
    const query = encodeURIComponent(`${hotelName} ${city} resmi web sitesi`);
    const ddgUrl = `https://html.duckduckgo.com/html?q=${query}`;
    const proxyUrl = `${CORS_PROXY}${encodeURIComponent(ddgUrl)}`;

    const response = await fetch(proxyUrl);
    if (!response.ok) throw new Error("Proxy error");
    
    const data = await response.json(); // allorigins returns JSON with 'contents'
    const html = data.contents;

    // Very basic parsing regex to find the first result link in DDG HTML
    // Looking for <a class="result__a" href="...">
    // Note: DDG HTML structure changes, this is a best-effort regex.
    const linkRegex = /class="[^"]*result__a[^"]*" href="([^"]+)"/i;
    const match = html.match(linkRegex);

    if (match && match[1]) {
        // Decode the URL (DDG usually wraps it in /l/?uddg=...)
        let url = match[1];
        if (url.includes('uddg=')) {
            const params = new URLSearchParams(url.split('?')[1]);
            return params.get('uddg');
        }
        return url;
    }
    return null;

  } catch (error) {
    console.warn("DDG Discovery Failed:", error);
    return null;
  }
};


/**
 * Email Discovery
 * 1. Try to fetch the homepage via Proxy.
 * 2. Look for "iletisim" or "contact" links.
 * 3. Scrape emails from those pages.
 */
export const findEmailOnPage = async (url: string): Promise<string | null> => {
  try {
    // Basic normalization
    if (!url.startsWith('http')) url = 'https://' + url;

    // Fetch via Proxy
    const proxyUrl = `${CORS_PROXY}${encodeURIComponent(url)}`;
    const response = await fetch(proxyUrl);
    if (!response.ok) return null;

    const data = await response.json();
    const html = data.contents as string;

    // 1. Look for mailto
    const emailRegex = /([a-zA-Z0-9._-]+@[a-zA-Z0-9._-]+\.[a-zA-Z0-9._-]+)/gi;
    const emails = html.match(emailRegex);

    if (emails && emails.length > 0) {
        // Filter out garbage (images, unrelated generic emails)
        const validEmails = emails.filter(e => !e.endsWith('.png') && !e.endsWith('.jpg') && !e.endsWith('.js'));
        if (validEmails.length > 0) return validEmails[0];
    }

    // 2. If no email, check for contact page link (Basic implementation)
    // In a real crawler, we would fetch the contact page. 
    // For this MVP, we only scan the homepage.

    return null;
  } catch (error) {
    console.warn("Email Scan Failed:", error);
    return null;
  }
};
