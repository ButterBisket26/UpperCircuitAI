import time
import logging
import json
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
import asyncpg

from app.db.connection import get_db
from app.retrieval.hybrid_retriever import hybrid_retrieve
from app.retrieval.reranker import reranker
from app.generation.llm import generate_answer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/query", tags=["query"])

class QueryFilters(BaseModel):
    ticker: Optional[str] = Field(None, example="INFY")
    report_type: Optional[str] = Field(None, example="quarterly")
    fiscal_period: Optional[str] = Field(None, example="Q3FY25")

class QueryRequest(BaseModel):
    question: str = Field(..., example="What was Infosys revenue in Q3FY25?")
    filters: Optional[QueryFilters] = None

class CitationModel(BaseModel):
    company: str
    report_type: str
    fiscal_period: str
    page_number: int
    chunk_preview: str

class QueryResponse(BaseModel):
    answer: str
    citations: list[CitationModel]
    chunks_used: int
    latency_ms: int

@router.post("", response_model=QueryResponse)
async def query_filings(
    request: QueryRequest,
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    RAG Query endpoint. Runs hybrid search, reranks candidate documents, 
    calls Groq API (llama-3.3-70b-versatile) with temperature 0.1, 
    and returns answer + citations.
    """
    start_time = time.perf_counter()
    
    question = request.question.strip()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question string cannot be empty."
        )
        
    # Standardize filters for database query compatibility
    filters_dict = {}
    if request.filters:
        if request.filters.ticker:
            filters_dict["ticker"] = request.filters.ticker.strip().upper()
        if request.filters.report_type:
            filters_dict["report_type"] = request.filters.report_type.strip().lower()
        if request.filters.fiscal_period:
            filters_dict["fiscal_period"] = request.filters.fiscal_period.strip().upper()
            
    logger.info(f"Query: Initiating RAG pipeline for question: '{question}' with filters: {filters_dict}")
    
    try:
        # Step 1: Hybrid Retrieval (fuses pgvector and BM25 using RRF)
        # Fetch up to 20 candidate chunks for reranker input
        retrieved_chunks = await hybrid_retrieve(
            conn, 
            question, 
            top_k=20, 
            filters=filters_dict
        )
        
        if not retrieved_chunks:
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            return QueryResponse(
                answer="This information is not available in the indexed filings because no matching content was found in database.",
                citations=[],
                chunks_used=0,
                latency_ms=latency_ms
            )
            
        # Step 2: Cross-Encoder Reranking
        # Re-score retrieved candidates and narrow down to top 5 chunks
        top_chunks = reranker.rerank(question, retrieved_chunks, top_k=5)
        
        # Step 3: LLM Generation
        # Call Groq API with context chunks
        generation_result = await generate_answer(question, top_chunks)
        
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        
        # Log latency data as structured JSON to stdout
        latency_log = {
            "event": "query_latency",
            "question": question,
            "latency_ms": latency_ms,
            "chunks_retrieved": len(retrieved_chunks),
            "chunks_used": len(top_chunks)
        }
        print(json.dumps(latency_log))
        
        return QueryResponse(
            answer=generation_result["answer"],
            citations=generation_result["citations"],
            chunks_used=len(top_chunks),
            latency_ms=latency_ms
        )
        
    except Exception as e:
        logger.error(f"Query: Pipeline failed to run query: {e}", exc_info=True)
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred in RAG pipeline execution: {str(e)}"
        )
