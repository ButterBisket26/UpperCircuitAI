import json
import logging
from typing import List, Dict, Any, Optional
import asyncpg

logger = logging.getLogger(__name__)

async def insert_chunks(
    conn: asyncpg.Connection,
    chunks: List[Dict[str, Any]],
    embeddings: List[List[float]],
    filing_id: str
) -> None:
    """
    Performs bulk insertion of document chunks and their high-dimensional vector
    embeddings into the chunks database table using asyncpg's copy_records_to_table.
    
    Args:
        conn: The active asyncpg database connection.
        chunks: List of chunk dictionaries containing content and metadata.
        embeddings: List of embedding vectors (list of floats).
        filing_id: UUID of the filing as a string.
    """
    import uuid
    # Convert string uuid to uuid.UUID object for db compatibility
    filing_uuid = uuid.UUID(str(filing_id)) if isinstance(filing_id, str) else filing_id

    records = []
    for idx, (chunk, emb) in enumerate(zip(chunks, embeddings)):
        # Format embedding vector as string format for pgvector casting
        emb_str = f"[{','.join(map(str, emb))}]"
        
        # Serialize metadata dict to JSON string
        meta_str = json.dumps(chunk["metadata"])
        
        records.append((
            filing_uuid,
            idx,
            chunk["content"],
            chunk["chunk_type"],
            chunk["metadata"].get("page_number", 0),
            emb_str,
            meta_str
        ))
        
    logger.info(f"Vector Store: Bulk inserting {len(records)} chunks for filing_id: {filing_id}")
    
    # We use executemany with vector casting ($6::vector) because pgvector's binary OID
    # does not have a registered binary encoder in asyncpg's copy_records_to_table.
    await conn.executemany(
        """
        INSERT INTO chunks (filing_id, chunk_index, content, chunk_type, page_number, embedding, metadata)
        VALUES ($1, $2, $3, $4, $5, $6::vector, $7::jsonb)
        """,
        records
    )
    logger.info("Vector Store: Bulk insertion completed successfully.")

async def similarity_search(
    conn: asyncpg.Connection,
    query_embedding: List[float],
    top_k: int = 20,
    filters: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Executes a cosine similarity vector search on the chunks table using pgvector <=> operator,
    joining companies and filings to support metadata filters.
    
    Args:
        conn: The active asyncpg connection.
        query_embedding: The vector representation of the query string.
        top_k: Maximum number of records to return.
        filters: Dictionary of filters like: {"ticker": str, "report_type": str, "fiscal_period": str}
        
    Returns:
        A list of matching records with their computed cosine similarity score.
    """
    emb_str = f"[{','.join(map(str, query_embedding))}]"
    
    # Base query joining companies and filings for clean filtering
    sql = """
        SELECT 
            c.id::text as chunk_id,
            c.filing_id::text,
            c.chunk_index,
            c.content,
            c.chunk_type,
            c.page_number,
            c.metadata,
            (1.0 - (c.embedding <=> $1::vector)) as similarity,
            f.report_type,
            f.fiscal_period,
            comp.ticker,
            comp.name as company_name
        FROM chunks c
        JOIN filings f ON c.filing_id = f.id
        JOIN companies comp ON f.company_id = comp.id
        WHERE c.embedding IS NOT NULL
    """
    
    params = [emb_str]
    param_counter = 2
    
    # Apply dynamic filters
    if filters:
        if filters.get("ticker"):
            sql += f" AND comp.ticker = ${param_counter}"
            params.append(filters["ticker"].upper())
            param_counter += 1
            
        if filters.get("report_type"):
            sql += f" AND f.report_type = ${param_counter}"
            params.append(filters["report_type"])
            param_counter += 1
            
        if filters.get("fiscal_period"):
            sql += f" AND f.fiscal_period = ${param_counter}"
            params.append(filters["fiscal_period"].upper())
            param_counter += 1
            
    # Order by cosine distance (similarity descending)
    sql += f" ORDER BY c.embedding <=> $1::vector LIMIT ${param_counter}"
    params.append(top_k)
    
    logger.info(f"Vector Store: Running similarity search with filters={filters}, top_k={top_k}")
    
    rows = await conn.fetch(sql, *params)
    
    results = []
    for r in rows:
        results.append({
            "chunk_id": r["chunk_id"],
            "filing_id": r["filing_id"],
            "chunk_index": r["chunk_index"],
            "content": r["content"],
            "chunk_type": r["chunk_type"],
            "page_number": r["page_number"],
            "similarity": r["similarity"],
            "metadata": json.loads(r["metadata"]) if isinstance(r["metadata"], str) else r["metadata"],
            "report_type": r["report_type"],
            "fiscal_period": r["fiscal_period"],
            "ticker": r["ticker"],
            "company_name": r["company_name"]
        })
        
    return results
