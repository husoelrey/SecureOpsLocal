import asyncio
import pytest
from src.job_runner import JobRunner

import pytest_asyncio

@pytest_asyncio.fixture
async def runner():
    # Use a small queue for testing
    runner = JobRunner(max_queue_size=2)
    await runner.start()
    yield runner
    await runner.stop()

@pytest.mark.asyncio
async def test_job_runner_success(runner):
    async def sample_job(x, y):
        await asyncio.sleep(0.1)
        return x + y

    job_id = await runner.submit_job(sample_job, 3, 4)
    status = runner.get_job_status(job_id)
    assert status["status"] in ("pending", "running", "completed")

    # Wait for completion
    await asyncio.sleep(0.2)
    status = runner.get_job_status(job_id)
    assert status["status"] == "completed"
    assert status["result"] == 7

@pytest.mark.asyncio
async def test_job_runner_failure(runner):
    async def failing_job():
        await asyncio.sleep(0.1)
        raise ValueError("Test error")

    job_id = await runner.submit_job(failing_job)
    
    await asyncio.sleep(0.2)
    status = runner.get_job_status(job_id)
    assert status["status"] == "failed"
    assert "Test error" in status["error"]

@pytest.mark.asyncio
async def test_job_runner_queue_full(runner):
    async def blocking_job():
        await asyncio.sleep(0.5)
        return True

    # The worker will immediately pick up the first job, so it leaves the queue.
    # To fill the queue of size 2, we need 1 running and 2 pending = 3 jobs total.
    
    # 1. Starts running immediately
    await runner.submit_job(blocking_job)
    await asyncio.sleep(0.05) # Yield to event loop so worker picks it up, making queue size 0
    
    # 2. Stays in queue (queue: 1)
    await runner.submit_job(blocking_job)
    
    # 3. Stays in queue (queue: 2 - full)
    await runner.submit_job(blocking_job)
    
    # 4. Should raise QueueFull
    with pytest.raises(asyncio.QueueFull):
        await runner.submit_job(blocking_job)

@pytest.mark.asyncio
async def test_job_runner_concurrency(runner):
    concurrency_counter = 0
    max_observed = 0
    
    async def track_concurrency():
        nonlocal concurrency_counter, max_observed
        concurrency_counter += 1
        if concurrency_counter > max_observed:
            max_observed = concurrency_counter
        await asyncio.sleep(0.1)
        concurrency_counter -= 1

    # Submit 2 jobs
    await runner.submit_job(track_concurrency)
    await runner.submit_job(track_concurrency)
    
    await asyncio.sleep(0.3)
    # The max observed concurrency should be exactly 1
    assert max_observed == 1
