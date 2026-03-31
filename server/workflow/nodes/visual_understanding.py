"""Node 1.2: Visual Understanding (Gemini 2.5 Pro)."""

import logging

from server.config import settings
from server.workflow.engine import WorkflowNode, registry
from server.workflow.prompts import VISUAL_UNDERSTANDING_PROMPT
from server.workflow.llm_client import vision_completion, encode_video_base64

logger = logging.getLogger(__name__)


class VisualUnderstandingNode(WorkflowNode):
    node_id = "1.2_visual_understanding"
    node_name = "画面理解"
    default_model = settings.modelgate.visual_understanding_model

    def get_default_system_prompt(self) -> str:
        return VISUAL_UNDERSTANDING_PROMPT

    async def execute(self, input_data: dict, config: dict) -> dict:
        """Analyze each video's visual content using Gemini 2.5 Pro.

        Input from 1.1: {"1.1_video_preprocess": {"videos": [...]}}
        Output: {"visual_results": [{video_id, analysis}]}
        """
        preprocess_data = input_data.get("1.1_video_preprocess", {})
        videos = preprocess_data.get("videos", [])
        model = config.get("model", self.default_model)
        system_prompt = config.get("system_prompt", VISUAL_UNDERSTANDING_PROMPT)

        results = []
        total_tokens = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

        for video in videos:
            if video.get("status") != "processed":
                continue

            video_id = video["video_id"]
            video_path = video["video_path"]

            try:
                # Encode video as base64 for Gemini
                video_b64 = encode_video_base64(video_path)

                additional_text = "Please analyze this 15-second wearable camera video clip and extract all details as specified."

                result = await vision_completion(
                    model=model,
                    system_prompt=system_prompt,
                    video_base64=video_b64,
                    additional_text=additional_text,
                )

                # Accumulate token usage
                usage = result.get("token_usage", {})
                for key in total_tokens:
                    total_tokens[key] += usage.get(key, 0)

                results.append({
                    "video_id": video_id,
                    "analysis": result["data"],
                    "status": "completed",
                })

            except Exception as e:
                logger.error(f"Visual understanding failed for video {video_id}: {e}")
                results.append({
                    "video_id": video_id,
                    "analysis": None,
                    "status": "failed",
                    "error": str(e),
                })

        return {
            "visual_results": results,
            "token_usage": total_tokens,
        }


registry.register(VisualUnderstandingNode())
