import os
import pickle
import logging
import re
from typing import List, Dict, Any, Optional
from rank_bm25 import BM25Okapi
import asyncpg
from app.config import settings

logger = logging.getLogger(__name__)

class BM25Store:
    """Keyword search index using BM25 (Okapi) algorithm. Serialized to disk."""
    
    def __init__(self, index_path: Optional[str] = None) -> None:
        self.index_path = index_path or settings.BM25_INDEX_PATH
        self.bm25: Optional[BM25Okapi] = None
        self.chunk_ids: List[str] = []
        self.chunks_data: List[Dict[str, Any]] = []

    def _tokenize(self, text: str) -> List[str]:
        """Simple alphanumeric tokenizer for search text."""
        words = re.findall(r'\b\w+\b', text.lower())
        return words

    async def rebuild_index(self, conn: asyncpg.Connection) -> None:
        """
        Queries the database for all available chunks and regenerates the BM25 index.
        Saves index representation to disk after completion.
        """
        logger.info("BM25 Store: Querying database to rebuild search index...")
        
        sql = """
            SELECT 
                c.id::text as chunk_id,
                c.filing_id::text,
                c.chunk_index,
                c.content,
                c.chunk_type,
                c.page_number,
                c.metadata,
                f.report_type,
                f.fiscal_period,
                comp.ticker,
                comp.name as company_name
            FROM chunks c
            JOIN filings f ON c.filing_id = f.id
            JOIN companies comp ON f.company_id = comp.id
        """
        rows = await conn.fetch(sql)
        if not rows:
            logger.warning("BM25 Store: No database records found to build index.")
            self.bm25 = None
            self.chunk_ids = []
            self.chunks_data = []
            return
            
        corpus = []
        chunk_ids = []
        chunks_data = []
        
        for r in rows:
            content = r["content"]
            corpus.append(self._tokenize(content))
            chunk_ids.append(r["chunk_id"])
            
            # Try to decode metadata if stored as string, else use directly
            meta_val = r["metadata"]
            if isinstance(meta_val, str):
                try:
                    meta_val = json.loads(meta_val)
                except Exception:
                    pass
                    
            chunks_data.append({
                "chunk_id": r["chunk_id"],
                "filing_id": r["filing_id"],
                "chunk_index": r["chunk_index"],
                "content": content,
                "chunk_type": r["chunk_type"],
                "page_number": r["page_number"],
                "metadata": meta_val,
                "report_type": r["report_type"],
                "fiscal_period": r["fiscal_period"],
                "ticker": r["ticker"],
                "company_name": r["company_name"]
            })
            
        logger.info(f"BM25 Store: Fitting BM25 model with {len(chunks_data)} documents...")
        self.bm25 = BM25Okapi(corpus)
        self.chunk_ids = chunk_ids
        self.chunks_data = chunks_data
        
        self.save_index()
        logger.info("BM25 Store: Search index rebuilt and persisted.")

    def save_index(self) -> None:
        """Saves current chunks_data to index_path using pickle."""
        try:
            with open(self.index_path, "wb") as f:
                pickle.dump({
                    "chunk_ids": self.chunk_ids,
                    "chunks_data": self.chunks_data
                }, f)
            logger.info(f"BM25 Store: Saved pickle search index to {self.index_path}")
        except Exception as e:
            logger.error(f"BM25 Store: Failed to serialize index file: {e}", exc_info=True)

    def load_index(self) -> bool:
        """Loads index from pickle and recreates BM25 instance."""
        if not os.path.exists(self.index_path):
            logger.warning(f"BM25 Store: Index path not found: {self.index_path}")
            return False
            
        try:
            with open(self.index_path, "rb") as f:
                data = pickle.load(f)
                self.chunk_ids = data.get("chunk_ids", [])
                self.chunks_data = data.get("chunks_data", [])
                
            if self.chunks_data:
                corpus = [self._tokenize(c["content"]) for c in self.chunks_data]
                self.bm25 = BM25Okapi(corpus)
                logger.info(f"BM25 Store: Index loaded with {len(self.chunk_ids)} chunks.")
                return True
            else:
                logger.warning("BM25 Store: Index file is empty.")
                return False
        except Exception as e:
            logger.error(f"BM25 Store: Error reading search index: {e}", exc_info=True)
            return False

    def search(
        self,
        query: str,
        top_k: int = 20,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Executes sparse token lookup scoring, filtering results down to top_k matching elements.
        
        Args:
            query: User search string.
            top_k: Limit on response records.
            filters: Filtering parameters matching vector_store filters.
            
        Returns:
            List of dictionaries matching search context, with "score" parameter.
        """
        if self.bm25 is None or not self.chunks_data:
            # Try loading if not initialized
            if not self.load_index():
                logger.warning("BM25 Store: Searching empty index.")
                return []
                
        tokenized_query = self._tokenize(query)
        scores = self.bm25.get_scores(tokenized_query)
        
        results = []
        for idx, score in enumerate(scores):
            # Focus on documents containing at least one query term match
            if score <= 0:
                continue
                
            chunk = self.chunks_data[idx]
            
            # Apply metadata filters manually on the CPU representation
            if filters:
                if filters.get("ticker") and chunk["ticker"] != filters["ticker"].upper():
                    continue
                if filters.get("report_type") and chunk["report_type"] != filters["report_type"]:
                    continue
                if filters.get("fiscal_period") and chunk["fiscal_period"] != filters["fiscal_period"].upper():
                    continue
                    
            results.append({
                **chunk,
                "score": float(score)
            })
            
        # Order descending
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

# Singleton instance
bm25_store = BM25Store()
