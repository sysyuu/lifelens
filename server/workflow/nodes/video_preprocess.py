"""Node 1.1: Video Preprocessing (FFmpeg)."""

import os
import json
import uuid
import logging
import subprocess
from datetime import datetime

from server.config import settings
from server.workflow.engine import WorkflowNode, registry

logger = logging.getLogger(__name__)


class VideoPreprocessNode(WorkflowNode):
    node_id = "1.1_video_preprocess"
    node_name = "视频预处理"
    default_model = None  # Non-AI node

    def get_default_config(self) -> dict:
        return {
            "frame_fps": settings.workflow.frame_extraction_fps,
            "thumbnail_width": settings.workflow.thumbnail_width,
        }

    async def execute(self, input_data: dict, config: dict) -> dict:
        """Process uploaded videos: extract audio, generate thumbnails, get metadata.

        Input: {"video_paths": [str], "video_ids": [str]}
        Output: {"videos": [{video_id, audio_path, thumbnail_path, duration, metadata}]}
        """
        video_paths = input_data.get("video_paths", [])
        video_ids = input_data.get("video_ids", [])

        results = []
        for video_path, video_id in zip(video_paths, video_ids):
            try:
                result = await self._process_single_video(video_path, video_id, config)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to preprocess video {video_id}: {e}")
                results.append({
                    "video_id": video_id,
                    "video_path": video_path,
                    "status": "failed",
                    "error": str(e),
                })

        return {"videos": results}

    async def _process_single_video(self, video_path: str, video_id: str, config: dict) -> dict:
        """Process a single video file."""
        base_name = os.path.splitext(os.path.basename(video_path))[0]

        # Extract metadata (duration, resolution, capture date)
        metadata = self._get_video_metadata(video_path)

        # Extract audio track
        audio_path = os.path.join(settings.storage.audio_dir, f"{video_id}.wav")
        self._extract_audio(video_path, audio_path)

        # Generate thumbnail
        thumbnail_path = os.path.join(settings.storage.thumbnails_dir, f"{video_id}_thumb.jpg")
        self._generate_thumbnail(video_path, thumbnail_path, config.get("params", {}).get("thumbnail_width", 320))

        return {
            "video_id": video_id,
            "video_path": video_path,
            "audio_path": audio_path,
            "thumbnail_path": thumbnail_path,
            "duration": metadata.get("duration"),
            "resolution": metadata.get("resolution"),
            "capture_date": metadata.get("capture_date"),
            "status": "processed",
        }

    def _get_video_metadata(self, video_path: str) -> dict:
        """Extract video metadata using ffprobe."""
        try:
            cmd = [
                "ffprobe", "-v", "quiet",
                "-print_format", "json",
                "-show_format", "-show_streams",
                video_path,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            probe = json.loads(result.stdout)

            # Extract duration
            duration = float(probe.get("format", {}).get("duration", 0))

            # Extract resolution from video stream
            resolution = None
            for stream in probe.get("streams", []):
                if stream.get("codec_type") == "video":
                    w = stream.get("width")
                    h = stream.get("height")
                    if w and h:
                        resolution = f"{w}x{h}"
                    break

            # Try to extract capture date from metadata
            capture_date = None
            tags = probe.get("format", {}).get("tags", {})
            for key in ["creation_time", "date", "com.apple.quicktime.creationdate"]:
                if key in tags:
                    try:
                        dt = datetime.fromisoformat(tags[key].replace("Z", "+00:00"))
                        capture_date = dt.strftime("%Y-%m-%d")
                    except (ValueError, AttributeError):
                        pass
                    break

            return {
                "duration": duration,
                "resolution": resolution,
                "capture_date": capture_date,
            }
        except Exception as e:
            logger.error(f"ffprobe failed for {video_path}: {e}")
            return {}

    def _extract_audio(self, video_path: str, audio_path: str):
        """Extract audio track as WAV."""
        cmd = [
            "ffmpeg", "-y", "-i", video_path,
            "-vn", "-acodec", "pcm_s16le",
            "-ar", "16000", "-ac", "1",
            audio_path,
        ]
        subprocess.run(cmd, capture_output=True, timeout=60, check=True)

    def _generate_thumbnail(self, video_path: str, thumbnail_path: str, width: int = 320):
        """Generate a thumbnail from the middle of the video."""
        cmd = [
            "ffmpeg", "-y", "-i", video_path,
            "-vf", f"thumbnail,scale={width}:-1",
            "-frames:v", "1",
            thumbnail_path,
        ]
        subprocess.run(cmd, capture_output=True, timeout=30, check=True)


# Register
registry.register(VideoPreprocessNode())
