"""Video upload API endpoints."""

import os
import uuid
import shutil
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from server.config import settings
from server.models.database import get_db
from server.models.video import UploadedVideo, UploadBatch
from server.models.workflow import WorkflowRun, NodeRun
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


@router.post("/image")
async def upload_image(
    profile_id: str = Form(...),
    file: UploadFile = File(...),
    capture_date_str: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """Upload a single image file from phone gallery."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    allowed_types = {"image/jpeg", "image/png", "image/heic", "image/heif", "image/webp"}
    if file.content_type and file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail=f"Unsupported image type: {file.content_type}")

    image_id = uuid.uuid4()
    ext = os.path.splitext(file.filename)[1] or ".jpg"
    stored_filename = f"{image_id}{ext}"
    file_path = os.path.join(settings.storage.frames_dir, stored_filename)

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    file_size = os.path.getsize(file_path)

    capture_date = None
    capture_unknown = True
    if capture_date_str:
        try:
            capture_date = date.fromisoformat(capture_date_str)
            capture_unknown = False
        except ValueError:
            pass

    # Reuse UploadedVideo model with a special status to indicate it's an image
    record = UploadedVideo(
        id=image_id,
        profile_id=uuid.UUID(profile_id),
        filename=file.filename,
        file_path=file_path,
        file_size_bytes=file_size,
        capture_date=capture_date,
        capture_date_unknown=capture_unknown,
        status="uploaded_image",
    )
    db.add(record)
    await db.commit()

    return {"media_id": str(image_id), "filename": file.filename, "type": "image", "status": "uploaded"}


@router.post("/batch", response_model=BatchUploadResponse)
async def create_batch(
    profile_id: str = Form(...),
    video_ids: str = Form("", description="Comma-separated video UUIDs"),
    image_ids: str = Form("", description="Comma-separated image UUIDs"),
    target_date: Optional[str] = Form(None, description="YYYY-MM-DD or empty for unknown"),
    db: AsyncSession = Depends(get_db),
):
    """Create a processing batch from uploaded videos/images and trigger workflow."""
    vid_list = [v.strip() for v in video_ids.split(",") if v.strip()]
    img_list = [v.strip() for v in image_ids.split(",") if v.strip()]
    if not vid_list and not img_list:
        raise HTTPException(status_code=400, detail="No media IDs provided")

    parsed_date = None
    date_unknown = False
    if target_date:
        try:
            parsed_date = date.fromisoformat(target_date)
        except ValueError:
            date_unknown = True
    else:
        date_unknown = True

    all_media_ids = vid_list + img_list
    batch = UploadBatch(
        profile_id=uuid.UUID(profile_id),
        target_date=parsed_date,
        target_date_unknown=date_unknown,
        video_ids=all_media_ids,
        video_count=len(all_media_ids),
        status="pending",
    )
    db.add(batch)
    await db.commit()

    # Trigger async workflow processing
    from server.services.workflow_service import trigger_workflow
    await trigger_workflow(str(batch.id), str(profile_id))

    return BatchUploadResponse(
        batch_id=batch.id,
        video_count=len(all_media_ids),
        target_date=parsed_date,
        status="processing",
    )


@router.post("/voiceprint")
async def upload_voiceprint(
    profile_id: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload a voiceprint audio recording for user identification."""
    from sqlalchemy import select
    from server.models.profile import UserProfile

    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    # Save audio file
    ext = os.path.splitext(file.filename)[1] or ".wav"
    stored_filename = f"voiceprint_{profile_id}{ext}"
    file_path = os.path.join(settings.storage.audio_dir, stored_filename)

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Update profile with voiceprint path
    result = await db.execute(
        select(UserProfile).where(UserProfile.id == uuid.UUID(profile_id))
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    profile.voiceprint_path = file_path
    await db.commit()

    return {"status": "ok", "voiceprint_path": file_path}


@router.get("/batch/{batch_id}/status")
async def get_batch_status(batch_id: str, db: AsyncSession = Depends(get_db)):
    """Get batch processing status including current workflow node."""
    batch_uuid = uuid.UUID(batch_id)

    # Find workflow run for this batch
    result = await db.execute(
        select(WorkflowRun)
        .where(WorkflowRun.batch_id == batch_uuid)
        .options(selectinload(WorkflowRun.node_runs))
    )
    workflow_run = result.scalar_one_or_none()

    if not workflow_run:
        return {"status": "pending", "current_node": None, "completed_nodes": 0, "total_nodes": 12}

    node_runs = workflow_run.node_runs or []
    completed = [nr for nr in node_runs if nr.status == "completed"]
    running = [nr for nr in node_runs if nr.status == "running"]
    failed = [nr for nr in node_runs if nr.status == "failed"]

    current_node = None
    if running:
        current_node = {"node_id": running[0].node_id, "node_name": running[0].node_name}
    elif failed:
        current_node = {"node_id": failed[0].node_id, "node_name": failed[0].node_name}

    return {
        "status": workflow_run.status,
        "current_node": current_node,
        "completed_nodes": len(completed),
        "total_nodes": 12,
        "diary_id": str(workflow_run.diary_id) if workflow_run.diary_id else None,
    }


@router.get("/batches/{profile_id}/active")
async def get_active_batches(profile_id: str, db: AsyncSession = Depends(get_db)):
    """Get all active (non-completed) batches for a profile."""
    profile_uuid = uuid.UUID(profile_id)

    result = await db.execute(
        select(UploadBatch)
        .where(
            UploadBatch.profile_id == profile_uuid,
            UploadBatch.status.in_(["pending", "processing"]),
        )
        .order_by(UploadBatch.created_at.desc())
    )
    batches = result.scalars().all()

    active = []
    for batch in batches:
        # Get workflow status for each batch
        wr_result = await db.execute(
            select(WorkflowRun)
            .where(WorkflowRun.batch_id == batch.id)
            .options(selectinload(WorkflowRun.node_runs))
        )
        workflow_run = wr_result.scalar_one_or_none()

        current_node = None
        completed_nodes = 0
        if workflow_run:
            node_runs = workflow_run.node_runs or []
            completed = [nr for nr in node_runs if nr.status == "completed"]
            running = [nr for nr in node_runs if nr.status == "running"]
            completed_nodes = len(completed)
            if running:
                current_node = {"node_id": running[0].node_id, "node_name": running[0].node_name}

        # Count images vs videos from the batch's media IDs
        media_result = await db.execute(
            select(UploadedVideo).where(UploadedVideo.id.in_(
                [uuid.UUID(mid) for mid in (batch.video_ids or [])]
            ))
        )
        media_items = media_result.scalars().all()
        img_count = sum(1 for m in media_items if m.status == "uploaded_image")
        vid_count = len(media_items) - img_count

        active.append({
            "batch_id": str(batch.id),
            "video_count": batch.video_count,
            "image_count": img_count,
            "pure_video_count": vid_count,
            "status": workflow_run.status if workflow_run else batch.status,
            "current_node": current_node,
            "completed_nodes": completed_nodes,
            "total_nodes": 12,
            "created_at": batch.created_at.isoformat() if batch.created_at else None,
        })

    return active


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
