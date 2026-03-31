"""Application settings and configuration."""

import os
from dataclasses import dataclass, field


@dataclass
class ModelGateConfig:
    """ModelGate API configuration."""

    api_key: str = os.getenv("MODELGATE_API_KEY", "sk-9c9604ff-8124-42fc-ad94-cd8c6995657f")
    base_url: str = os.getenv("MODELGATE_BASE_URL", "https://mg.aid.pub/v1")

    # Model IDs for each workflow node
    visual_understanding_model: str = "Gemini-2.5-Pro"
    event_structuring_model: str = "Claude-Opus-4.6"
    person_matching_model: str = "Claude-Sonnet-4.6"
    profile_update_model: str = "Claude-Opus-4.6"
    diary_generation_model: str = "Claude-Opus-4.6"
    quality_check_model: str = "Claude-Sonnet-4.6"


@dataclass
class DatabaseConfig:
    """Database configuration."""

    url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://lifelens:lifelens@localhost:5432/lifelens",
    )
    sync_url: str = os.getenv(
        "DATABASE_SYNC_URL",
        "postgresql://lifelens:lifelens@localhost:5432/lifelens",
    )


@dataclass
class StorageConfig:
    """File storage configuration."""

    # Local storage for V1, can switch to S3/MinIO later
    base_dir: str = os.getenv("STORAGE_BASE_DIR", "/Users/bytedance/lifelens/storage")
    videos_dir: str = ""
    frames_dir: str = ""
    audio_dir: str = ""
    clips_dir: str = ""
    thumbnails_dir: str = ""

    def __post_init__(self):
        self.videos_dir = os.path.join(self.base_dir, "videos")
        self.frames_dir = os.path.join(self.base_dir, "frames")
        self.audio_dir = os.path.join(self.base_dir, "audio")
        self.clips_dir = os.path.join(self.base_dir, "clips")
        self.thumbnails_dir = os.path.join(self.base_dir, "thumbnails")

        for d in [
            self.base_dir,
            self.videos_dir,
            self.frames_dir,
            self.audio_dir,
            self.clips_dir,
            self.thumbnails_dir,
        ]:
            os.makedirs(d, exist_ok=True)


@dataclass
class CeleryConfig:
    """Celery configuration."""

    broker_url: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    result_backend: str = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")


@dataclass
class WorkflowConfig:
    """Workflow processing configuration."""

    # Video preprocessing
    frame_extraction_fps: float = 1.0  # frames per second
    thumbnail_width: int = 320
    thumbnail_quality: int = 85

    # Speaker diarization
    voiceprint_similarity_threshold: float = 0.75

    # Emotion recognition
    emotion_confidence_threshold: float = 0.6

    # Person matching
    face_similarity_threshold: float = 0.7
    voice_similarity_threshold: float = 0.75

    # Profile update
    interest_initial_confidence: float = 0.25
    interest_decay_days: int = 30
    recent_focus_window_days: int = 14

    # Diary generation
    min_key_events: int = 3
    max_key_events: int = 10
    recent_diary_context_days: int = 3


@dataclass
class Settings:
    """Root settings container."""

    modelgate: ModelGateConfig = field(default_factory=ModelGateConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    celery: CeleryConfig = field(default_factory=CeleryConfig)
    workflow: WorkflowConfig = field(default_factory=WorkflowConfig)

    debug: bool = os.getenv("DEBUG", "true").lower() == "true"
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))


settings = Settings()
