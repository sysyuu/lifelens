"""Node 2.2: Person Identification & Matching (Claude Sonnet 4.6)."""

import json
import logging

from server.config import settings
from server.workflow.engine import WorkflowNode, registry
from server.workflow.prompts import PERSON_MATCHING_PROMPT
from server.workflow.llm_client import chat_completion_json

logger = logging.getLogger(__name__)


class PersonMatchingNode(WorkflowNode):
    node_id = "2.2_person_matching"
    node_name = "人物识别与匹配"
    default_model = settings.modelgate.person_matching_model

    def get_default_system_prompt(self) -> str:
        return PERSON_MATCHING_PROMPT

    async def execute(self, input_data: dict, config: dict) -> dict:
        """Match people from today's events against existing social contacts.

        Input from 2.1: structured events with people info.
        Also needs current social contacts from user profile.
        Output: matching results and new person records.
        """
        event_data = input_data.get("2.1_event_structuring", {})
        structured_events = event_data.get("structured_events", {})

        # Extract all people from events
        event_people = self._extract_people_from_events(structured_events)

        if not event_people:
            return {
                "person_matches": {"matches": [], "new_persons": []},
                "token_usage": {},
            }

        # Load existing social contacts (passed as part of context)
        existing_contacts = input_data.get("existing_contacts", [])

        model = config.get("model", self.default_model)
        system_prompt = config.get("system_prompt", PERSON_MATCHING_PROMPT)

        user_message = self._build_user_message(event_people, existing_contacts)

        result = await chat_completion_json(
            model=model,
            system_prompt=system_prompt,
            user_content=user_message,
            max_tokens=8192,
        )

        return {
            "person_matches": result["data"],
            "token_usage": result["token_usage"],
        }

    def _extract_people_from_events(self, structured_events: dict) -> list:
        """Extract unique people from all events."""
        events = structured_events.get("events", [])
        people = []
        seen = set()

        for event in events:
            for person in event.get("people", []):
                person_key = person.get("person_index", "")
                if person_key and person_key not in seen:
                    seen.add(person_key)
                    people.append({
                        **person,
                        "appeared_in_events": [event.get("event_id")],
                        "scene_context": event.get("location", ""),
                    })
                elif person_key in seen:
                    # Add event reference to existing person
                    for p in people:
                        if p.get("person_index") == person_key:
                            p["appeared_in_events"].append(event.get("event_id"))

        return people

    def _build_user_message(self, event_people: list, existing_contacts: list) -> str:
        """Build user prompt with people data and existing contacts."""
        parts = []

        parts.append("## People appearing in today's events:\n")
        parts.append(json.dumps(event_people, ensure_ascii=False, indent=2))

        parts.append("\n\n## Existing social contacts in user's profile:\n")
        if existing_contacts:
            parts.append(json.dumps(existing_contacts, ensure_ascii=False, indent=2))
        else:
            parts.append("(No existing contacts yet - this may be a new user)")

        parts.append("\n\nPlease match today's people against existing contacts and identify any new persons.")

        return "\n".join(parts)


registry.register(PersonMatchingNode())
