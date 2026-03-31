"""Celery application configuration."""

import asyncio
from celery import Celery

from server.config import settings

app = Celery(
    "lifelens",
    broker=settings.celery.broker_url,
    backend=settings.celery.result_backend,
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,
)


@app.task(name="lifelens.process_batch", bind=True, max_retries=1)
def process_batch_task(self, batch_id: str, profile_id: str):
    """Celery task to process a batch of videos through the workflow."""
    from server.services.workflow_service import _run_workflow

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_run_workflow(batch_id, profile_id))
    finally:
        loop.close()
