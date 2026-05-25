from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # App
    app_name: str = "helpdesk-ai-service"
    port: int = 8000
    log_level: str = "INFO"

    # Gemini
    gemini_api_key: str
    gemini_model: str = "gemini-2.0-flash"
    gemini_embedding_model: str = "models/gemini-embedding-001"

    # ChromaDB
    chroma_host: str = "localhost"
    chroma_port: int = 8001
    chroma_collection: str = "helpdesk_tickets"
    chroma_persist_dir: str = "./chroma_data"

    # Backend (NestJS)
    backend_url: str = "http://localhost:3001"
    internal_api_secret: str

    # RAG
    rag_top_k: int = 3
    rag_similarity_threshold: float = 0.75


@lru_cache
def get_settings() -> Settings:
    return Settings()
