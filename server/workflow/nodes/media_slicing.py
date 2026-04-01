"""Node 4.1: Media Slicing (FFmpeg) - Extract keyframes and video clips."""

import os
import logging
import subprocess
import uuid as uuid_mod
from difflib import SequenceMatcher

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

        # Recover diary from raw_content if JSON parse failed upstream
        if ("raw_content" in diary_data or "raw_content" in diary) and "key_events" not in diary:
            raw = diary_data.get("raw_content") or diary.get("raw_content", "")
            if raw:
                import re, json as _json
                logger.info(f"Diary has raw_content (len={len(raw)}), attempting recovery in 4.1")
                fence_match = re.search(r'```(?:json)?\s*\n([\s\S]*?)\n\s*```', raw)
                if fence_match:
                    raw = fence_match.group(1).strip()
                try:
                    diary = _json.loads(raw)
                    logger.info(f"Recovered diary from raw_content, keys: {list(diary.keys())}")
                except _json.JSONDecodeError:
                    try:
                        from server.workflow.llm_client import _fix_llm_json
                        diary = _json.loads(_fix_llm_json(raw))
                        logger.info(f"Recovered diary after JSON fix, keys: {list(diary.keys())}")
                    except Exception as e:
                        logger.error(f"Could not recover diary from raw_content: {e}")

        # Collect all media references from diary
        media_refs = self._collect_media_refs(diary)
        logger.info(f"Collected {len(media_refs)} media references from diary")

        # Build video path map from 1.1 preprocess output
        preprocess_data = input_data.get("1.1_video_preprocess", {})
        videos = preprocess_data.get("videos", [])
        video_path_map = {
            v["video_id"]: v["video_path"]
            for v in videos
            if v.get("status") == "processed"
        }
        logger.info(f"Available videos: {list(video_path_map.keys())}")

        # Also build a list of all valid video paths (for fallback)
        all_video_paths = [
            (vid, path) for vid, path in video_path_map.items()
            if os.path.exists(path)
        ]

        if not all_video_paths:
            logger.warning("No valid video files found on disk — skipping media slicing")
            return {"processed_media": [], "diary": diary}

        processed_media = []
        for ref in media_refs:
            source_video_id = ref.get("source_video_id", "")
            video_path = self._resolve_video_path(
                source_video_id, video_path_map, all_video_paths
            )

            if not video_path:
                logger.warning(
                    f"Could not resolve video for source_video_id={source_video_id}, "
                    f"using first available video as fallback"
                )
                fallback_vid, video_path = all_video_paths[0]
                source_video_id = fallback_vid

            # Get video duration to clamp timestamps
            duration = self._get_video_duration(video_path)

            try:
                if ref.get("type") == "video_clip":
                    result = self._extract_clip(video_path, ref, source_video_id, duration)
                else:
                    # Default to keyframe extraction (safer)
                    result = self._extract_keyframe(video_path, ref, source_video_id, duration)

                processed_media.append(result)
                logger.info(f"Generated {result['type']}: {result['url']}")
            except Exception as e:
                logger.error(f"Media slicing failed for ref {ref.get('context', '?')}: {e}")

        # If diary had events but no media refs (LLM didn't generate any),
        # generate fallback keyframes — one per event from available videos
        if not media_refs and diary.get("key_events"):
            logger.info("No media refs in diary — generating fallback keyframes for events")
            processed_media = self._generate_fallback_media(diary, all_video_paths)

        logger.info(f"Media slicing complete: {len(processed_media)} items generated")
        return {
            "processed_media": processed_media,
            "diary": diary,
        }

    def _resolve_video_path(
        self, source_video_id: str, video_path_map: dict, all_video_paths: list
    ) -> str | None:
        """Resolve a source_video_id to a file path with fuzzy matching.

        LLMs often garble UUIDs — try multiple matching strategies.
        """
        if not source_video_id:
            return None

        # Strategy 1: Exact match
        if source_video_id in video_path_map:
            path = video_path_map[source_video_id]
            if os.path.exists(path):
                return path

        # Strategy 2: Case-insensitive / stripped match
        normalized = source_video_id.strip().lower().replace("-", "")
        for vid, path in video_path_map.items():
            if vid.lower().replace("-", "") == normalized:
                if os.path.exists(path):
                    return path

        # Strategy 3: Prefix match (LLM may have truncated the UUID)
        for vid, path in video_path_map.items():
            if vid.startswith(source_video_id[:8]) or source_video_id.startswith(vid[:8]):
                if os.path.exists(path):
                    logger.info(f"Prefix-matched video: {source_video_id[:8]}... → {vid}")
                    return path

        # Strategy 4: Best fuzzy match (similarity > 0.6)
        best_score = 0.0
        best_path = None
        for vid, path in video_path_map.items():
            score = SequenceMatcher(None, source_video_id, vid).ratio()
            if score > best_score:
                best_score = score
                best_path = path if os.path.exists(path) else None

        if best_score > 0.6 and best_path:
            logger.info(f"Fuzzy-matched video: {source_video_id} → score={best_score:.2f}")
            return best_path

        return None

    def _get_video_duration(self, video_path: str) -> float:
        """Get video duration in seconds using ffprobe."""
        try:
            cmd = [
                "ffprobe", "-v", "quiet",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                video_path,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            return float(result.stdout.strip())
        except Exception:
            return 15.0  # Default to 15s for Insta Go3S clips

    def _clamp_timestamp(self, ts: float, duration: float) -> float:
        """Clamp a timestamp to valid range within the video."""
        if ts < 0 or ts >= duration:
            # Use middle of video as safe default
            return duration / 2
        return ts

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

    def _extract_keyframe(self, video_path: str, ref: dict, source_video_id: str, duration: float) -> dict:
        """Extract a single frame as JPEG."""
        timestamp = ref.get("timestamp", 0)
        timestamp = self._clamp_timestamp(float(timestamp), duration)

        output_id = str(uuid_mod.uuid4())[:8]
        output_path = os.path.join(
            settings.storage.frames_dir,
            f"{source_video_id[:8]}_{output_id}.jpg",
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
            f"{source_video_id[:8]}_{output_id}_thumb.jpg",
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

    def _extract_clip(self, video_path: str, ref: dict, source_video_id: str, duration: float) -> dict:
        """Extract a video clip."""
        clip_range = ref.get("clip_range", [0, 5])
        start = float(clip_range[0]) if len(clip_range) > 0 else 0
        end = float(clip_range[1]) if len(clip_range) > 1 else start + 5

        # Clamp to valid range
        start = max(0, min(start, duration - 0.5))
        end = max(start + 0.5, min(end, duration))
        clip_duration = end - start

        output_id = str(uuid_mod.uuid4())[:8]
        output_path = os.path.join(
            settings.storage.clips_dir,
            f"{source_video_id[:8]}_{output_id}.mp4",
        )

        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start),
            "-i", video_path,
            "-t", str(clip_duration),
            "-c:v", "libx264", "-c:a", "aac",
            "-preset", "fast",
            output_path,
        ]
        subprocess.run(cmd, capture_output=True, timeout=60, check=True)

        # Generate thumbnail from clip
        thumb_path = os.path.join(
            settings.storage.thumbnails_dir,
            f"{source_video_id[:8]}_{output_id}_clip_thumb.jpg",
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

    def _generate_fallback_media(self, diary: dict, all_video_paths: list) -> list:
        """Generate one keyframe per key event when the LLM didn't produce media refs.

        Distributes available videos evenly across events.
        """
        events = diary.get("key_events", [])
        if not events:
            return []

        results = []
        for i, event in enumerate(events):
            # Round-robin across available videos
            vid, path = all_video_paths[i % len(all_video_paths)]
            duration = self._get_video_duration(path)

            ref = {
                "type": "keyframe",
                "source_video_id": vid,
                "timestamp": duration / 2,  # Middle of clip
                "context": f"event_{event.get('event_id', str(i))}",
            }

            try:
                result = self._extract_keyframe(path, ref, vid, duration)
                results.append(result)
            except Exception as e:
                logger.error(f"Fallback keyframe extraction failed: {e}")

        return results


registry.register(MediaSlicingNode())
