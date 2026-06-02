from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.config import FRONTEND_DIR, SETTINGS, ensure_folders
from backend.routes.generate import router as generate_router


def create_app() -> FastAPI:
    ensure_folders()

    app = FastAPI(
        title="AI Handwritten Assignment Generator",
        description="Generate downloadable handwritten assignment PDFs from text or PDF input.",
        version="2.0.0",
    )

    allow_origins = list(SETTINGS.cors_origins) or ["*"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Job-Id", "X-Total-Pages", "X-Generation-Mode", "X-Fallback-Used"],
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(generate_router)

    if FRONTEND_DIR.exists():
        app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")

    return app


app = create_app()
