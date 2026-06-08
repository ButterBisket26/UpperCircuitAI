import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings, loaded from env variables and optional .env file."""
    
    # Database Settings
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/uppercircuitai"
    
    # LLM Provider
    GROQ_API_KEY: str = ""
    
    # Hugging Face Configuration
    HF_API_TOKEN: str = ""
    
    # AWS S3 Configuration
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_BUCKET_NAME: str = ""
    AWS_REGION: str = "ap-south-1"
    
    # Server configuration
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    
    # Local Dev settings
    BM25_INDEX_PATH: str = "bm25_index.pkl"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
