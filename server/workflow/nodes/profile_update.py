"""Node 3.1: Profile Update (Claude Opus 4.6)."""

import json
import logging

from server.config import settings
from server.workflow.engine import WorkflowNode, registry
from server.workflow.prompts import PROFILE_UPDATE_PROMPT
from server.workflow.llm_client import chat_completion_json

logger = logging.getLogger(__name__)


class ProfileUpdateNode(WorkflowNode):
    node_id = "3.1_profile_update"
    node_name = "用户画像更新"
    default_model = settings.modelgate.profile_update_model

    def get_default_system_prompt(self) -> str:
        return PROFILE_UPDATE_PROMPT

    async def execute(self, input_data: dict, config: dict) -> dict:
        """Analyze today's events and update user profile.

        Input from 2.2 (which carries forward 2.1 data).
        Also needs current user profile.
        Output: profile diff and change signals.
        """
        event_data = input_data.get("2.1_event_structuring", {})
        # Passed through from 2.2
        if "2.2_person_matching" in input_data:
            event_data = input_data.get("2.2_person_matching", {}).get(
                "structured_events", event_data
            )

        structured_events = input_data.get("2.1_event_structuring", {}).get("structured_events", {})
        person_matches = input_data.get("2.2_person_matching", {}).get("person_matches", {})
        current_profile = input_data.get("current_profile", {})

        model = config.get("model", self.default_model)
        system_prompt = config.get("system_prompt", PROFILE_UPDATE_PROMPT)

        user_message = self._build_user_message(structured_events, person_matches, current_profile)

        result = await chat_completion_json(
            model=model,
            system_prompt=system_prompt,
            user_content=user_message,
            max_tokens=8192,
        )

        return {
            "profile_diff": result["data"],
            "token_usage": result["token_usage"],
        }

    def _build_user_message(self, structured_events: dict, person_matches: dict, current_profile: dict) -> str:
        parts = []

        parts.append("## Today's structured events:\n")
        parts.append(json.dumps(structured_events, ensure_ascii=False, indent=2))

        parts.append("\n\n## Person matching results:\n")
        parts.append(json.dumps(person_matches, ensure_ascii=False, indent=2))

        parts.append("\n\n## Current user profile:\n")
        parts.append(json.dumps(current_profile, ensure_ascii=False, indent=2))

        parts.append("\n\nPlease analyze the events and determine what profile updates are needed.")

        return "\n".join(parts)


registry.register(ProfileUpdateNode())
