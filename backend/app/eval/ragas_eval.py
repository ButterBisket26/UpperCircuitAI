import os
import json
import logging
import time
from typing import List, Dict, Any, Tuple
import httpx
import asyncpg
from datetime import datetime

from app.config import settings
from app.retrieval.hybrid_retriever import hybrid_retrieve
from app.retrieval.reranker import reranker
from app.generation.llm import generate_answer

logger = logging.getLogger(__name__)

async def call_judge_api(system_prompt: str, user_prompt: str) -> Tuple[float, str]:
    """Helper to query the Groq LLM as a judge and parse score + reason."""
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
        "temperature": 0.0, # Complete determinism
        "response_format": {"type": "json_object"}
    }
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            res_data = response.json()
            content = res_data["choices"][0]["message"]["content"]
            
            data = json.loads(content)
            score = float(data.get("score", 0.0))
            reason = str(data.get("reason", "No reason provided."))
            
            # Bound score to [0.0, 1.0]
            score = max(0.0, min(1.0, score))
            return score, reason
    except Exception as e:
        logger.error(f"Judge API call failed: {e}", exc_info=True)
        return 0.5, f"Scoring engine error: {str(e)}"

async def evaluate_faithfulness(context: str, answer: str) -> Tuple[float, str]:
    """Evaluates whether answer is grounded strictly in context."""
    system_prompt = (
        "You are an AI judge evaluating a RAG pipeline's faithfulness.\n"
        "Analyze if the Answer is grounded strictly on facts provided in the Context.\n"
        "If the answer makes claims not explicitly present in the context, deduct points.\n"
        "Return a JSON object: {\"score\": <float between 0.0 and 1.0>, \"reason\": \"<brief explanation>\"}"
    )
    user_prompt = f"Context:\n{context}\n\nAnswer:\n{answer}"
    return await call_judge_api(system_prompt, user_prompt)

async def evaluate_context_recall(ground_truth: str, context: str) -> Tuple[float, str]:
    """Evaluates if the retrieval captured all key details of the ground truth."""
    system_prompt = (
        "You are an AI judge evaluating a RAG pipeline's context recall.\n"
        "Analyze if the key factual statements in the Ground Truth are present inside the Context.\n"
        "If key metrics/numbers from the ground truth are missing from the context, deduct points.\n"
        "Return a JSON object: {\"score\": <float between 0.0 and 1.0>, \"reason\": \"<brief explanation>\"}"
    )
    user_prompt = f"Ground Truth:\n{ground_truth}\n\nContext:\n{context}"
    return await call_judge_api(system_prompt, user_prompt)

async def evaluate_answer_relevancy(question: str, answer: str) -> Tuple[float, str]:
    """Evaluates how well the answer addresses the question directly."""
    system_prompt = (
        "You are an AI judge evaluating a RAG pipeline's answer relevancy.\n"
        "Analyze if the Answer directly addresses the Question without rambling or including unrelated facts.\n"
        "Return a JSON object: {\"score\": <float between 0.0 and 1.0>, \"reason\": \"<brief explanation>\"}"
    )
    user_prompt = f"Question:\n{question}\n\nAnswer:\n{answer}"
    return await call_judge_api(system_prompt, user_prompt)

async def run_pipeline_eval(conn: asyncpg.Connection) -> Dict[str, Any]:
    """
    Runs evaluation on the test set. 
    Queries RAG pipeline for each question, computes scores, and logs results.
    """
    logger.info("RAGAS Eval: Loading evaluation questions...")
    
    # Try finding the file in typical locations
    paths_to_try = [
        "eval/test_questions.json",
        "../eval/test_questions.json",
        "d:/Projects/UpperCircuitAI/uppercircuitai/eval/test_questions.json"
    ]
    
    test_questions_file = None
    for p in paths_to_try:
        if os.path.exists(p):
            test_questions_file = p
            break
            
    if not test_questions_file:
        raise FileNotFoundError("Could not locate eval/test_questions.json in workspace directories.")
        
    with open(test_questions_file, "r") as f:
        test_questions = json.load(f)
        
    logger.info(f"RAGAS Eval: Loaded {len(test_questions)} questions from {test_questions_file}")
    
    results = []
    
    total_faithfulness = 0.0
    total_recall = 0.0
    total_relevancy = 0.0
    
    for idx, q_pair in enumerate(test_questions):
        question = q_pair["question"]
        ground_truth = q_pair["ground_truth"]
        ticker = q_pair.get("ticker", "")
        
        logger.info(f"RAGAS Eval: Running evaluation [{idx+1}/{len(test_questions)}] for {ticker}...")
        
        # 1. Run RAG Retrieval
        filters = {"ticker": ticker} if ticker else None
        retrieved = await hybrid_retrieve(conn, question, top_k=20, filters=filters)
        
        if not retrieved:
            logger.warning(f"RAGAS Eval: No chunks retrieved for question: '{question}'")
            results.append({
                "question": question,
                "ground_truth": ground_truth,
                "answer": "No context chunks retrieved from DB.",
                "faithfulness": 0.0,
                "context_recall": 0.0,
                "answer_relevancy": 0.0,
                "reasons": {"faithfulness": "No context", "context_recall": "No context", "answer_relevancy": "No answer"}
            })
            continue
            
        # Rerank to top 5
        top_chunks = reranker.rerank(question, retrieved, top_k=5)
        
        # 2. Run LLM generation
        generation_res = await generate_answer(question, top_chunks)
        answer = generation_res["answer"]
        
        # Merge chunk contents for context scoring
        context_merged = "\n\n".join([c["content"] for c in top_chunks])
        
        # 3. Compute Scores
        faith_score, faith_reason = await evaluate_faithfulness(context_merged, answer)
        recall_score, recall_reason = await evaluate_context_recall(ground_truth, context_merged)
        rel_score, rel_reason = await evaluate_answer_relevancy(question, answer)
        
        total_faithfulness += faith_score
        total_recall += recall_score
        total_relevancy += rel_score
        
        results.append({
            "question": question,
            "ground_truth": ground_truth,
            "answer": answer,
            "faithfulness": faith_score,
            "context_recall": recall_score,
            "answer_relevancy": rel_score,
            "reasons": {
                "faithfulness": faith_reason,
                "context_recall": recall_reason,
                "answer_relevancy": rel_reason
            }
        })
        
        # Pause slightly to avoid Groq rate limit issues
        await asyncio.sleep(0.5)
        
    num_questions = len(test_questions)
    metrics = {
        "faithfulness": total_faithfulness / num_questions if num_questions > 0 else 0.0,
        "context_recall": total_recall / num_questions if num_questions > 0 else 0.0,
        "answer_relevancy": total_relevancy / num_questions if num_questions > 0 else 0.0
    }
    
    # Save results to local file
    os.makedirs("eval/results", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"eval/results/eval_run_{timestamp}.json"
    
    with open(results_file, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "summary_metrics": metrics,
            "details": results
        }, f, indent=2)
        
    logger.info(f"RAGAS Eval: Evaluation complete. Results saved to {results_file}")
    
    # Print a summary table to stdout as requested by constraints
    print("=" * 60)
    print(" RAGAS EVALUATION PIPELINE SUMMARY SCORE ")
    print("=" * 60)
    print(f"Faithfulness:     {metrics['faithfulness']:.4f}")
    print(f"Context Recall:   {metrics['context_recall']:.4f}")
    print(f"Answer Relevancy: {metrics['answer_relevancy']:.4f}")
    print("=" * 60)
    
    return {
        "metrics": metrics,
        "results_file": results_file,
        "details": results
    }
