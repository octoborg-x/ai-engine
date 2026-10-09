"""Bounded in-process background jobs for long-running AI work.

This first implementation is intentionally in-memory: jobs are not durable across
process restarts and should not be used as a multi-worker production queue.
"""
import asyncio
import logging
import time
from contextlib import suppress
from dataclasses import dataclass, field
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter(tags=["jobs"])

JobStatus = Literal["queued", "running", "succeeded", "failed"]
QUEUE_CAPACITY = 100
WORKER_COUNT = 2


class JobSubmission(BaseModel):
    prompt: str = Field(min_length=1, max_length=4000)


class JobAccepted(BaseModel):
    job_id: str
    status: JobStatus


class JobView(BaseModel):
    job_id: str
    status: JobStatus
    result: str | None = None
    error: str | None = None
    duration_ms: float | None = None


@dataclass
class Job:
    job_id: str
    prompt: str
    status: JobStatus = "queued"
    result: str | None = None
    error: str | None = None
    duration_ms: float | None = None
    created_at: float = field(default_factory=time.monotonic)


_jobs: dict[str, Job] = {}
_queue: asyncio.Queue[str] = asyncio.Queue(maxsize=QUEUE_CAPACITY)
_worker_tasks: list[asyncio.Task] = []


async def process_prompt(prompt: str) -> str:
    """Placeholder processor; replace with the existing LLM service adapter."""
    await asyncio.sleep(0)
    return f"Processed: {prompt}"


async def _worker() -> None:
    while True:
        job_id = await _queue.get()
        started = time.monotonic()
        job = _jobs.get(job_id)
        try:
            if job is None:
                logger.error("Queued job %s was not found", job_id)
                continue
            job.status = "running"
            logger.info("Background job started", extra={"job_id": job_id})
            job.result = await process_prompt(job.prompt)
            job.status = "succeeded"
        except asyncio.CancelledError:
            if job is not None:
                job.status = "queued"
            raise
        except Exception as exc:  # isolate failures so the worker keeps running
            if job is not None:
                job.status = "failed"
                job.error = "Job processing failed"
            logger.exception("Background job failed", extra={"job_id": job_id})
        finally:
            if job is not None:
                job.duration_ms = round((time.monotonic() - started) * 1000, 2)
            _queue.task_done()


async def start_workers() -> None:
    """Start workers once per application process."""
    if _worker_tasks and any(not task.done() for task in _worker_tasks):
        return
    _worker_tasks.clear()
    _worker_tasks.extend(
        asyncio.create_task(_worker(), name=f"ai-job-worker-{index}")
        for index in range(WORKER_COUNT)
    )


async def stop_workers() -> None:
    """Cancel local workers cleanly during application shutdown."""
    tasks = list(_worker_tasks)
    _worker_tasks.clear()
    for task in tasks:
        task.cancel()
    for task in tasks:
        with suppress(asyncio.CancelledError):
            await task


@router.post(
    "/jobs",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=JobAccepted,
)
async def submit_job(request: JobSubmission) -> JobAccepted:
    job = Job(job_id=str(uuid4()), prompt=request.prompt)
    # Register before enqueueing so a worker can never observe a missing job.
    _jobs[job.job_id] = job
    try:
        _queue.put_nowait(job.job_id)
    except asyncio.QueueFull as exc:
        _jobs.pop(job.job_id, None)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Job queue is full; retry later",
            headers={"Retry-After": "5"},
        ) from exc
    return JobAccepted(job_id=job.job_id, status=job.status)


@router.get("/jobs/{job_id}", response_model=JobView)
async def get_job(job_id: str) -> JobView:
    job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobView(
        job_id=job.job_id,
        status=job.status,
        result=job.result,
        error=job.error,
        duration_ms=job.duration_ms,
    )
