import os
import json
import logging
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status
import asyncpg

from app.db.connection import get_db
# We will import the evaluation run function from the evaluation module
from app.eval.ragas_eval import run_pipeline_eval

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/eval", tags=["evaluation"])

from pydantic import BaseModel

class EvalResponse(BaseModel):
    status: str
    metrics: Dict[str, float]
    results_saved_to: str
    details: List[Dict[str, Any]]

@router.post("", response_model=EvalResponse)
async def run_rag_evaluation(conn: asyncpg.Connection = Depends(get_db)):
    """
    Runs the RAG evaluation pipeline. Loads test questions, queries the active RAG
    pipeline for each, computes RAGAS-like metrics (faithfulness, context recall, 
    answer relevancy), and returns the summary stats.
    """
    logger.info("Eval Router: Triggering pipeline validation run...")
    
    # Check if there are any filings in the database first
    chunks_exist = await conn.fetchval("SELECT COUNT(*) FROM chunks")
    if chunks_exist == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot run evaluation because no document chunks are currently indexed in database."
        )
        
    try:
        # Run evaluation asynchronously
        eval_result = await run_pipeline_eval(conn)
        
        return EvalResponse(
            status="completed",
            metrics=eval_result["metrics"],
            results_saved_to=eval_result["results_file"],
            details=eval_result["details"]
        )
    except Exception as e:
        logger.error(f"Eval Router: Evaluation run failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Evaluation pipeline error: {str(e)}"
        )
