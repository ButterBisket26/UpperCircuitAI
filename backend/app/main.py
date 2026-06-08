import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db.connection import db_manager
from app.ingestion.embedder import embedder
from app.retrieval.reranker import reranker
from app.retrieval.bm25_store import bm25_store
from app.routers import ingest, query, companies, eval as eval_router

# Configure structured logging to stdout
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles application startup and shutdown lifecycle events.
    Pre-loads local models and initializes databases to minimize response latencies.
    """
    logger.info("Starting up UpperCircuitAI Backend server...")
    
    # 1. Initialize PostgreSQL connection pool
    await db_manager.initialize()
    
    # 2. Pre-load local transformer models into memory
    # This prevents the first query from hanging for minutes
    logger.info("Initializing SentenceTransformer models...")
    embedder.load_model()
    
    logger.info("Initializing CrossEncoder reranker models...")
    reranker.load_model()
    
    # 3. Load BM25 index from pickle if available
    logger.info("Initializing BM25 index from disk cache...")
    loaded = bm25_store.load_index()
    if not loaded:
        logger.warning("BM25 index cache was not found. Index will be generated on first document ingestion.")
        
    yield
    
    # Close connection pool on shutdown
    logger.info("Shutting down UpperCircuitAI Backend server...")
    await db_manager.close()

app = FastAPI(
    title="UpperCircuitAI",
    description=" interview-grade Financial Filing QA RAG backend API.",
    version="1.0.0",
    lifespan=lifespan
)

# Setup CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this to vercel domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Register Routers
app.include_router(ingest.router)
app.include_router(query.router)
app.include_router(companies.router)
app.include_router(eval_router.router)

@app.get("/health", tags=["system"])
async def health_check():
    """Simple status check endpoint."""
    return {
        "status": "healthy",
        "models_loaded": {
            "bge_embeddings": embedder.model is not None,
            "cross_encoder_reranker": reranker.model is not None
        },
        "bm25_index_loaded": bm25_store.bm25 is not None
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=True)
