"""Node 2.1: Event Structuring (Claude Opus 4.6)."""

import json
import logging

from server.config import settings
from server.workflow.engine import WorkflowNode, registry
from server.workflow.prompts import EVENT_STRUCTURING_PROMPT
from server.workflow.llm_client import chat_completion_json

logger = logging.getLogger(__name__)


class EventStructuringNode(WorkflowNode):
    node_id = "2.1_event_structuring"
    node_name = "事件结构化"
    default_model = settings.modelgate.event_structuring_model

    def get_default_system_prompt(self) -> str:
        return EVENT_STRUCTURING_PROMPT

    async def execute(self, input_data: dict, config: dict) -> dict:
        """Merge fragmented video analyses into coherent life events.

        Input from 1.2, 1.3b, 1.3c.
        Output: structured event list with emotions.
        """
        preprocess_data = input_data.get("1.1_video_preprocess", {})
        visual_data = input_data.get("1.2_visual_understanding", {})
        asr_data = input_data.get("1.3b_asr", {})
        emotion_data = input_data.get("1.3c_emotion_recognition", {})

        videos_meta = preprocess_data.get("videos", [])
        visual_results = visual_data.get("visual_results", [])
        asr_results = asr_data.get("asr_results", [])
        emotion_results = emotion_data.get("emotion_results", [])

        # Extract capture dates from preprocessed videos
        capture_dates = {}
        for v in videos_meta:
            if v.get("capture_date"):
                capture_dates[v["video_id"]] = v["capture_date"]

        # Image analysis results from 1.2
        image_results = visual_data.get("image_results", [])

        # Build per-video combined data
        combined_segments = self._combine_per_video(visual_results, asr_results, emotion_results, capture_dates)

        model = config.get("model", self.default_model)
        system_prompt = config.get("system_prompt", EVENT_STRUCTURING_PROMPT)

        # Build the user message with all data
        user_message = self._build_user_message(combined_segments, image_results)

        result = await chat_completion_json(
            model=model,
            system_prompt=system_prompt,
            user_content=user_message,
            max_tokens=16384,
        )

        return {
            "structured_events": result["data"],
            "token_usage": result["token_usage"],
        }

    def _combine_per_video(self, visual_results, asr_results, emotion_results, capture_dates=None) -> list:
        """Combine visual, ASR, and emotion data by video_id."""
        asr_map = {r["video_id"]: r.get("transcripts", []) for r in asr_results}
        emotion_map = {r["video_id"]: r.get("emotions", []) for r in emotion_results}
        capture_dates = capture_dates or {}

        combined = []
        for vr in visual_results:
            video_id = vr["video_id"]
            combined.append({
                "video_id": video_id,
                "capture_date": capture_dates.get(video_id),
                "visual_analysis": vr.get("analysis"),
                "transcripts": asr_map.get(video_id, []),
                "emotions": emotion_map.get(video_id, []),
            })

        return combined

    def _build_user_message(self, combined_segments: list, image_results: list = None) -> str:
        """Build the user prompt with all segment data."""
        # Determine the date from capture dates
        dates = [seg["capture_date"] for seg in combined_segments if seg.get("capture_date")]
        date_str = dates[0] if dates else "unknown"
        parts = [f"Date of recording: {date_str}\n"]
        parts.append("Here is the data from all video segments and photos recorded on this date:\n")

        for i, seg in enumerate(combined_segments):
            date_info = f", captured: {seg['capture_date']}" if seg.get("capture_date") else ""
            parts.append(f"\n--- Video Segment {i + 1} (ID: {seg['video_id']}{date_info}) ---")

            if seg.get("visual_analysis"):
                parts.append(f"\nVisual Analysis:\n{json.dumps(seg['visual_analysis'], ensure_ascii=False, indent=2)}")

            if seg.get("transcripts"):
                parts.append("\nTranscripts:")
                for t in seg["transcripts"]:
                    speaker_label = "USER" if t.get("is_user") else t.get("speaker", "unknown")
                    parts.append(f"  [{t['start']:.1f}s - {t['end']:.1f}s] {speaker_label}: {t.get('text', '')}")

            if seg.get("emotions"):
                parts.append("\nEmotion Tags:")
                for e in seg["emotions"]:
                    speaker_label = "USER" if e.get("is_user") else e.get("speaker", "unknown")
                    parts.append(
                        f"  [{e['start']:.1f}s - {e['end']:.1f}s] {speaker_label}: "
                        f"{e.get('emotion', 'calm')} (confidence: {e.get('confidence', 0):.2f})"
                    )

        # Append image analysis results
        if image_results:
            completed_images = [img for img in image_results if img.get("status") == "completed"]
            if completed_images:
                parts.append(f"\n\n=== Photos ({len(completed_images)} images) ===")
                for i, img in enumerate(completed_images):
                    parts.append(f"\n--- Photo {i + 1} (ID: {img['image_id']}) ---")
                    if img.get("analysis"):
                        parts.append(f"\nVisual Analysis:\n{json.dumps(img['analysis'], ensure_ascii=False, indent=2)}")

        parts.append("\n\nPlease analyze all the above video segments and photos, and produce the structured event list as specified.")

        return "\n".join(parts)


registry.register(EventStructuringNode())
