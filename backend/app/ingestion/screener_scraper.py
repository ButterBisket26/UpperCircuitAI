import asyncio
import logging
import re
from typing import Dict, Any, Optional
from datetime import date
import httpx
from html.parser import HTMLParser

logger = logging.getLogger(__name__)

class ScreenerHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.current_link = None
        self.current_text_parts = []
        self.links = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == "a" and "href" in attrs_dict:
            self.current_link = attrs_dict["href"]
            self.current_text_parts = []

    def handle_endtag(self, tag):
        if tag == "a" and self.current_link:
            link_text = "".join(self.current_text_parts).strip()
            # Clean up newlines and excessive whitespace
            link_text = re.sub(r'\s+', ' ', link_text)
            self.links.append((link_text, self.current_link))
            self.current_link = None

    def handle_data(self, data):
        if self.current_link is not None:
            self.current_text_parts.append(data)

# Static mappings for common mismatches on Screener.in
SCREENER_TICKER_ALIASES = {
    "LTIM": "LTM",
    "LTIMINDTREE": "LTM",
}

async def scrape_screener_filing(
    ticker: str,
    fiscal_period: str
) -> Optional[Dict[str, Any]]:
    """
    Scrapes annual report PDF URLs from Screener.in for a given ticker and fiscal period.
    Uses the Screener Search API to resolve non-matching ticker codes.
    
    Args:
        ticker: The stock ticker (e.g. INFY, ITC)
        fiscal_period: e.g. 'FY25', 'FY24'
        
    Returns:
        Dict containing filing metadata, or None if not found.
    """
    # 1. Clean up ticker: strip exchange suffixes (.NS, .BO, :NS, :BO, etc.)
    # but preserve special characters like & and -
    ticker_upper = ticker.strip().upper()
    ticker_clean = re.sub(r'[\.:\s]+(NS|BO|NSE|BSE)$', '', ticker_upper)
    
    # 2. Apply static alias mapping if any
    ticker_clean = SCREENER_TICKER_ALIASES.get(ticker_clean, ticker_clean)
    
    period_upper = fiscal_period.strip().upper()
    
    # Extract year digits (e.g., 'FY25' -> '25')
    year_digits = re.sub(r'\D', '', period_upper)
    if not year_digits:
        logger.error(f"Screener Scraper: Could not extract year digits from period '{fiscal_period}'")
        return None
        
    if len(year_digits) == 2:
        year_four_digit = f"20{year_digits}"
    elif len(year_digits) == 4:
        year_four_digit = year_digits
    else:
        logger.error(f"Screener Scraper: Invalid year digits '{year_digits}' extracted from '{fiscal_period}'")
        return None
        
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9"
    }
    
    company_name = f"{ticker_clean} Limited"
        
    # 3. Try loading consolidated and standalone urls sequentially
    paths_to_try = [
        f"/company/{ticker_clean}/consolidated/",
        f"/company/{ticker_clean}/"
    ]
        
    max_retries = 3
    
    for path in paths_to_try:
        url = f"https://www.screener.in{path}"
        if not url.startswith("http"):
            url = f"https://www.screener.in{url}"
            
        logger.info(f"Screener Scraper: Querying documents page for {ticker_clean} at {url}...")
        
        delay = 1.0
        async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=30.0) as client:
            for attempt in range(max_retries):
                try:
                    resp = await client.get(url)
                    if resp.status_code == 429:
                        logger.warning(f"Screener Scraper: Rate limited (429). Retrying in {delay}s...")
                        await asyncio.sleep(delay)
                        delay *= 2
                        continue
                        
                    if resp.status_code == 404:
                        logger.warning(f"Screener Scraper: Page not found (404) at {url}. Trying next path.")
                        break
                        
                    resp.raise_for_status()
                    
                    # Parse HTML content
                    parser = ScreenerHTMLParser()
                    parser.feed(resp.text)
                    
                    # Search for matching annual report
                    target_phrase = f"Financial Year {year_four_digit}"
                    
                    pdf_url = None
                    for text, href in parser.links:
                        if target_phrase in text:
                            pdf_url = href
                            break
                            
                    # Alternative loose check if no exact phrase match
                    if not pdf_url:
                        for text, href in parser.links:
                            if "Financial Year" in text and year_four_digit in text:
                                pdf_url = href
                                break
                                
                    if pdf_url:
                        # Resolve relative URLs if any
                        if not pdf_url.startswith("http"):
                            if pdf_url.startswith("/"):
                                pdf_url = f"https://www.screener.in{pdf_url}"
                            else:
                                pdf_url = f"https://www.screener.in/{pdf_url}"
                                
                        logger.info(f"Screener Scraper: Successfully found annual report for {ticker_clean} ({fiscal_period}): {pdf_url}")
                        
                        return {
                            "ticker": ticker_clean,
                            "company_name": company_name,
                            "report_type": "annual",
                            "fiscal_period": period_upper,
                            "pdf_url": pdf_url,
                            "filing_date": date.today()
                        }
                    
                    logger.warning(f"Screener Scraper: No annual report matching {target_phrase} found on page {url}")
                    break # Break retry loop, check next path
                    
                except Exception as e:
                    logger.error(f"Screener Scraper attempt {attempt + 1} failed for {url}: {e}")
                    if attempt == max_retries - 1:
                        break # Try next path
                    await asyncio.sleep(delay)
                    delay *= 2
                    
    logger.error(f"Screener Scraper: Failed to find annual report for {ticker} ({fiscal_period}) after trying all options.")
    return None
