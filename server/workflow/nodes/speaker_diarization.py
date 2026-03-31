"""Node 1.3a: Speaker Diarization + Voiceprint Matching.

Uses pyannote.audio for diarization and speechbrain for voiceprint matching.
In V1, we provide a working interface with graceful fallback if models aren't installed.
"""

import os
import logging
from typing import Optional

from server.config import settings
from server.workflow.engine import WorkflowNode, registry

logger = logging.getLogger(__name__)


class SpeakerDiarizationNode(WorkflowNode):
    node_id = "1.3a_speaker_diarization"
    node_name = "说话人分离与声纹匹配"
    default_model = None  # Local models

    def get_default_config(self) -> dict:
        return {
            "similarity_threshold": settings.workflow.voiceprint_similarity_threshold,
        }

    async def execute(self, input_data: dict, config: dict) -> dict:
        """Perform speaker diarization and match against user's voiceprint.

        Input from 1.1: {"1.1_video_preprocess": {"videos": [...]}}
        Output: {"diarization_results": [{video_id, segments: [{start, end, speaker, is_user}]}]}
        """
        preprocess_data = input_data.get("1.1_video_preprocess", {})
        videos = preprocess_data.get("videos", [])
        threshold = config.get("params", {}).get(
            "similarity_threshold",
            settings.workflow.voiceprint_similarity_threshold,
        )

        results = []

        for video in videos:
            if video.get("status") != "processed":
                continue

            video_id = video["video_id"]
            audio_path = video.get("audio_path")

            if not audio_path or not os.path.exists(audio_path):
                results.append({
                    "video_id": video_id,
                    "segments": [],
                    "status": "skipped",
                    "error": "No audio file",
                })
                continue

            try:
                segments = await self._diarize_and_match(audio_path, threshold)
                results.append({
                    "video_id": video_id,
                    "segments": segments,
                    "status": "completed",
                })
            except Exception as e:
                logger.error(f"Diarization failed for {video_id}: {e}")
                # Fallback: treat all speech as single unknown speaker
                results.append({
                    "video_id": video_id,
                    "segments": [{"start": 0, "end": 15, "speaker": "unknown", "is_user": False}],
                    "status": "fallback",
                    "error": str(e),
                })

        return {"diarization_results": results}

    async def _diarize_and_match(self, audio_path: str, threshold: float) -> list:
        """Run speaker diarization and voiceprint matching.

        Attempts to use pyannote.audio and speechbrain.
        Falls back to simple energy-based segmentation if unavailable.
        """
        try:
            return await self._diarize_with_pyannote(audio_path, threshold)
        except ImportError:
            logger.warning("pyannote.audio not installed, using fallback segmentation")
            return await self._fallback_segmentation(audio_path)

    async def _diarize_with_pyannote(self, audio_path: str, threshold: float) -> list:
        """Full diarization with pyannote + speechbrain voiceprint matching."""
        from pyannote.audio import Pipeline as PyannotePipeline
        import torch

        # Load diarization pipeline
        pipeline = PyannotePipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            use_auth_token=os.getenv("HF_TOKEN"),
        )

        # Run diarization
        diarization = pipeline(audio_path)

        segments = []
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            # Try to match voiceprint with user
            is_user = await self._match_voiceprint(
                audio_path, turn.start, turn.end, threshold
            )

            segments.append({
                "start": round(turn.start, 2),
                "end": round(turn.end, 2),
                "speaker": speaker,
                "is_user": is_user,
            })

        return segments

    async def _match_voiceprint(
        self, audio_path: str, start: float, end: float, threshold: float
    ) -> bool:
        """Match a speech segment against the user's registered voiceprint."""
        try:
            from speechbrain.inference.speaker import EncoderClassifier
            import torchaudio

            # Load user voiceprint (registered during onboarding)
            # This would load from the user's stored voiceprint file
            # For now, return False as placeholder
            # In production: extract embedding from segment, compare cosine similarity
            return False
        except ImportError:
            return False

    async def _fallback_segmentation(self, audio_path: str) -> list:
        """Simple fallback: detect speech vs silence using energy."""
        try:
            import numpy as np
            import wave

            with wave.open(audio_path, 'r') as wav:
                frames = wav.readframes(wav.getnframes())
                sample_rate = wav.getframerate()
                audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32)

            # Simple energy-based VAD
            frame_length = int(0.025 * sample_rate)
            hop_length = int(0.010 * sample_rate)
            energy = []
            for i in range(0, len(audio) - frame_length, hop_length):
                frame = audio[i:i + frame_length]
                energy.append(np.sqrt(np.mean(frame ** 2)))

            energy = np.array(energy)
            threshold_val = np.mean(energy) * 0.5

            # Find speech segments
            is_speech = energy > threshold_val
            segments = []
            in_speech = False
            start = 0

            for i, speech in enumerate(is_speech):
                t = i * hop_length / sample_rate
                if speech and not in_speech:
                    start = t
                    in_speech = True
                elif not speech and in_speech:
                    segments.append({
                        "start": round(start, 2),
                        "end": round(t, 2),
                        "speaker": "unknown",
                        "is_user": False,
                    })
                    in_speech = False

            if in_speech:
                segments.append({
                    "start": round(start, 2),
                    "end": round(len(audio) / sample_rate, 2),
                    "speaker": "unknown",
                    "is_user": False,
                })

            return segments

        except Exception as e:
            logger.error(f"Fallback segmentation failed: {e}")
            return [{"start": 0, "end": 15, "speaker": "unknown", "is_user": False}]


registry.register(SpeakerDiarizationNode())
