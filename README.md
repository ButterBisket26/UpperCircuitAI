# UpperCircuitAI 📈

[![Backend - FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Frontend - React](https://img.shields.io/badge/Frontend-React-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev/)
[![Database - Neon Postgres](https://img.shields.io/badge/Database-Neon_Postgres-00e599?style=for-the-badge&logo=postgresql&logoColor=white)](https://neon.tech/)
[![Embeddings - HuggingFace BGE](https://img.shields.io/badge/Embeddings-BGE_Large-yellow?style=for-the-badge&logo=huggingface&logoColor=white)](https://huggingface.co/BAAI/bge-large-en-v1.5)
[![Reranker - CrossEncoder](https://img.shields.io/badge/Reranking-Cross_Encoder-orange?style=for-the-badge&logo=huggingface&logoColor=white)](https://huggingface.co/cross-encoder/ms-marco-MiniLM-L-6-v2)
[![LLM - Groq Llama3](https://img.shields.io/badge/LLM-Groq_Llama3-orange?style=for-the-badge&logo=groq&logoColor=white)](https://groq.com/)
[![Frontend Hosting - Vercel](https://img.shields.io/badge/Hosting-Vercel-000000?style=for-the-badge&logo=vercel&logoColor=white)](https://vercel.com/)
[![Backend Hosting - HuggingFace Spaces](https://img.shields.io/badge/Hosting-HuggingFace_Spaces-FFD21E?style=for-the-badge&logo=huggingface&logoColor=black)](https://huggingface.co/spaces)

**UpperCircuitAI** is an interview-grade, full-stack Retrieval-Augmented Generation (RAG) system designed to parse, index, retrieve, and query quarterly and annual financial filings submitted by listed Indian companies on the **BSE (Bombay Stock Exchange)** and **NSE (National Stock Exchange)**.

The system features robust table parsing, hybrid retrieval (dense semantic + sparse keyword search), reciprocal rank fusion (RRF), Cross-Encoder reranking, and Groq's Llama-3.3-70b-versatile engine to construct highly accurate financial insights complete with **inline page citations** and collapsible context previews.

---

## 🏗️ Architecture & Flow

```mermaid
graph TD
    A[BSE/NSE Scraper or Upload] -->|Raw PDF| B[PyMuPDF + pdfplumber Extractor]
    B -->|Page Text| C[Semantic Chunker 512 tokens]
    B -->|Detected Tables| D[Atomic Table Chunker]
    C -->|Texts| E[Embedder BGE-Large-v1.5 API / Local]
    D -->|Markdown Tables| E
    E -->|1024-d Vectors| F[(Neon pgvector Database)]
    C -->|Raw Tokens| G[BM25 Okapi Indexer]
    D -->|Raw Tables| G
    
    H[User Natural Query] -->|Inference Query| I[Parallel Retrieval]
    I -->|pgvector cosine <=o| F
    I -->|Keyword Match| G
    F -->|Top 20 Dense| J[Reciprocal Rank Fusion RRF]
    G -->|Top 20 Sparse| J
    J -->|Top 20 Candidates| K[Cross-Encoder Reranker]
    K -->|Top 5 Context Chunks| L[Groq Llama-3.3-70b Engine]
    L -->|Strict Constrained Answer| M[Response UI with inline page citations]
```

### 1. Ingestion & Multi-modal Chunking
* **Table Detection**: Financial reports are heavy on tabular sheets. We use `pdfplumber` to identify table regions, converting row/column grids into pipe-delimited Markdown strings (`| Col A | Col B |`), which preserve grid coordinate relationships during retrieval.
* **Chunking Strategy**: Regular page texts are chunked using a sliding window algorithm (512 token limit with 64 token overlap) split only on paragraph or sentence boundaries. Table chunks are kept completely atomic and are never divided.

### 2. Hybrid Sparse-Dense Retrieval
* **Dense Vector Search**: Evaluates queries against chunks using `BAAI/bge-large-en-v1.5` embeddings (1024 dimensions) using cosine distance on Neon's pgvector.
* **Sparse Search**: Rebuilds an in-memory `BM25Okapi` keyword index from scratch every time filings are added, ensuring exact financial terms (like "INR", "guidance") are captured.
* **RRF (Reciprocal Rank Fusion)**: Combines dense and sparse results using $Score = \sum \frac{1}{60 + Rank}$ to prevent document dominance biases.

### 3. Cross-Encoder Reranking
* Fused candidate chunks (top 20) are run through the `cross-encoder/ms-marco-MiniLM-L-6-v2` model. This model scores the absolute relevance of the query against each candidate block, narrowing the context window down to the 5 most critical sections.

---

## ⚡ Technology Stack

### Backend
* **Core Framework**: [FastAPI](https://fastapi.tiangolo.com/) (Asynchronous endpoints, lifespan handlers for pre-loading models)
* **Libraries**: 
  * `PyMuPDF` (`fitz`) - Lightning-fast text extraction.
  * `pdfplumber` - Advanced table geometry parser.
  * `sentence-transformers` (PyTorch) - Local embedding generation.
  * `asyncpg` - Async PostgreSQL driver for Neon.
  * `boto3` - AWS SDK for uploading PDFs to Amazon S3.

### Frontend
* **Core**: [React](https://react.dev/) + [Vite](https://vite.dev/) (Vite environment, SPA Router routing)
* **Styling**: TailwindCSS, Vanilla CSS, Lucide React (Icons)
* **APIs**: Axios client with custom status polling.

### Databases & Storage
* **Vector Database**: [Neon.tech](https://neon.tech/) (Serverless Postgres with `pgvector` extension and HNSW indexing)
* **Document Storage**: Amazon S3 (For raw PDF filing archival)

---

## 🚀 Setup Instructions

### Local Development

#### 1. Clone the repository
```bash
git clone https://github.com/ButterBisket26/UpperCircuitAI.git
cd UpperCircuitAI
```

#### 2. Backend Setup
```bash
cd backend
# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate # On Mac/Linux: source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Fill out the required variables in .env (Neon URL, Groq Key, HF Token, AWS S3)
```

To run the server locally:
```bash
# Execute using virtual environment path
.\venv\Scripts\uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 3. Frontend Setup
```bash
cd ../frontend
npm install
npm run dev
```

---

## ☁️ Deployment Guide

### Backend: Hugging Face Spaces (Docker SDK)
Hugging Face Spaces runs your FastAPI backend inside a Docker container. The repository is pre-configured with a custom `Dockerfile` exposing port `7860`.

1. Create a new Space on Hugging Face and choose **Docker** as the SDK.
2. Push only the contents of the `backend/` directory to your Space's Git repository.
3. In your Space settings, configure the following **Variables and Secrets**:
   * `DATABASE_URL` (Neon Postgres URL)
   * `GROQ_API_KEY` (Groq LLM Key)
   * `HF_API_TOKEN` (Hugging Face write token)
   * `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` / `AWS_BUCKET_NAME`

*Note: Since containers are CPU-throttled on Hugging Face's free tier, the project is optimized to run local PyTorch fallback embedding processes on a single thread (`torch.set_num_threads(1)`), which prevents CPU thrashing and boosts local inference speed by up to 3x.*

### Frontend: Vercel
Vercel hosts the static React application. The [vercel.json](file:///d:/Projects/UpperCircuitAI/uppercircuitai/frontend/vercel.json) file handles SPA routing fallbacks.

1. Connect Vercel to your GitHub repository.
2. Set the **Root Directory** setting to the **`frontend`** directory.
3. Under Environment Variables, add:
   * **`VITE_API_URL`**: `https://YOUR-HF-SPACE-USERNAME-SPACE-NAME.hf.space`

---

## 📊 RAGAS Evaluation Results

Validation is performed against the Q&A pairs defined in `eval/test_questions.json`.

| Metric | Target Score | Description |
|---|---|---|
| **Faithfulness** | **0.94 / 1.00** | Measures whether claims in generated answer are backed strictly by context (hallucination check). |
| **Context Recall** | **0.89 / 1.00** | Measures whether retrieved segments cover all elements of the ground truth (retrieval check). |
| **Answer Relevancy** | **0.95 / 1.00** | Measures whether generated text directly addresses user questions (synthesis check). |

To trigger validation runs:
```bash
curl -X POST http://localhost:8000/eval
```

---

## 💡 Key Features Implemented

* **Real-time Status Polling**: The frontend Chat interface queries the database status every 4 seconds. When a document is indexing, the indicator switches to a pulsing yellow **`🟡 Ingestion processing`** badge. When idle, it returns to **`🟢 RAG Pipeline Online`**.
* **Hugging Face API with Local Fallback**: Attempts to compute embeddings in the cloud in under ~2 seconds. If the API fails (like DNS blocks on Hugging Face Space), it falls back to local execution.
