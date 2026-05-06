"""Node 1.2: Visual Understanding (Gemini 2.5 Pro)."""

import asyncio
import logging

from server.config import settings
from server.workflow.engine import WorkflowNode, registry
from server.workflow.prompts import VISUAL_UNDERSTANDING_PROMPT
from server.workflow.llm_client import vision_completion, encode_video_base64

logger = logging.getLogger(__name__)

# Max concurrent API calls to avoid rate limiting
MAX_CONCURRENCY = 4


class VisualUnderstandingNode(WorkflowNode):
    node_id = "1.2_visual_understanding"
    node_name = "画面理解"
    default_model = settings.modelgate.visual_understanding_model

    def get_default_system_prompt(self) -> str:
        return VISUAL_UNDERSTANDING_PROMPT

    async def execute(self, input_data: dict, config: dict) -> dict:
        """Analyze each video and image's visual content using Gemini 2.5 Pro.

        Input from 1.1: {"1.1_video_preprocess": {"videos": [...], "images": [...]}}
        Output: {"visual_results": [{video_id, analysis}], "image_results": [{image_id, analysis}]}
        """
        preprocess_data = input_data.get("1.1_video_preprocess", {})
        videos = preprocess_data.get("videos", [])
        images = preprocess_data.get("images", [])
        model = config.get("model", self.default_model)
        system_prompt = config.get("system_prompt", VISUAL_UNDERSTANDING_PROMPT)

        # Filter to processed videos only
        processable = [v for v in videos if v.get("status") == "processed"]
        processable_images = [img for img in images if img.get("status") == "processed"]

        # Process concurrently with semaphore
        semaphore = asyncio.Semaphore(MAX_CONCURRENCY)
        total_tokens = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

        async def process_video(video):
            async with semaphore:
                return await self._process_single_video(video, model, system_prompt)

        async def process_image(image):
            async with semaphore:
                return await self._process_single_image(image, model, system_prompt)

        # Process videos
        video_tasks = [process_video(v) for v in processable]
        video_raw = await asyncio.gather(*video_tasks, return_exceptions=True)

        results = []
        for video, result in zip(processable, video_raw):
            if isinstance(result, Exception):
                logger.error(f"Visual understanding failed for video {video['video_id']}: {result}")
                results.append({
                    "video_id": video["video_id"],
                    "analysis": None,
                    "status": "failed",
                    "error": str(result),
                })
            else:
                usage = result.get("token_usage", {})
                for key in total_tokens:
                    total_tokens[key] += usage.get(key, 0)
                results.append({
                    "video_id": video["video_id"],
                    "analysis": result["data"],
                    "status": "completed",
                })

        # Process images
        image_tasks = [process_image(img) for img in processable_images]
        image_raw = await asyncio.gather(*image_tasks, return_exceptions=True)

        image_results = []
        for image, result in zip(processable_images, image_raw):
            if isinstance(result, Exception):
                logger.error(f"Visual understanding failed for image {image['image_id']}: {result}")
                image_results.append({
                    "image_id": image["image_id"],
                    "analysis": None,
                    "status": "failed",
                    "error": str(result),
                })
            else:
                usage = result.get("token_usage", {})
                for key in total_tokens:
                    total_tokens[key] += usage.get(key, 0)
                image_results.append({
                    "image_id": image["image_id"],
                    "analysis": result["data"],
                    "status": "completed",
                })

        return {
            "visual_results": results,
            "image_results": image_results,
            "token_usage": total_tokens,
        }

    async def _process_single_video(self, video: dict, model: str, system_prompt: str) -> dict:
        """Process a single video through LLM."""
        video_id = video["video_id"]
        video_path = video.get("compressed_path") or video["video_path"]

        logger.info(f"Processing video {video_id} with {video_path}")
        video_b64 = encode_video_base64(video_path)

        additional_text = "Please analyze this wearable camera video clip and extract all details as specified."

        result = await vision_completion(
            model=model,
            system_prompt=system_prompt,
            video_base64=video_b64,
            additional_text=additional_text,
        )
        return result

    async def _process_single_image(self, image: dict, model: str, system_prompt: str) -> dict:
        """Process a single image through LLM."""
        image_id = image["image_id"]
        image_path = image["image_path"]

        logger.info(f"Processing image {image_id} with {image_path}")
        image_b64 = encode_video_base64(image_path)  # same base64 encoding

        # Determine MIME type from extension
        ext = image_path.rsplit('.', 1)[-1].lower() if '.' in image_path else 'jpg'
        mime_map = {'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'png': 'image/png', 'heic': 'image/heic', 'webp': 'image/webp'}
        mime_type = mime_map.get(ext, 'image/jpeg')

        additional_text = "Please analyze this photo taken by a wearable camera or phone and extract all details as specified. This is a single image (not a video), so describe the scene captured in this moment."

        result = await vision_completion(
            model=model,
            system_prompt=system_prompt,
            video_base64=image_b64,
            mime_type=mime_type,
            additional_text=additional_text,
        )
        return result


registry.register(VisualUnderstandingNode())
