import re
import logging
from typing import List, Dict, Any
import httpx
from app.config import settings
from app.generation.prompt_builder import get_system_prompt, build_user_prompt

logger = logging.getLogger(__name__)

def parse_citations(answer: str, context_chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Parses citations from the answer text matching the format:
    [Company | Report Type | Period | Page N]
    
    Matches are linked back to context_chunks to extract a text preview.
    
    Args:
        answer: The generated LLM response.
        context_chunks: List of retrieved chunks.
        
    Returns:
        List of citation dictionaries containing metadata and preview.
    """
    # Regex to capture [Company | Type | Period | Page Num]
    pattern = re.compile(
        r'\[([^\|\]]+)\s*\|\s*([^\|\]]+)\s*\|\s*([^\|\]]+)\s*\|\s*(?:Page\s*)?(\d+)\]', 
        re.IGNORECASE
    )
    matches = pattern.findall(answer)
    
    citations = []
    seen = set()
    
    for match in matches:
        company_raw, report_type_raw, period_raw, page_num_str = match
        company = company_raw.strip()
        report_type = report_type_raw.strip()
        period = period_raw.strip()
        
        try:
            page_number = int(page_num_str.strip())
        except ValueError:
            page_number = 0
            
        citation_key = (company.lower(), report_type.lower(), period.lower(), page_number)
        if citation_key in seen:
            continue
        seen.add(citation_key)
        
        # Look for matching context chunk to extract a text snippet preview
        chunk_preview = "No context preview available."
        for chunk in context_chunks:
            chunk_company = chunk.get("company_name", chunk.get("company", ""))
            chunk_ticker = chunk.get("ticker", "")
            chunk_report = chunk.get("report_type", "")
            chunk_period = chunk.get("fiscal_period", "")
            chunk_page = chunk.get("page_number", 0)
            
            # Fuzzy match company or ticker name and exact page match
            company_match = (
                company.lower() in chunk_company.lower() or 
                company.lower() in chunk_ticker.lower() or 
                chunk_ticker.lower() in company.lower()
            )
            page_match = int(chunk_page) == page_number
            
            if company_match and page_match:
                content = chunk.get("content", "")
                # Clean up snippet size to keep response payload lean
                chunk_preview = content[:200] + "..." if len(content) > 200 else content
                break
                
        citations.append({
            "company": company,
            "report_type": report_type,
            "fiscal_period": period,
            "page_number": page_number,
            "chunk_preview": chunk_preview
        })
        
    return citations

async def generate_answer(
    query: str, 
    context_chunks: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Constructs instructions and context, queries Groq API (llama-3.3-70b-versatile),
    and structures response metadata.
    
    Args:
        query: The user's query.
        context_chunks: Retrieved document segments.
        
    Returns:
        Dict: {"answer": str, "citations": list}
    """
    if not settings.GROQ_API_KEY:
        logger.error("LLM: GROQ_API_KEY is not configured.")
        return {
            "answer": "Error: Groq API key is not configured in backend environment variables.",
            "citations": []
        }
        
    system_prompt = get_system_prompt()
    user_prompt = build_user_prompt(query, context_chunks)
    
    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.1
    }
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            logger.info("LLM: Querying Groq completions endpoint...")
            response = await client.post(url, json=payload, headers=headers)
            
            if response.status_code != 200:
                logger.error(f"LLM: Groq API error response: {response.text}")
                response.raise_for_status()
                
            res_data = response.json()
            answer = res_data["choices"][0]["message"]["content"]
            
            logger.info("LLM: Response received, parsing citations...")
            citations = parse_citations(answer, context_chunks)
            
            return {
                "answer": answer,
                "citations": citations
            }
            
    except Exception as e:
        logger.error(f"LLM: Failed to run generation: {e}", exc_info=True)
        return {
            "answer": "This information is not available in the indexed filings due to a pipeline query error.",
            "citations": []
        }
