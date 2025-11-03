"""FastAPI application entry for mindiv.
- OpenAI-compatible endpoints: /v1/chat/completions and /v1/responses
- Engines endpoints: /mindiv/deepthink, /mindiv/ultrathink
"""
from contextlib import asynccontextmanager
import logging
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from mindiv.config import get_config, set_config, load_config
from mindiv.providers.registry import register_builtin_providers
from mindiv.api.v1 import chat, responses, models, engines


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger = logging.getLogger(__name__)
    logger.info("Starting mindiv service...")

    # Load configuration
    config_path = Path("mindiv/config/config.yaml")
    pricing_path = Path("mindiv/config/pricing.yaml")

    if config_path.exists():
        cfg = load_config(config_path, pricing_path)
        set_config(cfg)
        logger.info(f"Loaded configuration from {config_path}")
    else:
        logger.warning(f"Config file not found: {config_path}, using defaults")

    cfg = get_config()

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, cfg.log_level, logging.INFO),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Register providers
    register_builtin_providers()
    logger.info("Registered built-in providers")

    logger.info(f"Available models: {cfg.list_models()}")
    logger.info("mindiv service started successfully")

    try:
        yield
    finally:
        logger.info("Shutting down mindiv service...")


app = FastAPI(
    title="mindiv",
    description="AI agent backend for math/physics reasoning with DeepThink/UltraThink",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(chat.router, tags=["Chat"])
app.include_router(responses.router, tags=["Responses"])
app.include_router(models.router, tags=["Models"])
app.include_router(engines.router, tags=["Engines"])


@app.get("/")
async def root():
    cfg = get_config()
    return {
        "name": "mindiv",
        "version": "0.1.0",
        "endpoints": {
            "chat": "/v1/chat/completions",
            "responses": "/v1/responses",
            "models": "/v1/models",
            "deepthink": "/mindiv/deepthink",
            "ultrathink": "/mindiv/ultrathink",
        },
        "models": list(cfg.models.keys())
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}

