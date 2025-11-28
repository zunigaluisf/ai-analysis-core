import threading
import time
import uuid
from typing import Any, Dict, List, Optional

class ProgressManager:
    def __init__(self):
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def create_job(self, files: List[Dict]) -> str:
        job_id = str(uuid.uuid4())
        with self._lock:
            self._jobs[job_id] = {
                "status": "running",
                "stage": "initializing",
                "progress": 0,
                "step": "queued",
                "message": "Starting analysis",
                "files": [
                    {
                        "file_id": f.get("file_id"),
                        "name": f.get("name"),
                        "file_type": f.get("file_type", "unknown"),
                        "size_bytes": f.get("size_bytes"),
                        "progress": 0,
                        "status": "pending",
                        "chunk_index": 0,
                        "chunk_total": 0,
                        "message": f.get("source_zip", "") or "",
                    }
                    for f in files
                ],
                "logs": [],
                "result": None,
                "updated_at": time.time(),
            }
        return job_id

    def update(
        self,
        job_id: str,
        *,
        progress: Optional[float] = None,
        step: Optional[str] = None,
        stage: Optional[str] = None,
        message: Optional[str] = None,
        file_name: Optional[str] = None,
        file_id: Optional[str] = None,
        file_progress: Optional[float] = None,
        file_status: Optional[str] = None,
        chunk_index: Optional[int] = None,
        chunk_total: Optional[int] = None,
        log: Optional[str] = None,
    ) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            if progress is not None:
                job["progress"] = max(job.get("progress", 0), min(progress, 100))
            if step:
                job["step"] = step
                job["stage"] = stage or step
            elif stage:
                job["stage"] = stage
            if message:
                job["message"] = message
            if log:
                ts = time.strftime("%H:%M:%S")
                job["logs"].append(f"[{ts}] {log}")
                job["logs"] = job["logs"][-200:]  # cap
            if file_name or file_id:
                for f in job["files"]:
                    if (file_id and f.get("file_id") == file_id) or (file_name and f.get("name") == file_name):
                        if file_progress is not None:
                            f["progress"] = max(f.get("progress", 0), min(file_progress, 100))
                        if file_status:
                            f["status"] = file_status
                        if chunk_index is not None:
                            f["chunk_index"] = chunk_index
                        if chunk_total is not None:
                            f["chunk_total"] = chunk_total
                        if message:
                            f["message"] = message
                        break
            job["updated_at"] = time.time()

    def set_result(self, job_id: str, result: Dict[str, Any]) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            job["status"] = "completed"
            job["progress"] = 100
            job["step"] = "completed"
            job["message"] = "Analysis complete"
            job["result"] = result
            job["updated_at"] = time.time()

    def fail(self, job_id: str, message: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            job["status"] = "failed"
            job["message"] = message
            job["progress"] = max(job.get("progress", 0), 100)
            job["step"] = "failed"
            job["updated_at"] = time.time()

    def get(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            job = self._jobs.get(job_id)
            return dict(job) if job else None


progress_manager = ProgressManager()
