"""Node 1.3b: Automatic Speech Recognition (FunASR Paraformer)."""

import os
import logging

from server.workflow.engine import WorkflowNode, registry

logger = logging.getLogger(__name__)


class ASRNode(WorkflowNode):
    node_id = "1.3b_asr"
    node_name = "语音转文字"
    default_model = None  # Local model (FunASR)

    async def execute(self, input_data: dict, config: dict) -> dict:
        """Transcribe speech segments with speaker labels.

        Input from 1.3a: {"1.3a_speaker_diarization": {"diarization_results": [...]}}
        Also needs audio files from 1.1.
        Output: {"asr_results": [{video_id, transcripts: [{start, end, speaker, is_user, text}]}]}
        """
        diarization_data = input_data.get("1.3a_speaker_diarization", {})
        diarization_results = diarization_data.get("diarization_results", [])

        # Also get video preprocess data for audio paths
        preprocess_data = input_data.get("1.1_video_preprocess", {})
        videos = preprocess_data.get("videos", [])
        audio_map = {v["video_id"]: v.get("audio_path") for v in videos if v.get("status") == "processed"}

        results = []

        for diar in diarization_results:
            video_id = diar["video_id"]
            segments = diar.get("segments", [])
            audio_path = audio_map.get(video_id)

            if not audio_path or not os.path.exists(audio_path):
                results.append({
                    "video_id": video_id,
                    "transcripts": [],
                    "status": "skipped",
                })
                continue

            try:
                transcripts = await self._transcribe_segments(audio_path, segments)
                results.append({
                    "video_id": video_id,
                    "transcripts": transcripts,
                    "status": "completed",
                })
            except Exception as e:
                logger.error(f"ASR failed for {video_id}: {e}")
                results.append({
                    "video_id": video_id,
                    "transcripts": [],
                    "status": "failed",
                    "error": str(e),
                })

        return {"asr_results": results}

    async def _transcribe_segments(self, audio_path: str, segments: list) -> list:
        """Transcribe each speaker segment."""
        try:
            return await self._transcribe_with_funasr(audio_path, segments)
        except ImportError:
            logger.warning("FunASR not installed, using whisper fallback")
            return await self._transcribe_with_whisper(audio_path, segments)

    async def _transcribe_with_funasr(self, audio_path: str, segments: list) -> list:
        """Use FunASR Paraformer for Chinese ASR."""
        from funasr import AutoModel

        model = AutoModel(model="paraformer-zh", model_revision="v2.0.4")

        transcripts = []
        for seg in segments:
            # FunASR can handle the full audio with timestamps
            # For simplicity, transcribe the full audio and align with segments
            pass

        # Full audio transcription with timestamps
        result = model.generate(input=audio_path, batch_size_s=300)

        if result and len(result) > 0:
            full_text = result[0].get("text", "")
            timestamps = result[0].get("timestamp", [])

            # Map transcribed text to speaker segments
            for seg in segments:
                seg_text_parts = []
                for ts_pair in timestamps:
                    ts_start = ts_pair[0] / 1000.0  # ms to seconds
                    ts_end = ts_pair[1] / 1000.0
                    # Check overlap with speaker segment
                    if ts_start >= seg["start"] and ts_end <= seg["end"]:
                        seg_text_parts.append(ts_pair)

                transcripts.append({
                    "start": seg["start"],
                    "end": seg["end"],
                    "speaker": seg["speaker"],
                    "is_user": seg.get("is_user", False),
                    "text": full_text if not timestamps else " ".join(
                        [str(p) for p in seg_text_parts]
                    ),
                })
        else:
            # Fallback: return segments with empty text
            for seg in segments:
                transcripts.append({
                    "start": seg["start"],
                    "end": seg["end"],
                    "speaker": seg["speaker"],
                    "is_user": seg.get("is_user", False),
                    "text": "",
                })

        return transcripts

    async def _transcribe_with_whisper(self, audio_path: str, segments: list) -> list:
        """Fallback: use OpenAI Whisper for ASR."""
        try:
            import whisper

            model = whisper.load_model("base")
            result = model.transcribe(audio_path, language="zh")

            whisper_segments = result.get("segments", [])

            # Map whisper segments to speaker segments
            transcripts = []
            for seg in segments:
                seg_texts = []
                for ws in whisper_segments:
                    # Check overlap
                    if ws["start"] < seg["end"] and ws["end"] > seg["start"]:
                        seg_texts.append(ws["text"])

                transcripts.append({
                    "start": seg["start"],
                    "end": seg["end"],
                    "speaker": seg["speaker"],
                    "is_user": seg.get("is_user", False),
                    "text": " ".join(seg_texts).strip(),
                })

            return transcripts

        except ImportError:
            logger.warning("Neither FunASR nor Whisper installed, returning empty transcripts")
            return [
                {
                    "start": seg["start"],
                    "end": seg["end"],
                    "speaker": seg["speaker"],
                    "is_user": seg.get("is_user", False),
                    "text": "",
                }
                for seg in segments
            ]


registry.register(ASRNode())
