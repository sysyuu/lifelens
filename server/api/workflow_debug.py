"""Workflow debug panel API endpoints."""

from datetime import date
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from server.models.database import get_db
from server.models.workflow import WorkflowRun, NodeRun, NodeConfig
from server.workflow.engine import registry, WorkflowEngine
from server.api.schemas import WorkflowRunOut, NodeRunOut, NodeConfigUpdate, RerunNodeRequest

router = APIRouter(prefix="/api/debug", tags=["debug"])


@router.get("/{profile_id}/runs", response_model=list[WorkflowRunOut])
async def list_workflow_runs(
    profile_id: UUID,
    target_date: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List workflow runs, optionally filtered by date (for date selector in debug panel)."""
    query = (
        select(WorkflowRun)
        .where(WorkflowRun.profile_id == profile_id)
        .options(selectinload(WorkflowRun.node_runs))
        .order_by(WorkflowRun.started_at.desc().nullslast())
        .limit(50)
    )

    if target_date:
        query = query.where(WorkflowRun.target_date == target_date)

    result = await db.execute(query)
    runs = result.scalars().all()

    return [
        WorkflowRunOut(
            id=r.id,
            target_date=r.target_date,
            status=r.status,
            started_at=r.started_at,
            completed_at=r.completed_at,
            error_message=r.error_message,
            node_runs=[NodeRunOut.model_validate(nr) for nr in r.node_runs],
        )
        for r in runs
    ]


@router.get("/{profile_id}/dates", response_model=list[Optional[date]])
async def list_workflow_dates(
    profile_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """List all dates with workflow runs (for date picker)."""
    result = await db.execute(
        select(WorkflowRun.target_date)
        .where(WorkflowRun.profile_id == profile_id)
        .distinct()
        .order_by(WorkflowRun.target_date.desc().nullslast())
    )
    return result.scalars().all()


@router.get("/node/{node_run_id}", response_model=NodeRunOut)
async def get_node_run(node_run_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get detailed info for a specific node run (input, output, config)."""
    result = await db.execute(
        select(NodeRun).where(NodeRun.id == node_run_id)
    )
    node_run = result.scalar_one_or_none()
    if not node_run:
        raise HTTPException(status_code=404, detail="Node run not found")

    return NodeRunOut.model_validate(node_run)


@router.put("/{profile_id}/config/{node_id}")
async def update_node_config(
    profile_id: UUID,
    node_id: str,
    data: NodeConfigUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update node configuration (model, system prompt, params). Used by debug panel."""
    result = await db.execute(
        select(NodeConfig).where(
            NodeConfig.profile_id == profile_id,
            NodeConfig.node_id == node_id,
        )
    )
    config = result.scalar_one_or_none()

    if config:
        if data.model is not None:
            config.model = data.model
        if data.system_prompt is not None:
            config.system_prompt = data.system_prompt
        if data.params is not None:
            config.params = data.params
    else:
        config = NodeConfig(
            profile_id=profile_id,
            node_id=node_id,
            model=data.model,
            system_prompt=data.system_prompt,
            params=data.params,
        )
        db.add(config)

    await db.commit()
    return {"status": "updated", "node_id": node_id}


@router.get("/{profile_id}/config/{node_id}")
async def get_node_config(
    profile_id: UUID,
    node_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get current node configuration (user overrides + defaults)."""
    result = await db.execute(
        select(NodeConfig).where(
            NodeConfig.profile_id == profile_id,
            NodeConfig.node_id == node_id,
        )
    )
    user_config = result.scalar_one_or_none()

    # Get defaults from registered node
    node = registry.get(node_id)
    defaults = {
        "model": node.default_model if node else None,
        "system_prompt": node.get_default_system_prompt() if node else None,
        "params": node.get_default_config() if node else {},
    }

    return {
        "node_id": node_id,
        "defaults": defaults,
        "overrides": {
            "model": user_config.model if user_config else None,
            "system_prompt": user_config.system_prompt if user_config else None,
            "params": user_config.params if user_config else None,
        },
        "effective": {
            "model": (user_config.model if user_config and user_config.model else defaults["model"]),
            "system_prompt": (user_config.system_prompt if user_config and user_config.system_prompt else defaults["system_prompt"]),
            "params": {**defaults["params"], **(user_config.params if user_config and user_config.params else {})},
        },
    }


@router.post("/rerun")
async def rerun_node(data: RerunNodeRequest, db: AsyncSession = Depends(get_db)):
    """Re-run a single workflow node with current config. Used by debug panel."""
    # Get workflow run to find profile_id
    result = await db.execute(
        select(WorkflowRun).where(WorkflowRun.id == data.workflow_run_id)
    )
    workflow_run = result.scalar_one_or_none()
    if not workflow_run:
        raise HTTPException(status_code=404, detail="Workflow run not found")

    engine = WorkflowEngine(db, workflow_run.profile_id)
    node_run = await engine.rerun_node(data.workflow_run_id, data.node_id)

    return NodeRunOut.model_validate(node_run)


@router.get("/nodes")
async def list_available_nodes():
    """List all registered workflow nodes and their info."""
    nodes = registry.all_nodes()
    return [
        {
            "node_id": node_id,
            "node_name": node.node_name,
            "default_model": node.default_model,
            "has_system_prompt": node.get_default_system_prompt() is not None,
        }
        for node_id, node in nodes.items()
    ]
