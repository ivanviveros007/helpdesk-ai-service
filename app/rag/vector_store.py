import logging
import chromadb
from chromadb import Collection
from app.core.config import get_settings

logger = logging.getLogger(__name__)

_client: chromadb.ClientAPI | None = None
_collection: Collection | None = None


def get_chroma_client() -> chromadb.ClientAPI:
    global _client
    if _client is None:
        settings = get_settings()
        # Persistent local storage — no server required for dev
        _client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
        logger.info("ChromaDB PersistentClient initialized at %s", settings.chroma_persist_dir)
    return _client


def get_collection() -> Collection:
    global _collection
    if _collection is None:
        client = get_chroma_client()
        settings = get_settings()
        _collection = client.get_or_create_collection(
            name=settings.chroma_collection,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(
            "ChromaDB collection '%s' ready (%d docs)",
            settings.chroma_collection,
            _collection.count(),
        )
    return _collection


def add_ticket_to_store(
    ticket_id: str,
    text: str,
    metadata: dict,
    embedding: list[float],
) -> None:
    """Inserta o actualiza un ticket en el vector store."""
    collection = get_collection()
    collection.upsert(
        ids=[ticket_id],
        embeddings=[embedding],
        documents=[text],
        metadatas=[metadata],
    )
    logger.debug("Upserted ticket %s into ChromaDB", ticket_id)
