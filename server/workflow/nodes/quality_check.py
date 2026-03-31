"""Node 4.2: Quality Check (Claude Sonnet 4.6)."""

import json
import logging

from server.config import settings
from server.workflow.engine import WorkflowNode, registry
from server.workflow.prompts import QUALITY_CHECK_PROMPT
from server.workflow.llm_client import chat_completion_json

logger = logging.getLogger(__name__)


class QualityCheckNode(WorkflowNode):
    node_id = "4.2_quality_check"
    node_name = "质量检查"
    default_model = settings.modelgate.quality_check_model

    def get_default_system_prompt(self) -> str:
        return QUALITY_CHECK_PROMPT

    async def execute(self, input_data: dict, config: dict) -> dict:
        """Check diary quality before publishing.

        Input from 4.1: diary + processed media.
        Also needs structured events and profile for verification.
        Output: quality verdict and issues.
        """
        media_data = input_data.get("4.1_media_slicing", {})
        diary = media_data.get("diary", {})
        structured_events = input_data.get("2.1_event_structuring", {}).get("structured_events", {})
        current_profile = input_data.get("current_profile", {})

        model = config.get("model", self.default_model)
        system_prompt = config.get("system_prompt", QUALITY_CHECK_PROMPT)

        user_message = self._build_user_message(diary, structured_events, current_profile)

        result = await chat_completion_json(
            model=model,
            system_prompt=system_prompt,
            user_content=user_message,
            max_tokens=4096,
        )

        return {
            "quality_result": result["data"],
            "diary": diary,
            "processed_media": media_data.get("processed_media", []),
            "token_usage": result["token_usage"],
        }

    def _build_user_message(self, diary: dict, structured_events: dict, current_profile: dict) -> str:
        parts = []

        parts.append("## Diary to check:\n")
        parts.append(json.dumps(diary, ensure_ascii=False, indent=2))

        parts.append("\n\n## Original structured events (ground truth):\n")
        parts.append(json.dumps(structured_events, ensure_ascii=False, indent=2))

        parts.append("\n\n## User profile (for personalization verification):\n")
        parts.append(json.dumps(current_profile, ensure_ascii=False, indent=2))

        parts.append("\n\nPlease check this diary for quality issues as specified.")

        return "\n".join(parts)


registry.register(QualityCheckNode())
