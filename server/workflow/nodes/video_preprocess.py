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
        """Process uploaded videos and images.

        Input: {"video_paths": [str], "video_ids": [str], "image_paths": [str], "image_ids": [str]}
        Output: {"videos": [{video_id, audio_path, thumbnail_path, duration, metadata}], "images": [{image_id, image_path, status}]}
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

        # Pass through images (no FFmpeg processing needed)
        image_paths = input_data.get("image_paths", [])
        image_ids = input_data.get("image_ids", [])
        image_results = []
        for image_path, image_id in zip(image_paths, image_ids):
            if os.path.exists(image_path):
                image_results.append({
                    "image_id": image_id,
                    "image_path": image_path,
                    "status": "processed",
                    "media_type": "image",
                })
            else:
                logger.error(f"Image file not found: {image_path}")
                image_results.append({
                    "image_id": image_id,
                    "image_path": image_path,
                    "status": "failed",
                    "error": "File not found",
                })

        return {"videos": results, "images": image_results}

    async def _process_single_video(self, video_path: str, video_id: str, config: dict) -> dict:
        """Process a single video file."""
        # Extract metadata (duration, resolution, capture date)
        metadata = self._get_video_metadata(video_path)

        # Compress video for LLM (720p, 800kbps)
        compressed_path = os.path.join(settings.storage.clips_dir, f"{video_id}_compressed.mp4")
        self._compress_video(video_path, compressed_path)

        # Extract audio track
        audio_path = os.path.join(settings.storage.audio_dir, f"{video_id}.wav")
        self._extract_audio(video_path, audio_path)

        # Generate thumbnail
        thumbnail_path = os.path.join(settings.storage.thumbnails_dir, f"{video_id}_thumb.jpg")
        self._generate_thumbnail(video_path, thumbnail_path, config.get("params", {}).get("thumbnail_width", 320))

        return {
            "video_id": video_id,
            "video_path": video_path,
            "compressed_path": compressed_path,
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

    def _compress_video(self, video_path: str, output_path: str):
        """Compress video to 720p / 800kbps for LLM visual understanding."""
        cmd = [
            "ffmpeg", "-y", "-i", video_path,
            "-vf", "scale=-2:720",
            "-c:v", "libx264", "-preset", "fast",
            "-b:v", "800k", "-maxrate", "1200k", "-bufsize", "1600k",
            "-c:a", "aac", "-b:a", "64k", "-ac", "1",
            "-movflags", "+faststart",
            output_path,
        ]
        try:
            subprocess.run(cmd, capture_output=True, timeout=300, check=True)
            compressed_size = os.path.getsize(output_path)
            original_size = os.path.getsize(video_path)
            logger.info(
                f"Compressed video: {original_size / 1024 / 1024:.1f}MB -> "
                f"{compressed_size / 1024 / 1024:.1f}MB"
            )
        except subprocess.CalledProcessError as e:
            logger.error(f"Video compression failed: {e.stderr}")
            # Fallback: copy original
            import shutil
            shutil.copy2(video_path, output_path)

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
