import logging
from typing import List, Optional
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

class DocumentEmbedder:
    """Computes dense vector representations of texts using a local sentence-transformer model."""
    
    def __init__(self, model_name: str = "BAAI/bge-large-en-v1.5") -> None:
        self.model_name = model_name
        self.model: Optional[SentenceTransformer] = None

    def load_model(self) -> None:
        """Load the model into memory. Done lazily on first call or startup."""
        if self.model is None:
            logger.info(f"Embedder: Loading model {self.model_name}...")
            
            # Optimize PyTorch CPU threading to prevent CPU thrashing
            import torch
            import os
            num_threads = min(os.cpu_count() or 4, 8)
            torch.set_num_threads(num_threads)
            logger.info(f"Embedder: Configured PyTorch to use {num_threads} CPU threads for local inference.")
            
            self.model = SentenceTransformer(self.model_name)
            logger.info("Embedder: Model loaded successfully.")

    def _get_embeddings_api(self, formatted_texts: List[str]) -> Optional[List[List[float]]]:
        """Queries the HuggingFace Inference API for embeddings."""
        from app.config import settings
        import httpx
        import time
        
        token = settings.HF_API_TOKEN
        if not token:
            return None
            
        url = f"https://api-inference.huggingface.co/pipeline/feature-extraction/{self.model_name}"
        headers = {"Authorization": f"Bearer {token}"}
        
        # Chunk texts into batches of 32 to conform with API limitations
        batch_size = 32
        all_embeddings = []
        
        try:
            with httpx.Client(timeout=120.0) as client:
                for i in range(0, len(formatted_texts), batch_size):
                    batch = formatted_texts[i:i+batch_size]
                    payload = {
                        "inputs": batch,
                        "options": {"wait_for_model": True}
                    }
                    
                    retries = 3
                    delay = 5.0
                    for retry in range(retries):
                        logger.info(f"Embedder API: Batch {i//batch_size + 1}/{(len(formatted_texts)-1)//batch_size + 1} ({len(batch)} chunks)")
                        resp = client.post(url, headers=headers, json=payload)
                        
                        if resp.status_code == 200:
                            embeddings = resp.json()
                            if isinstance(embeddings, list) and len(embeddings) > 0:
                                all_embeddings.extend(embeddings)
                                break
                            else:
                                raise ValueError(f"Unexpected response format: {type(embeddings)}")
                        
                        elif resp.status_code == 503:
                            data = resp.json()
                            wait_time = data.get("estimated_time", delay)
                            logger.warning(f"Embedder API: Model is loading. Waiting {wait_time}s (retry {retry + 1}/{retries})...")
                            time.sleep(wait_time)
                            
                        else:
                            resp.raise_for_status()
                    else:
                        raise httpx.HTTPError(f"Failed to get embeddings after {retries} retries due to model loading.")
                        
            if len(all_embeddings) == len(formatted_texts):
                logger.info("Embedder API: Successfully retrieved all embeddings.")
                return all_embeddings
            else:
                logger.error(f"Embedder API: Count mismatch (got {len(all_embeddings)}, expected {len(formatted_texts)}).")
                return None
                
        except Exception as e:
            logger.error(f"Embedder API: HuggingFace API call failed: {e}. Falling back to local SentenceTransformer.")
            return None

    def get_embeddings(self, texts: List[str], is_query: bool = False) -> List[List[float]]:
        """
        Generates dense vector list representation for texts.
        Uses HuggingFace Inference API if settings.HF_API_TOKEN is set,
        otherwise falls back to local SentenceTransformer model.
        
        Args:
            texts: List of strings to embed.
            is_query: If True, formats text as a query, else formats as document chunk.
            
        Returns:
            List of lists of floats representing embeddings.
        """
        # Format strings with BGE task instructions
        formatted_texts = []
        for text in texts:
            if is_query:
                # BGE v1.5 standard query instruction
                formatted_texts.append(f"Represent this sentence for searching relevant passages: {text}")
            else:
                # Custom financial document chunk instruction
                formatted_texts.append(f"Represent this financial document for retrieval: {text}")
                
        # Try HF Inference API first
        api_embeddings = self._get_embeddings_api(formatted_texts)
        if api_embeddings is not None:
            return api_embeddings
            
        # Local model fallback
        logger.info(f"Embedder: Generating embeddings locally for {len(texts)} chunks (is_query={is_query})")
        self.load_model()
        assert self.model is not None
        
        # Encode with local model
        embeddings = self.model.encode(
            formatted_texts,
            batch_size=32,
            show_progress_bar=True,
            normalize_embeddings=True
        )
        
        # Convert numpy array to standard list of lists of float
        return embeddings.tolist()

# Singleton instance
embedder = DocumentEmbedder()
