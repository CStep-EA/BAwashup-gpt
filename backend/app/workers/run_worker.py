"""
Bower Ag CowCare Tool — ARQ Worker Runner
Sprint 14: Entry point to run the ARQ worker process.

Usage: python -m app.workers.run_worker
"""

import asyncio
import os
import sys

# Ensure backend root is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from dotenv import load_dotenv
load_dotenv()

from arq import run_worker as arq_run_worker
from app.workers.settings import WorkerSettings


def main():
    """Run the ARQ worker."""
    arq_run_worker(WorkerSettings)


if __name__ == "__main__":
    main()
