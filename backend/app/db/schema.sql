-- UpperCircuitAI Database Schema
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

-- Companies Table
CREATE TABLE IF NOT EXISTS companies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ticker VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    exchange VARCHAR(10) CHECK (exchange IN ('BSE', 'NSE')) NOT NULL,
    sector VARCHAR(100),
    isin VARCHAR(20) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Filings Table
CREATE TABLE IF NOT EXISTS filings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID REFERENCES companies(id) ON DELETE CASCADE NOT NULL,
    report_type VARCHAR(20) CHECK (report_type IN ('quarterly', 'annual')) NOT NULL,
    fiscal_period VARCHAR(20) NOT NULL,
    filing_date DATE,
    pdf_url TEXT,
    s3_key TEXT,
    status VARCHAR(20) CHECK (status IN ('pending', 'processed', 'failed')) DEFAULT 'pending' NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Chunks Table
CREATE TABLE IF NOT EXISTS chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    filing_id UUID REFERENCES filings(id) ON DELETE CASCADE NOT NULL,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    chunk_type VARCHAR(10) CHECK (chunk_type IN ('text', 'table')) NOT NULL,
    page_number INTEGER NOT NULL,
    embedding vector(1024), -- 1024 dimensions for bge-large-en-v1.5
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indices
CREATE INDEX IF NOT EXISTS chunks_embedding_hnsw_idx ON chunks USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS chunks_content_fts_idx ON chunks USING gin (to_tsvector('english', content));
CREATE INDEX IF NOT EXISTS filings_company_id_idx ON filings(company_id);
CREATE INDEX IF NOT EXISTS chunks_filing_id_idx ON chunks(filing_id);
