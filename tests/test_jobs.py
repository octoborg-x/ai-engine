"""Focused tests for bounded background job submission and execution."""
import asyncio
import pytest
from fastapi import HTTPException
import app.jobs as jobs

@pytest.fixture(autouse=True)
async def clean_job_state():
    await jobs.stop_workers()
    jobs._jobs.clear()
    while not jobs._queue.empty():
        jobs._queue.get_nowait()
        jobs._queue.task_done()
    yield
    await jobs.stop_workers()
    jobs._jobs.clear()
    while not jobs._queue.empty():
        jobs._queue.get_nowait()
        jobs._queue.task_done()

@pytest.mark.asyncio
async def test_submit_returns_queued_job_and_worker_completes(monkeypatch):
    async def fake_process(prompt: str) -> str:
        return f"test result: {prompt}"
    monkeypatch.setattr(jobs, "process_prompt", fake_process)
    await jobs.start_workers()
    accepted = await jobs.submit_job(jobs.JobSubmission(prompt="summarize"))
    assert accepted.status == "queued"
    await asyncio.wait_for(jobs._queue.join(), timeout=1)
    result = await jobs.get_job(accepted.job_id)
    assert result.status == "succeeded"
    assert result.result == "test result: summarize"
    assert result.duration_ms is not None

@pytest.mark.asyncio
async def test_failed_job_does_not_kill_worker(monkeypatch):
    calls = 0
    async def flaky_process(prompt: str) -> str:
        nonlocal calls
        calls += 1
        if prompt == "fail":
            raise RuntimeError("private provider detail")
        return "ok"
    monkeypatch.setattr(jobs, "process_prompt", flaky_process)
    await jobs.start_workers()
    failed = await jobs.submit_job(jobs.JobSubmission(prompt="fail"))
    succeeded = await jobs.submit_job(jobs.JobSubmission(prompt="works"))
    await asyncio.wait_for(jobs._queue.join(), timeout=1)
    failed_view = await jobs.get_job(failed.job_id)
    succeeded_view = await jobs.get_job(succeeded.job_id)
    assert failed_view.status == "failed"
    assert failed_view.error == "Job processing failed"
    assert "private provider detail" not in str(failed_view.model_dump())
    assert succeeded_view.status == "succeeded"
    assert calls == 2

@pytest.mark.asyncio
async def test_missing_job_returns_404():
    with pytest.raises(HTTPException) as exc:
        await jobs.get_job("missing")
    assert exc.value.status_code == 404

@pytest.mark.asyncio
async def test_full_queue_returns_503(monkeypatch):
    jobs._queue = asyncio.Queue(maxsize=1)
    jobs._queue.put_nowait("existing")
    with pytest.raises(HTTPException) as exc:
        await jobs.submit_job(jobs.JobSubmission(prompt="overflow"))
    assert exc.value.status_code == 503
    assert exc.value.headers["Retry-After"] == "5"
    assert not any(job.prompt == "overflow" for job in jobs._jobs.values())
