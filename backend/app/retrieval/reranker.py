import logging
from typing import List, Dict, Any, Optional
from sentence_transformers import CrossEncoder

logger = logging.getLogger(__name__)

class DocumentReranker:
    """Reranks candidate document chunks using a local CrossEncoder transformer model."""
    
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2") -> None:
        self.model_name = model_name
        self.model: Optional[CrossEncoder] = None

    def load_model(self) -> None:
        """Load the reranking cross-encoder model lazily."""
        if self.model is None:
            logger.info(f"Reranker: Loading model {self.model_name}...")
            self.model = CrossEncoder(self.model_name)
            logger.info("Reranker: CrossEncoder model loaded successfully.")

    def rerank(self, query: str, chunks: List[Dict[str, Any]], top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Computes relevance scores for (query, document) pairs and returns sorted list.
        
        Args:
            query: The user query string.
            chunks: A list of retrieval candidate chunk dictionaries.
            top_k: Number of highest-scored chunks to retain.
            
        Returns:
            A list of top_k reranked chunk dictionaries, with score appended.
        """
        if not chunks:
            return []
            
        self.load_model()
        assert self.model is not None
        
        # Format input as pairs: (query, document_text)
        pairs = [(query, chunk["content"]) for chunk in chunks]
        
        logger.info(f"Reranker: Scoring {len(chunks)} candidate chunks for query: '{query}'")
        
        # Predict relevance scores
        scores = self.model.predict(pairs)
        
        # Append scores to chunks
        scored_chunks = []
        for chunk, score in zip(chunks, scores):
            chunk_copy = chunk.copy()
            # Convert float32 numpy to standard float for serialization
            chunk_copy["rerank_score"] = float(score)
            scored_chunks.append(chunk_copy)
            
        # Sort descending by score
        scored_chunks.sort(key=lambda x: x["rerank_score"], reverse=True)
        
        logger.info(f"Reranker: Selected top {min(len(scored_chunks), top_k)} chunks.")
        return scored_chunks[:top_k]

# Singleton instance
reranker = DocumentReranker()
