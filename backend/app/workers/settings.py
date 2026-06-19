"""
Bower Ag CowCare Tool — ARQ Worker Settings
Sprint 14: Configuration for the async job queue worker.
"""

import os
from arq.connections import RedisSettings


class WorkerSettings:
    """ARQ worker settings — imported by arq CLI or run_worker."""

    redis_settings = RedisSettings.from_dsn(
        os.getenv("REDIS_URL", "redis://localhost:6379")
    )

    # Import functions lazily to avoid circular imports
    @staticmethod
    def get_functions():
        from app.workers.video_worker import process_video
        return [process_video]

    functions = property(lambda self: self.get_functions())

    max_jobs = 3
    job_timeout = 600  # 10 minutes max per video job
