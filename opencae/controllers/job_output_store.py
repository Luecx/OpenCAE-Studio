"""Persists and caches textual solver output for JobManager.

This module owns log-file I/O and the bounded in-memory output cache. It does
not emit Qt signals or mutate Job entities.
"""

from __future__ import annotations

from pathlib import Path


class JobOutputStore:
    """Bounded cache and append-only file store for per-job solver output."""

    def __init__(self, project_provider, *, maximum_characters: int = 2_000_000):
        """Create a store that resolves Job metadata from ``project_provider``."""
        self._project_provider = project_provider
        self._maximum_characters = int(maximum_characters)
        self._cache: dict[str, str] = {}

    def read(self, job_id: str) -> str:
        """Return cached output, loading the persisted log on first access."""
        key = str(job_id or "")
        if key in self._cache:
            return self._cache[key]

        project = self._project_provider()
        job = project.try_resolve(key) if key else None
        path = Path(getattr(job, "output_file", "")) if job else None
        if not path or not path.is_file():
            return ""

        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            text = ""

        # Keep the UI responsive even when a long-running solver produces a very
        # large log. The full file remains on disk; only the display cache is cut.
        self._cache[key] = text[-self._maximum_characters :]
        return self._cache[key]

    def append(self, job_id: str, text: str) -> str:
        """Append output to disk/cache and return the current cached tail."""
        key = str(job_id)
        addition = str(text)
        value = self._cache.get(key, self.read(key)) + addition
        self._cache[key] = value[-self._maximum_characters :]

        project = self._project_provider()
        job = project.try_resolve(key)
        path = Path(getattr(job, "output_file", "")) if job else None
        if path:
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                with path.open("a", encoding="utf-8") as stream:
                    stream.write(addition)
            except OSError:
                # Solver output is auxiliary runtime information. A logging
                # failure must not terminate or corrupt the analysis lifecycle.
                pass

        return self._cache[key]
