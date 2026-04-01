"""Node 3.2: Diary Generation (Claude Opus 4.6)."""

import json
import logging

from server.config import settings
from server.workflow.engine import WorkflowNode, registry
from server.workflow.prompts import DIARY_GENERATION_PROMPT
from server.workflow.llm_client import chat_completion_json

logger = logging.getLogger(__name__)


class DiaryGenerationNode(WorkflowNode):
    node_id = "3.2_diary_generation"
    node_name = "日记生成"
    default_model = settings.modelgate.diary_generation_model

    def get_default_system_prompt(self) -> str:
        return DIARY_GENERATION_PROMPT

    async def execute(self, input_data: dict, config: dict) -> dict:
        """Generate the diary entry based on events and profile.

        Input: structured events, updated profile, profile diff (change signals), recent diaries.
        Output: complete diary JSON.
        """
        structured_events = input_data.get("2.1_event_structuring", {}).get("structured_events", {})
        profile_diff = input_data.get("3.1_profile_update", {}).get("profile_diff", {})
        current_profile = input_data.get("current_profile", {})
        recent_diaries = input_data.get("recent_diaries", [])

        model = config.get("model", self.default_model)
        system_prompt = config.get("system_prompt", DIARY_GENERATION_PROMPT)

        user_message = self._build_user_message(
            structured_events, current_profile, profile_diff, recent_diaries
        )

        result = await chat_completion_json(
            model=model,
            system_prompt=system_prompt,
            user_content=user_message,
            max_tokens=16384,
            temperature=0.7,
        )

        diary = result["data"]

        # If JSON parse failed and we got raw_content, try to extract JSON
        if "raw_content" in diary and "insight" not in diary:
            import re
            raw = diary["raw_content"]
            fence_match = re.search(r'```(?:json)?\s*\n([\s\S]*?)\n\s*```', raw)
            if fence_match:
                raw = fence_match.group(1).strip()
            try:
                diary = json.loads(raw)
                logger.info("Recovered diary JSON from raw_content")
            except json.JSONDecodeError:
                logger.warning("Could not parse diary from raw_content")

        return {
            "diary": diary,
            "token_usage": result["token_usage"],
        }

    def _build_user_message(
        self,
        structured_events: dict,
        current_profile: dict,
        profile_diff: dict,
        recent_diaries: list,
    ) -> str:
        parts = []

        parts.append("## Today's structured events:\n")
        parts.append(json.dumps(structured_events, ensure_ascii=False, indent=2))

        parts.append("\n\n## Updated user profile:\n")
        parts.append(json.dumps(current_profile, ensure_ascii=False, indent=2))

        parts.append("\n\n## Profile change signals from today:\n")
        change_signals = profile_diff.get("change_signals", [])
        if change_signals:
            parts.append(json.dumps(change_signals, ensure_ascii=False, indent=2))
        else:
            parts.append("(No significant changes detected today)")

        parts.append("\n\n## Recent diaries (past 3 days) for continuity:\n")
        if recent_diaries:
            for diary in recent_diaries:
                parts.append(f"\n### {diary.get('date', 'unknown')}:")
                parts.append(f"Insight: {diary.get('insight', {}).get('text', 'N/A')}")
                events = diary.get("key_events", [])
                for evt in events[:5]:
                    parts.append(f"- {evt.get('title', '')}: {evt.get('narrative', '')[:100]}")
        else:
            parts.append("(No previous diaries available - this may be the first diary)")

        parts.append("\n\nPlease generate today's diary following the specified format and guidelines.")

        return "\n".join(parts)


registry.register(DiaryGenerationNode())
