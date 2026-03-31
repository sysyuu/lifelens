"""Node 4.1: Media Slicing (FFmpeg) - Extract keyframes and video clips."""

import os
import logging
import subprocess
import uuid as uuid_mod

from server.config import settings
from server.workflow.engine import WorkflowNode, registry

logger = logging.getLogger(__name__)


class MediaSlicingNode(WorkflowNode):
    node_id = "4.1_media_slicing"
    node_name = "媒体切片生成"
    default_model = None  # Non-AI node

    async def execute(self, input_data: dict, config: dict) -> dict:
        """Extract keyframes and video clips referenced in the diary.

        Input from 3.2: diary with media references (source_video_id + timestamp/clip_range).
        Output: processed media files with URLs ready for app display.
        """
        diary_data = input_data.get("3.2_diary_generation", {})
        diary = diary_data.get("diary", {})

        # Collect all media references from diary
        media_refs = self._collect_media_refs(diary)

        # Build video path map
        preprocess_data = input_data.get("1.1_video_preprocess", {})
        videos = preprocess_data.get("videos", [])
        video_path_map = {v["video_id"]: v["video_path"] for v in videos if v.get("status") == "processed"}

        processed_media = []
        for ref in media_refs:
            source_video_id = ref.get("source_video_id")
            video_path = video_path_map.get(source_video_id)

            if not video_path or not os.path.exists(video_path):
                logger.warning(f"Source video not found: {source_video_id}")
                continue

            try:
                if ref.get("type") == "keyframe":
                    result = self._extract_keyframe(video_path, ref, source_video_id)
                elif ref.get("type") == "video_clip":
                    result = self._extract_clip(video_path, ref, source_video_id)
                else:
                    continue

                processed_media.append(result)
            except Exception as e:
                logger.error(f"Media slicing failed for {ref}: {e}")

        return {
            "processed_media": processed_media,
            "diary": diary,
        }

    def _collect_media_refs(self, diary: dict) -> list:
        """Collect all media references from diary."""
        refs = []

        # Insight media
        insight = diary.get("insight", {})
        if insight.get("media") and insight["media"].get("type"):
            refs.append({**insight["media"], "context": "insight"})

        # Key event media
        for event in diary.get("key_events", []):
            for media in event.get("media", []):
                if media.get("type"):
                    refs.append({**media, "context": f"event_{event.get('event_id', '')}"})

        return refs

    def _extract_keyframe(self, video_path: str, ref: dict, source_video_id: str) -> dict:
        """Extract a single frame as JPEG."""
        timestamp = ref.get("timestamp", 0)
        output_id = str(uuid_mod.uuid4())[:8]
        output_path = os.path.join(
            settings.storage.frames_dir,
            f"{source_video_id}_{output_id}.jpg",
        )

        cmd = [
            "ffmpeg", "-y",
            "-ss", str(timestamp),
            "-i", video_path,
            "-frames:v", "1",
            "-q:v", "2",
            output_path,
        ]
        subprocess.run(cmd, capture_output=True, timeout=30, check=True)

        # Generate thumbnail
        thumb_path = os.path.join(
            settings.storage.thumbnails_dir,
            f"{source_video_id}_{output_id}_thumb.jpg",
        )
        cmd_thumb = [
            "ffmpeg", "-y",
            "-i", output_path,
            "-vf", "scale=320:-1",
            thumb_path,
        ]
        subprocess.run(cmd_thumb, capture_output=True, timeout=15, check=True)

        return {
            "ref_context": ref.get("context"),
            "type": "keyframe",
            "url": f"/media/frames/{os.path.basename(output_path)}",
            "thumbnail_url": f"/media/thumbnails/{os.path.basename(thumb_path)}",
            "source_video_id": source_video_id,
            "timestamp": timestamp,
        }

    def _extract_clip(self, video_path: str, ref: dict, source_video_id: str) -> dict:
        """Extract a video clip."""
        clip_range = ref.get("clip_range", [0, 5])
        start = clip_range[0] if len(clip_range) > 0 else 0
        end = clip_range[1] if len(clip_range) > 1 else start + 5
        duration = end - start

        output_id = str(uuid_mod.uuid4())[:8]
        output_path = os.path.join(
            settings.storage.clips_dir,
            f"{source_video_id}_{output_id}.mp4",
        )

        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start),
            "-i", video_path,
            "-t", str(duration),
            "-c:v", "libx264", "-c:a", "aac",
            "-preset", "fast",
            output_path,
        ]
        subprocess.run(cmd, capture_output=True, timeout=60, check=True)

        # Generate thumbnail from clip
        thumb_path = os.path.join(
            settings.storage.thumbnails_dir,
            f"{source_video_id}_{output_id}_clip_thumb.jpg",
        )
        cmd_thumb = [
            "ffmpeg", "-y",
            "-i", output_path,
            "-vf", "thumbnail,scale=320:-1",
            "-frames:v", "1",
            thumb_path,
        ]
        subprocess.run(cmd_thumb, capture_output=True, timeout=15, check=True)

        return {
            "ref_context": ref.get("context"),
            "type": "video_clip",
            "url": f"/media/clips/{os.path.basename(output_path)}",
            "thumbnail_url": f"/media/thumbnails/{os.path.basename(thumb_path)}",
            "source_video_id": source_video_id,
            "clip_start": start,
            "clip_end": end,
        }


registry.register(MediaSlicingNode())
