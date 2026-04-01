"""Workflow engine: orchestrates node execution for a single day's video processing."""

import uuid
import logging
from datetime import datetime
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from server.models.workflow import WorkflowRun, NodeRun, NodeConfig

logger = logging.getLogger(__name__)


class WorkflowNode:
    """Base class for all workflow nodes."""

    node_id: str = ""
    node_name: str = ""
    default_model: Optional[str] = None

    async def execute(self, input_data: dict, config: dict) -> dict:
        """Execute this node. Must be overridden by subclasses."""
        raise NotImplementedError

    def get_default_system_prompt(self) -> Optional[str]:
        """Return the default system prompt for this node."""
        return None

    def get_default_config(self) -> dict:
        """Return default configuration params."""
        return {}


class NodeRegistry:
    """Registry of all available workflow nodes."""

    def __init__(self):
        self._nodes: dict[str, WorkflowNode] = {}

    def register(self, node: WorkflowNode):
        self._nodes[node.node_id] = node

    def get(self, node_id: str) -> Optional[WorkflowNode]:
        return self._nodes.get(node_id)

    def all_nodes(self) -> dict[str, WorkflowNode]:
        return dict(self._nodes)


# Global registry
registry = NodeRegistry()


class WorkflowEngine:
    """Orchestrates the complete workflow for processing a day's videos."""

    # Define the execution order and dependencies
    PIPELINE = [
        # Stage 1: Video processing (1.2 and 1.3 run in parallel per video)
        {"id": "1.1_video_preprocess", "depends_on": []},
        {"id": "1.2_visual_understanding", "depends_on": ["1.1_video_preprocess"]},
        {"id": "1.3a_speaker_diarization", "depends_on": ["1.1_video_preprocess"]},
        {"id": "1.3b_asr", "depends_on": ["1.3a_speaker_diarization"]},
        {"id": "1.3c_emotion_recognition", "depends_on": ["1.3a_speaker_diarization"]},
        # Stage 2: Integration
        {"id": "2.1_event_structuring", "depends_on": ["1.2_visual_understanding", "1.3b_asr", "1.3c_emotion_recognition"]},
        {"id": "2.2_person_matching", "depends_on": ["2.1_event_structuring"]},
        # Stage 3: Generation
        {"id": "3.1_profile_update", "depends_on": ["2.2_person_matching"]},
        {"id": "3.2_diary_generation", "depends_on": ["3.1_profile_update"]},
        # Stage 4: Post-processing
        {"id": "4.1_media_slicing", "depends_on": ["3.2_diary_generation"]},
        {"id": "4.2_quality_check", "depends_on": ["4.1_media_slicing"]},
        {"id": "4.3_storage", "depends_on": ["4.2_quality_check"]},
    ]

    def __init__(self, db: AsyncSession, profile_id: uuid.UUID):
        self.db = db
        self.profile_id = profile_id
        self._results: dict[str, Any] = {}

    async def run(self, batch_id: uuid.UUID, target_date=None) -> WorkflowRun:
        """Execute the full workflow pipeline."""
        # Create workflow run record
        workflow_run = WorkflowRun(
            profile_id=self.profile_id,
            batch_id=batch_id,
            target_date=target_date,
            status="running",
            started_at=datetime.utcnow(),
        )
        self.db.add(workflow_run)
        await self.db.flush()

        try:
            for step in self.PIPELINE:
                node_id = step["id"]
                node = registry.get(node_id)

                if node is None:
                    logger.warning(f"Node {node_id} not registered, skipping")
                    continue

                # Gather ALL previous node results so any node can access
                # upstream data (not just direct dependencies)
                input_data = dict(self._results)

                # Inject engine context
                input_data["_db_session"] = self.db
                input_data["_profile_id"] = self.profile_id

                # Load node config (user overrides from debug panel)
                config = await self._load_node_config(node_id, node)

                # Create node run record
                node_run = NodeRun(
                    workflow_run_id=workflow_run.id,
                    node_id=node_id,
                    node_name=node.node_name,
                    status="running",
                    model_used=config.get("model"),
                    system_prompt=config.get("system_prompt"),
                    config_params=config.get("params"),
                    input_data=self._serialize_input(input_data),
                    started_at=datetime.utcnow(),
                )
                self.db.add(node_run)
                await self.db.flush()

                try:
                    # Execute node
                    result = await node.execute(input_data, config)
                    self._results[node_id] = result

                    # Update node run
                    node_run.status = "completed"
                    node_run.output_data = self._serialize_output(result)
                    node_run.completed_at = datetime.utcnow()
                    node_run.duration_seconds = (
                        node_run.completed_at - node_run.started_at
                    ).total_seconds()

                    if isinstance(result, dict) and "token_usage" in result:
                        node_run.token_usage = result["token_usage"]

                except Exception as e:
                    logger.error(f"Node {node_id} failed: {e}", exc_info=True)
                    node_run.status = "failed"
                    node_run.error_message = str(e)
                    node_run.completed_at = datetime.utcnow()
                    raise

                await self.db.flush()

            workflow_run.status = "completed"
            workflow_run.completed_at = datetime.utcnow()

        except Exception as e:
            workflow_run.status = "failed"
            workflow_run.error_message = str(e)
            workflow_run.completed_at = datetime.utcnow()

        await self.db.commit()
        return workflow_run

    async def rerun_node(self, workflow_run_id: uuid.UUID, node_id: str) -> NodeRun:
        """Re-run a single node with potentially updated config. Used by debug panel."""
        node = registry.get(node_id)
        if node is None:
            raise ValueError(f"Unknown node: {node_id}")

        # Load previous run's results for dependencies
        step = next((s for s in self.PIPELINE if s["id"] == node_id), None)
        if step is None:
            raise ValueError(f"Node {node_id} not in pipeline")

        # Load ALL node outputs from this workflow run (not just dependencies)
        input_data = {}
        from sqlalchemy import select as sa_select
        all_node_runs_result = await self.db.execute(
            sa_select(NodeRun)
            .where(
                NodeRun.workflow_run_id == workflow_run_id,
                NodeRun.status == "completed",
            )
        )
        for nr in all_node_runs_result.scalars().all():
            if nr.output_data:
                input_data[nr.node_id] = nr.output_data

        # Inject engine context
        input_data["_db_session"] = self.db
        input_data["_profile_id"] = self.profile_id

        config = await self._load_node_config(node_id, node)

        node_run = NodeRun(
            workflow_run_id=workflow_run_id,
            node_id=node_id,
            node_name=node.node_name,
            status="running",
            model_used=config.get("model"),
            system_prompt=config.get("system_prompt"),
            config_params=config.get("params"),
            input_data=self._serialize_input(input_data),
            started_at=datetime.utcnow(),
        )
        self.db.add(node_run)
        await self.db.flush()

        try:
            result = await node.execute(input_data, config)
            node_run.status = "completed"
            node_run.output_data = self._serialize_output(result)
            node_run.completed_at = datetime.utcnow()
            node_run.duration_seconds = (
                node_run.completed_at - node_run.started_at
            ).total_seconds()
            if isinstance(result, dict) and "token_usage" in result:
                node_run.token_usage = result["token_usage"]
        except Exception as e:
            node_run.status = "failed"
            node_run.error_message = str(e)
            node_run.completed_at = datetime.utcnow()

        await self.db.commit()
        return node_run

    async def _load_node_config(self, node_id: str, node: WorkflowNode) -> dict:
        """Load node config: user overrides > defaults."""
        from sqlalchemy import select

        result = await self.db.execute(
            select(NodeConfig).where(
                NodeConfig.profile_id == self.profile_id,
                NodeConfig.node_id == node_id,
            )
        )
        user_config = result.scalar_one_or_none()

        config = {
            "model": node.default_model,
            "system_prompt": node.get_default_system_prompt(),
            "params": node.get_default_config(),
        }

        if user_config:
            if user_config.model:
                config["model"] = user_config.model
            if user_config.system_prompt:
                config["system_prompt"] = user_config.system_prompt
            if user_config.params:
                config["params"] = {**config["params"], **user_config.params}

        return config

    async def _get_latest_node_run(self, workflow_run_id: uuid.UUID, node_id: str) -> Optional[NodeRun]:
        from sqlalchemy import select

        result = await self.db.execute(
            select(NodeRun)
            .where(
                NodeRun.workflow_run_id == workflow_run_id,
                NodeRun.node_id == node_id,
                NodeRun.status == "completed",
            )
            .order_by(NodeRun.completed_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    def _serialize_input(self, data: dict) -> dict:
        """Serialize input data for storage, truncating large blobs."""
        serialized = {}
        for key, value in data.items():
            if isinstance(value, dict):
                serialized[key] = value
            elif isinstance(value, (list, tuple)):
                serialized[key] = {"type": "list", "length": len(value), "preview": str(value[:2]) if value else "[]"}
            else:
                serialized[key] = str(value)[:1000]
        return serialized

    def _serialize_output(self, data) -> dict:
        """Serialize output data for storage."""
        if isinstance(data, dict):
            return data
        return {"result": str(data)[:5000]}
