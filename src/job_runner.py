import asyncio
import logging
from typing import Callable, Any, Dict, Optional
import uuid

logger = logging.getLogger(__name__)

class JobRunner:
    def __init__(self, max_queue_size: int = 100):
        self.queue = asyncio.Queue(maxsize=max_queue_size)
        self._worker_task: Optional[asyncio.Task] = None
        self.jobs: Dict[str, Dict[str, Any]] = {}

    async def start(self):
        """Starts the background worker task."""
        if self._worker_task is None:
            self._worker_task = asyncio.create_task(self._worker())
            logger.info("Job runner started.")

    async def stop(self):
        """Stops the background worker task."""
        if self._worker_task is not None:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            self._worker_task = None
            logger.info("Job runner stopped.")

    async def submit_job(self, func: Callable, *args, job_id: Optional[str] = None, **kwargs) -> str:
        """
        Submits a job to the runner. Returns a job_id.
        Raises asyncio.QueueFull if the queue is full.
        """
        job_id = job_id or str(uuid.uuid4())
        job_item = {
            "job_id": job_id,
            "func": func,
            "args": args,
            "kwargs": kwargs
        }
        
        self.queue.put_nowait(job_item)
        
        self.jobs[job_id] = {
            "status": "pending",
            "result": None,
            "error": None
        }
        logger.info(f"Job {job_id} submitted.")
        return job_id

    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Returns the current status of a job."""
        if job_id not in self.jobs:
            return {"status": "not_found"}
        return self.jobs[job_id]

    async def _worker(self):
        """Background task that processes jobs one at a time."""
        while True:
            try:
                job_item = await self.queue.get()
                job_id = job_item["job_id"]
                func = job_item["func"]
                args = job_item["args"]
                kwargs = job_item["kwargs"]

                self.jobs[job_id]["status"] = "running"
                logger.info(f"Job {job_id} started.")

                try:
                    if asyncio.iscoroutinefunction(func):
                        result = await func(*args, **kwargs)
                    else:
                        result = await asyncio.to_thread(func, *args, **kwargs)
                    
                    self.jobs[job_id]["status"] = "completed"
                    self.jobs[job_id]["result"] = result
                    logger.info(f"Job {job_id} completed.")
                except Exception as e:
                    self.jobs[job_id]["status"] = "failed"
                    self.jobs[job_id]["error"] = str(e)
                    logger.error(f"Job {job_id} failed: {e}")
                finally:
                    self.queue.task_done()
            except asyncio.CancelledError:
                logger.info("Job runner worker cancelled.")
                break
            except Exception as e:
                logger.error(f"Unexpected error in job runner worker: {e}")

# Global job runner instance
job_runner = JobRunner()
