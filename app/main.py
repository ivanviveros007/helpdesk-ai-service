import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.api.v1.router import router as v1_router

# Setup logging before anything else
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicializa recursos al arrancar y los libera al cerrar."""
    settings = get_settings()
    logger.info("Starting %s on port %d", settings.app_name, settings.port)

    # Warm up ChromaDB collection
    from app.rag.vector_store import get_collection
    get_collection()

    # Warm up embeddings model
    from app.pipeline.embedder import get_embeddings_model
    get_embeddings_model()

    # Warm up agent
    from app.agent.agent import get_agent
    get_agent()

    logger.info("All components initialized — ready to serve")
    yield
    logger.info("Shutting down %s", settings.app_name)


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Helpdesk AI Service",
        description="Agente de IA para clasificación y asignación automática de tickets de soporte.",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["POST", "GET"],
        allow_headers=["*"],
    )

    app.include_router(v1_router)

    @app.get("/health", tags=["health"])
    async def health_check():
        return {"status": "ok", "service": settings.app_name}

    return app


app = create_app()
