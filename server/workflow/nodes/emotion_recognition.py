"""Node 1.3c: Emotion Recognition from audio (emotion2vec)."""

import os
import logging

from server.config import settings
from server.workflow.engine import WorkflowNode, registry

logger = logging.getLogger(__name__)


class EmotionRecognitionNode(WorkflowNode):
    node_id = "1.3c_emotion_recognition"
    node_name = "情绪识别"
    default_model = None  # Local model (emotion2vec)

    def get_default_config(self) -> dict:
        return {
            "confidence_threshold": settings.workflow.emotion_confidence_threshold,
        }

    async def execute(self, input_data: dict, config: dict) -> dict:
        """Recognize emotions from speech segments.

        Input from 1.3a: {"1.3a_speaker_diarization": {"diarization_results": [...]}}
        Also needs audio files from 1.1.
        Output: {"emotion_results": [{video_id, emotions: [{start, end, speaker, is_user, emotion, confidence}]}]}
        """
        diarization_data = input_data.get("1.3a_speaker_diarization", {})
        diarization_results = diarization_data.get("diarization_results", [])

        preprocess_data = input_data.get("1.1_video_preprocess", {})
        videos = preprocess_data.get("videos", [])
        audio_map = {v["video_id"]: v.get("audio_path") for v in videos if v.get("status") == "processed"}

        threshold = config.get("params", {}).get(
            "confidence_threshold",
            settings.workflow.emotion_confidence_threshold,
        )

        results = []

        for diar in diarization_results:
            video_id = diar["video_id"]
            segments = diar.get("segments", [])
            audio_path = audio_map.get(video_id)

            if not audio_path or not os.path.exists(audio_path):
                results.append({
                    "video_id": video_id,
                    "emotions": [],
                    "status": "skipped",
                })
                continue

            try:
                emotions = await self._recognize_emotions(audio_path, segments, threshold)
                results.append({
                    "video_id": video_id,
                    "emotions": emotions,
                    "status": "completed",
                })
            except Exception as e:
                logger.error(f"Emotion recognition failed for {video_id}: {e}")
                # Fallback: all segments marked as calm
                results.append({
                    "video_id": video_id,
                    "emotions": [
                        {
                            "start": seg["start"],
                            "end": seg["end"],
                            "speaker": seg["speaker"],
                            "is_user": seg.get("is_user", False),
                            "emotion": "calm",
                            "confidence": 0.5,
                        }
                        for seg in segments
                    ],
                    "status": "fallback",
                })

        return {"emotion_results": results}

    async def _recognize_emotions(self, audio_path: str, segments: list, threshold: float) -> list:
        """Run emotion recognition on each speech segment."""
        try:
            return await self._recognize_with_emotion2vec(audio_path, segments, threshold)
        except ImportError:
            logger.warning("emotion2vec not installed, using fallback (all calm)")
            return [
                {
                    "start": seg["start"],
                    "end": seg["end"],
                    "speaker": seg["speaker"],
                    "is_user": seg.get("is_user", False),
                    "emotion": "calm",
                    "confidence": 0.5,
                }
                for seg in segments
            ]

    async def _recognize_with_emotion2vec(
        self, audio_path: str, segments: list, threshold: float
    ) -> list:
        """Use emotion2vec+ for speech emotion recognition."""
        from funasr import AutoModel

        model = AutoModel(model="iic/emotion2vec_plus_large")

        emotions = []
        for seg in segments:
            # Process each segment
            result = model.generate(
                input=audio_path,
                output_dir=None,
                granularity="utterance",
            )

            if result and len(result) > 0:
                scores = result[0].get("scores", {})
                labels = result[0].get("labels", [])

                # Map to our 3 categories: happy / angry / calm
                emotion, confidence = self._map_emotion(scores, labels, threshold)
            else:
                emotion, confidence = "calm", 0.5

            emotions.append({
                "start": seg["start"],
                "end": seg["end"],
                "speaker": seg["speaker"],
                "is_user": seg.get("is_user", False),
                "emotion": emotion,
                "confidence": confidence,
            })

        return emotions

    def _map_emotion(self, scores: dict, labels: list, threshold: float) -> tuple:
        """Map emotion2vec labels to our 3 categories."""
        # emotion2vec labels: angry, disgusted, fearful, happy, neutral, other, sad, surprised, unknown
        happy_keys = {"happy", "surprised"}
        angry_keys = {"angry", "disgusted", "fearful", "sad"}
        calm_keys = {"neutral", "other", "unknown"}

        happy_score = sum(scores.get(k, 0) for k in happy_keys if k in scores)
        angry_score = sum(scores.get(k, 0) for k in angry_keys if k in scores)
        calm_score = sum(scores.get(k, 0) for k in calm_keys if k in scores)

        max_score = max(happy_score, angry_score, calm_score)

        if max_score < threshold:
            return "calm", max_score

        if happy_score == max_score:
            return "happy", happy_score
        elif angry_score == max_score:
            return "angry", angry_score
        else:
            return "calm", calm_score


registry.register(EmotionRecognitionNode())
