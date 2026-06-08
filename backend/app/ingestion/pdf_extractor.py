import os
import tempfile
import logging
from typing import List, Dict, Any
import httpx
import fitz  # PyMuPDF
import pdfplumber

logger = logging.getLogger(__name__)

def convert_table_to_markdown(table_data: List[List[Any]]) -> str:
    """
    Converts a table (list of list of cells) into markdown/pipe-delimited text.
    
    Args:
        table_data: A matrix representing the rows and columns of the table.
        
    Returns:
        A formatted markdown string representation of the table.
    """
    rows = []
    for r in table_data:
        if not r:
            continue
        # Replace newlines in cell content with spaces to keep it single-line in tables
        clean_row = [str(cell or "").strip().replace("\n", " ") for cell in r]
        # Form pipe-delimited row
        rows.append("| " + " | ".join(clean_row) + " |")
        
    if not rows:
        return ""
        
    # Generate a markdown table separator if we have at least one row
    col_count = len(table_data[0])
    separator = "|" + " --- |" * col_count
    
    # Insert separator after the header row (if it exists)
    if len(rows) > 1:
        rows.insert(1, separator)
        
    return "\n".join(rows)

async def extract_pdf_content(file_source: str) -> List[Dict[str, Any]]:
    """
    Downloads a PDF if a URL is provided, then extracts page-by-page text and tables.
    
    Args:
        file_source: An HTTP(S) URL or a local absolute path to the PDF.
        
    Returns:
        List of dicts: {"page_number": int, "content": str, "content_type": "text" | "table"}
    """
    temp_path = None
    if file_source.startswith("http://") or file_source.startswith("https://"):
        logger.info(f"PDF Extractor: Downloading PDF from URL: {file_source}")
        # Create temp file
        fd, temp_path = tempfile.mkstemp(suffix=".pdf")
        os.close(fd)
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=120.0) as client:
            resp = await client.get(file_source)
            resp.raise_for_status()
            with open(temp_path, "wb") as f:
                f.write(resp.content)
        file_path = temp_path
    else:
        file_path = file_source
        if not os.path.exists(file_path):
            logger.error(f"PDF Extractor: Local file not found: {file_path}")
            raise FileNotFoundError(f"Local file not found: {file_path}")
            
    extracted_elements: List[Dict[str, Any]] = []
    
    try:
        # Step 1: Open PDF with pdfplumber to find tables
        logger.info(f"PDF Extractor: Opening with pdfplumber to extract tables from: {file_path}")
        with pdfplumber.open(file_path) as pdf:
            for i, page in enumerate(pdf.pages):
                page_num = i + 1
                tables = page.find_tables()
                if tables:
                    for t in tables:
                        table_data = t.extract()
                        if table_data and len(table_data) > 0:
                            md_table = convert_table_to_markdown(table_data)
                            if md_table.strip():
                                extracted_elements.append({
                                    "page_number": page_num,
                                    "content": md_table,
                                    "content_type": "table"
                                })
                                logger.info(f"PDF Extractor: Table extracted on page {page_num}")
                                
        # Step 2: Open PDF with PyMuPDF to extract text
        logger.info(f"PDF Extractor: Opening with PyMuPDF to extract text from: {file_path}")
        doc = fitz.open(file_path)
        for i, page in enumerate(doc):
            page_num = i + 1
            text = page.get_text()
            if text.strip():
                extracted_elements.append({
                    "page_number": page_num,
                    "content": text.strip(),
                    "content_type": "text"
                })
        doc.close()
        
    except Exception as e:
        logger.error(f"PDF Extractor: Failed to parse PDF: {e}", exc_info=True)
        raise e
        
    finally:
        # Clean up temp file
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
                logger.info(f"PDF Extractor: Cleaned up temporary file: {temp_path}")
            except Exception as e:
                logger.error(f"PDF Extractor: Error removing temp file {temp_path}: {e}")
                
    # Sort by page number and keep order (tables first then text, or vice versa)
    extracted_elements.sort(key=lambda x: (x["page_number"], 0 if x["content_type"] == "table" else 1))
    return extracted_elements
