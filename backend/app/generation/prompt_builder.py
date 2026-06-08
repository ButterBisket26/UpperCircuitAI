from typing import List, Dict, Any

def get_system_prompt() -> str:
    """
    Returns the exact system prompt constraining the LLM behavior to factual Indian filing answers.
    """
    return (
        "You are UpperCircuitAI, a financial analyst assistant specializing in Indian listed company filings.\n\n"
        "Answer the user's question using ONLY the provided context chunks from official BSE/NSE filings.\n"
        "For every factual claim, cite the source using [Company | Report Type | Period | Page N] format.\n"
        "If the answer cannot be found in the context, say \"This information is not available in the indexed filings.\"\n"
        "Never hallucinate financial figures. Never make up fiscal periods or numbers.\n"
        "Format numbers in Indian numbering system (lakhs, crores) when present in source."
    )

def build_user_prompt(query: str, chunks: List[Dict[str, Any]]) -> str:
    """
    Constructs the structured context representation containing filing information
    followed by the user's analytical question.
    
    Args:
        query: User search/analytical question.
        chunks: List of reranked context chunk dicts.
        
    Returns:
        Structured context and query string.
    """
    context_blocks = []
    for idx, chunk in enumerate(chunks):
        company = chunk.get("company_name", chunk.get("company", "Unknown Company"))
        report_type = chunk.get("report_type", "Filing")
        fiscal_period = chunk.get("fiscal_period", "N/A")
        page_number = chunk.get("page_number", "N/A")
        content = chunk.get("content", "")
        
        block = f"[CHUNK {idx + 1}] {company} | {report_type} | {fiscal_period} | Page {page_number}\n{content}"
        context_blocks.append(block)
        
    context_str = "\n\n".join(context_blocks)
    return f"Context:\n{context_str}\n\nQuestion: {query}"
