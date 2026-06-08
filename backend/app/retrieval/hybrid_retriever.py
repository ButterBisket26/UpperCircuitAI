import asyncio
import logging
from typing import List, Dict, Any, Optional
import asyncpg
from app.ingestion.embedder import embedder
from app.retrieval.vector_store import similarity_search
from app.retrieval.bm25_store import bm25_store

logger = logging.getLogger(__name__)

async def hybrid_retrieve(
    conn: asyncpg.Connection,
    query: str,
    top_k: int = 20,
    filters: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Executes parallel vector similarity search and sparse BM25 query lookups,
    combining ranking metrics using Reciprocal Rank Fusion (RRF).
    
    Args:
        conn: The database connection.
        query: The user query string.
        top_k: Number of unified search results to return.
        filters: Dictionary of metadata filters.
        
    Returns:
        List of fused search results sorted by RRF score.
    """
    # 1. Generate embedding for query
    # Since model loading and inference takes a moment, do it first.
    query_embedding = embedder.get_embeddings([query], is_query=True)[0]
    
    # 2. Setup parallel execution for dense search and sparse search
    # Fetch double the top_k to have a larger candidate pool for fusion
    candidate_limit = top_k * 2
    
    loop = asyncio.get_event_loop()
    
    logger.info(f"Hybrid Retriever: Running parallel retrieval for query: '{query}'")
    
    dense_task = similarity_search(conn, query_embedding, top_k=candidate_limit, filters=filters)
    
    # Run BM25 store search (CPU synchronous code) in executor to prevent thread blocking
    bm25_task = loop.run_in_executor(
        None, 
        bm25_store.search, 
        query, 
        candidate_limit, 
        filters
    )
    
    dense_results, bm25_results = await asyncio.gather(dense_task, bm25_task)
    
    # 3. Combine rankings using Reciprocal Rank Fusion (RRF)
    # RRF Score formula: Score = Sum_m ( 1 / (k + rank_m) )
    k = 60
    rrf_scores: Dict[str, float] = {}
    docs_metadata: Dict[str, Dict[str, Any]] = {}
    
    # Score dense result ranks
    for rank, doc in enumerate(dense_results):
        chunk_id = doc["chunk_id"]
        docs_metadata[chunk_id] = doc
        rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + (1.0 / (k + (rank + 1)))
        
    # Score BM25 result ranks
    for rank, doc in enumerate(bm25_results):
        chunk_id = doc["chunk_id"]
        if chunk_id not in docs_metadata:
            docs_metadata[chunk_id] = doc
        rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + (1.0 / (k + (rank + 1)))
        
    # Sort candidates by combined RRF scores descending
    sorted_candidates = sorted(rrf_scores.keys(), key=lambda cid: rrf_scores[cid], reverse=True)
    
    fused_results = []
    for chunk_id in sorted_candidates[:top_k]:
        doc = docs_metadata[chunk_id]
        # Include the RRF score in results for debugging and traceability
        doc_copy = doc.copy()
        doc_copy["rrf_score"] = rrf_scores[chunk_id]
        fused_results.append(doc_copy)
        
    logger.info(f"Hybrid Retriever: Fused {len(dense_results)} dense and {len(bm25_results)} sparse results into {len(fused_results)} top choices.")
    return fused_results
