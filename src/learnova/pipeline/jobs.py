"""
In-memory job store for asynchronous pipeline runs.

The pipeline takes far longer than an HTTP request should, so the API returns
a job id immediately and the client polls for stage progress.

Scope note: this is a single-process, in-memory store — jobs are lost on
restart and it does not work across multiple workers. That is the right size
for a demo; swap in Redis if this ever runs multi-worker.
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from learnova.logging_config import logger
from learnova.pipeline.orchestrator import (
    STAGES,
    PipelineConfig,
    PipelineResult,
    build_markdown,
    generate,
)


@dataclass
class Job:
    id: str
    source_name: str
    # Owner's Clerk user id. "" means anonymous (auth not configured).
    user_id: str = ""
    status: str = "pending"        # pending | running | done | failed
    stage: str = ""
    stage_status: str = ""
    progress: float = 0.0
    detail: str = ""
    error: Optional[str] = None
    markdown: str = ""
    created_at: float = field(default_factory=time.time)
    result: Optional[PipelineResult] = None
    _markdown_doc: Any = None

    def to_dict(self) -> dict:
        payload: Dict[str, Any] = {
            "id": self.id,
            "source_name": self.source_name,
            "user_id": self.user_id,
            "status": self.status,
            "stage": self.stage,
            "stage_status": self.stage_status,
            "progress": round(self.progress, 3),
            "detail": self.detail,
            "error": self.error,
            "stages": STAGES,
            "created_at": self.created_at,
        }
        if self.result is not None:
            payload["result"] = self.result.summary()
        return payload


class JobStore:
    """Thread-safe registry of jobs."""

    def __init__(self) -> None:
        self._jobs: Dict[str, Job] = {}
        self._lock = threading.Lock()

    def create(self, source_name: str, user_id: str = "") -> Job:
        job = Job(id=uuid.uuid4().hex[:16], source_name=source_name, user_id=user_id)
        with self._lock:
            self._jobs[job.id] = job
        return job

    def get(self, job_id: str) -> Optional[Job]:
        with self._lock:
            return self._jobs.get(job_id)

    def all(self) -> List[Job]:
        with self._lock:
            return list(self._jobs.values())

    def delete(self, job_id: str) -> bool:
        with self._lock:
            return self._jobs.pop(job_id, None) is not None

    # ── Execution ────────────────────────────────────────────────────────────
    def start_conversion(self, job: Job, path: str, config: PipelineConfig) -> None:
        """Run only the markdown conversion, so the user can review/edit it."""

        def _work() -> None:
            job.status = "running"
            job.stage = "convert"
            job.stage_status = "running"
            try:
                doc = build_markdown(path, source_name=job.source_name, config=config)
                job._markdown_doc = doc
                job.markdown = doc.markdown
                job.status = "awaiting_review"
                job.stage_status = "ok"
                job.progress = 1.0 / len(STAGES)
            except Exception as exc:
                logger.error("job %s conversion failed: %s", job.id, exc, exc_info=True)
                job.status = "failed"
                job.stage_status = "failed"
                job.error = str(exc)

        threading.Thread(target=_work, daemon=True, name=f"convert-{job.id}").start()

    def start_generation(
        self,
        job: Job,
        config: PipelineConfig,
        markdown_override: Optional[str] = None,
        on_complete: Optional[Callable[[Job], None]] = None,
    ) -> None:
        """
        Run the expensive half, optionally against user-edited markdown.

        ``on_complete`` fires on the worker thread after a successful run — the
        API uses it to persist the deck into the owner's library.
        """
        if job._markdown_doc is None:
            raise ValueError("conversion has not completed for this job")

        if markdown_override is not None:
            job._markdown_doc.markdown = markdown_override
            job.markdown = markdown_override

        def _progress(stage: str, status: str, fraction: float, detail: str) -> None:
            job.stage = stage
            job.stage_status = status
            job.progress = fraction
            job.detail = detail

        def _work() -> None:
            job.status = "running"
            try:
                job.result = generate(job._markdown_doc, config=config, progress=_progress)
                job.status = "done"
                job.progress = 1.0
                if on_complete:
                    try:
                        on_complete(job)
                    except Exception:
                        # Persisting is best-effort; never fail a good deck.
                        logger.error("job %s post-completion hook failed", job.id, exc_info=True)
            except Exception as exc:
                logger.error("job %s generation failed: %s", job.id, exc, exc_info=True)
                job.status = "failed"
                job.error = str(exc)

        threading.Thread(target=_work, daemon=True, name=f"generate-{job.id}").start()


_store: Optional[JobStore] = None


def get_store() -> JobStore:
    global _store
    if _store is None:
        _store = JobStore()
    return _store


__all__ = ["Job", "JobStore", "get_store"]
