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
        visual_data = input_data.get("1.2_visual_understanding", {})
        asr_data = input_data.get("1.3b_asr", {})
        emotion_data = input_data.get("1.3c_emotion_recognition", {})

        visual_results = visual_data.get("visual_results", [])
        asr_results = asr_data.get("asr_results", [])
        emotion_results = emotion_data.get("emotion_results", [])

        # Build per-video combined data
        combined_segments = self._combine_per_video(visual_results, asr_results, emotion_results)

        model = config.get("model", self.default_model)
        system_prompt = config.get("system_prompt", EVENT_STRUCTURING_PROMPT)

        # Build the user message with all data
        user_message = self._build_user_message(combined_segments)

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

    def _combine_per_video(self, visual_results, asr_results, emotion_results) -> list:
        """Combine visual, ASR, and emotion data by video_id."""
        asr_map = {r["video_id"]: r.get("transcripts", []) for r in asr_results}
        emotion_map = {r["video_id"]: r.get("emotions", []) for r in emotion_results}

        combined = []
        for vr in visual_results:
            video_id = vr["video_id"]
            combined.append({
                "video_id": video_id,
                "visual_analysis": vr.get("analysis"),
                "transcripts": asr_map.get(video_id, []),
                "emotions": emotion_map.get(video_id, []),
            })

        return combined

    def _build_user_message(self, combined_segments: list) -> str:
        """Build the user prompt with all segment data."""
        parts = ["Here is the data from all video segments recorded today:\n"]

        for i, seg in enumerate(combined_segments):
            parts.append(f"\n--- Video Segment {i + 1} (ID: {seg['video_id']}) ---")

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

        parts.append("\n\nPlease analyze all the above segments and produce the structured event list as specified.")

        return "\n".join(parts)


registry.register(EventStructuringNode())
