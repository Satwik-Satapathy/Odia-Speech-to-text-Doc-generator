"""Sarvam Batch API boundary.

The running MVP keeps orchestration in main.py while this module documents the
vendor-facing contract that should become its own service as persistence grows.
"""

from typing import Any, Protocol


class BatchClient(Protocol):
    def create_job(self, **options: Any) -> Any: ...
    def upload_files(self, file_paths: list[str]) -> Any: ...
    def start(self) -> Any: ...
    def wait_until_complete(self, poll_interval: int = 5, timeout: int = 7200) -> Any: ...
    def download_outputs(self, output_dir: str) -> Any: ...


BATCH_OPTIONS = {
    "model": "saaras:v3",
    "mode": "transcribe",
    "language_code": "od-IN",
    "with_diarization": True,
}
