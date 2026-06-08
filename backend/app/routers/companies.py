import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
import asyncpg
from datetime import date, datetime

from app.db.connection import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/companies", tags=["companies"])

class CompanyModel(BaseModel):
    id: str
    ticker: str
    name: str
    exchange: str
    sector: Optional[str] = None
    isin: str
    filing_count: int

class FilingModel(BaseModel):
    id: str
    report_type: str
    fiscal_period: str
    filing_date: Optional[date] = None
    pdf_url: Optional[str] = None
    s3_key: Optional[str] = None
    status: str
    chunk_count: int
    created_at: datetime

@router.get("", response_model=List[CompanyModel])
async def list_companies(conn: asyncpg.Connection = Depends(get_db)):
    """
    Returns a list of all indexed companies along with the count of filings indexed for each.
    """
    logger.info("Companies: Listing all companies...")
    
    sql = """
        SELECT 
            c.id::text as id, 
            c.ticker, 
            c.name, 
            c.exchange, 
            c.sector, 
            c.isin,
            COUNT(f.id)::int as filing_count
        FROM companies c
        LEFT JOIN filings f ON c.id = f.company_id
        GROUP BY c.id, c.ticker, c.name, c.exchange, c.sector, c.isin
        ORDER BY c.ticker ASC
    """
    
    try:
        rows = await conn.fetch(sql)
        results = []
        for r in rows:
            results.append(CompanyModel(
                id=r["id"],
                ticker=r["ticker"],
                name=r["name"],
                exchange=r["exchange"],
                sector=r["sector"],
                isin=r["isin"],
                filing_count=r["filing_count"]
            ))
        return results
    except Exception as e:
        logger.error(f"Companies: Failed to fetch companies: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to query companies index."
        )

@router.get("/{ticker}/filings", response_model=List[FilingModel])
async def list_company_filings(
    ticker: str, 
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Returns all filings indexed for a specific company ticker, including processing statuses.
    """
    ticker_val = ticker.strip().upper()
    logger.info(f"Companies: Listing filings for ticker: '{ticker_val}'")
    
    # Verify company exists
    comp_exists = await conn.fetchrow(
        "SELECT id FROM companies WHERE ticker = $1", ticker_val
    )
    if not comp_exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company with ticker '{ticker_val}' is not indexed in system database."
        )
        
    sql = """
        SELECT 
            f.id::text as id, 
            f.report_type, 
            f.fiscal_period, 
            f.filing_date, 
            f.pdf_url, 
            f.s3_key, 
            f.status,
            f.created_at,
            COUNT(c.id)::int as chunk_count
        FROM filings f
        LEFT JOIN chunks c ON f.id = c.filing_id
        WHERE f.company_id = $1
        GROUP BY f.id, f.report_type, f.fiscal_period, f.filing_date, f.pdf_url, f.s3_key, f.status, f.created_at
        ORDER BY f.created_at DESC
    """
    
    try:
        rows = await conn.fetch(sql, comp_exists["id"])
        results = []
        for r in rows:
            results.append(FilingModel(
                id=r["id"],
                report_type=r["report_type"],
                fiscal_period=r["fiscal_period"],
                filing_date=r["filing_date"],
                pdf_url=r["pdf_url"],
                s3_key=r["s3_key"],
                status=r["status"],
                chunk_count=r["chunk_count"],
                created_at=r["created_at"]
            ))
        return results
    except Exception as e:
        logger.error(f"Companies: Failed to list filings for {ticker_val}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to query filings for company ticker {ticker_val}."
        )

@router.delete("/filings/{filing_id}", status_code=status.HTTP_200_OK)
async def delete_filing(
    filing_id: str,
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Deletes an indexed filing and all associated text/table chunks.
    Rebuilds the BM25 search index.
    """
    import uuid
    from app.retrieval.bm25_store import bm25_store
    from app.config import settings
    import boto3
    
    logger.info(f"Companies: Deleting filing with ID: {filing_id}")
    
    try:
        filing_uuid = uuid.UUID(filing_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid UUID format for filing_id."
        )
        
    # Check if filing exists
    filing = await conn.fetchrow(
        "SELECT id, s3_key, company_id FROM filings WHERE id = $1", filing_uuid
    )
    if not filing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Filing not found."
        )
        
    # Delete from S3 if s3_key is present and AWS credentials are set
    s3_key = filing["s3_key"]
    if s3_key:
        if all([settings.AWS_ACCESS_KEY_ID, settings.AWS_SECRET_ACCESS_KEY, settings.AWS_BUCKET_NAME]):
            try:
                s3 = boto3.client(
                    "s3",
                    region_name=settings.AWS_REGION,
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
                )
                s3.delete_object(Bucket=settings.AWS_BUCKET_NAME, Key=s3_key)
                logger.info(f"Deleted S3 object: {s3_key}")
            except Exception as s3_err:
                logger.error(f"Failed to delete S3 object {s3_key}: {s3_err}")

    # Delete the filing record from DB (this will cascade delete chunks due to foreign key constraint)
    await conn.execute("DELETE FROM filings WHERE id = $1", filing_uuid)
    
    # Rebuild BM25 search index
    try:
        await bm25_store.rebuild_index(conn)
        logger.info("BM25 search index rebuilt successfully after filing deletion.")
    except Exception as bm25_err:
        logger.error(f"Failed to rebuild BM25 search index: {bm25_err}")
        
    return {"status": "success", "message": "Filing deleted successfully."}
