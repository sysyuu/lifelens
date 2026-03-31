"""Video upload API endpoints."""

import os
import uuid
import shutil
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession

from server.config import settings
from server.models.database import get_db
from server.models.video import UploadedVideo, UploadBatch
from server.api.schemas import VideoUploadResponse, BatchUploadResponse

router = APIRouter(prefix="/api/upload", tags=["upload"])


@router.post("/video", response_model=VideoUploadResponse)
async def upload_video(
    profile_id: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload a single video file from phone gallery."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    # Validate file type
    allowed_types = {"video/mp4", "video/quicktime", "video/x-msvideo", "video/webm"}
    if file.content_type and file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {file.content_type}")

    # Generate unique filename
    video_id = uuid.uuid4()
    ext = os.path.splitext(file.filename)[1] or ".mp4"
    stored_filename = f"{video_id}{ext}"
    file_path = os.path.join(settings.storage.videos_dir, stored_filename)

    # Save file
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    file_size = os.path.getsize(file_path)

    # Try to extract capture date from video metadata
    capture_date, capture_unknown = _extract_capture_date(file_path)

    # Create database record
    video = UploadedVideo(
        id=video_id,
        profile_id=uuid.UUID(profile_id),
        filename=file.filename,
        file_path=file_path,
        file_size_bytes=file_size,
        capture_date=capture_date,
        capture_date_unknown=capture_unknown,
    )
    db.add(video)
    await db.commit()

    return VideoUploadResponse(
        video_id=video_id,
        filename=file.filename,
        capture_date=capture_date,
        capture_date_unknown=capture_unknown,
        status="uploaded",
    )


@router.post("/batch", response_model=BatchUploadResponse)
async def create_batch(
    profile_id: str = Form(...),
    video_ids: str = Form(..., description="Comma-separated video UUIDs"),
    target_date: Optional[str] = Form(None, description="YYYY-MM-DD or empty for unknown"),
    db: AsyncSession = Depends(get_db),
):
    """Create a processing batch from uploaded videos and trigger workflow."""
    vid_list = [v.strip() for v in video_ids.split(",") if v.strip()]
    if not vid_list:
        raise HTTPException(status_code=400, detail="No video IDs provided")

    parsed_date = None
    date_unknown = False
    if target_date:
        try:
            parsed_date = date.fromisoformat(target_date)
        except ValueError:
            date_unknown = True
    else:
        date_unknown = True

    batch = UploadBatch(
        profile_id=uuid.UUID(profile_id),
        target_date=parsed_date,
        target_date_unknown=date_unknown,
        video_ids=vid_list,
        video_count=len(vid_list),
        status="pending",
    )
    db.add(batch)
    await db.commit()

    # Trigger async workflow processing
    from server.services.workflow_service import trigger_workflow
    await trigger_workflow(str(batch.id), str(profile_id))

    return BatchUploadResponse(
        batch_id=batch.id,
        video_count=len(vid_list),
        target_date=parsed_date,
        status="processing",
    )


def _extract_capture_date(file_path: str) -> tuple[Optional[date], bool]:
    """Try to extract capture date from video metadata."""
    import subprocess
    import json
    from datetime import datetime

    try:
        cmd = [
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            file_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        probe = json.loads(result.stdout)
        tags = probe.get("format", {}).get("tags", {})

        for key in ["creation_time", "date", "com.apple.quicktime.creationdate"]:
            if key in tags:
                dt = datetime.fromisoformat(tags[key].replace("Z", "+00:00"))
                return dt.date(), False
    except Exception:
        pass

    return None, True
