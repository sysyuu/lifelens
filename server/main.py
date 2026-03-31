"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from server.config import settings
from server.api import profile, diary, upload, workflow_debug

app = FastAPI(
    title="LifeLens API",
    description="AI-powered life diary from wearable camera footage",
    version="1.0.0",
)

# CORS for web debug panel and app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static file serving for processed media
app.mount("/media/frames", StaticFiles(directory=settings.storage.frames_dir), name="frames")
app.mount("/media/clips", StaticFiles(directory=settings.storage.clips_dir), name="clips")
app.mount("/media/thumbnails", StaticFiles(directory=settings.storage.thumbnails_dir), name="thumbnails")

# Register routers
app.include_router(profile.router)
app.include_router(diary.router)
app.include_router(upload.router)
app.include_router(workflow_debug.router)


@app.get("/")
async def root():
    return {"app": "LifeLens", "version": "1.0.0", "status": "running"}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.on_event("startup")
async def startup():
    """Initialize database tables on startup."""
    from server.models.database import engine, Base
    # Import all models to register them
    import server.models.profile
    import server.models.diary
    import server.models.video
    import server.models.workflow

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port)
