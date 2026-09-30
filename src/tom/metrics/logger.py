import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from .models import RunMetrics


class ExperimentLogger:
    """Append one JSON object per run, without rewriting previous results."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def log(self, metrics: RunMetrics, *, config: Any | None = None) -> None:
        record = metrics.model_dump(mode="json")
        if config is not None:
            record["config"] = _as_json_object(config)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as output:
            output.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def _as_json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    elif hasattr(value, "__dict__") and not isinstance(value, dict):
        value = vars(value)
    if not isinstance(value, dict):
        raise TypeError("experiment config must be a mapping or Pydantic model")
    json.dumps(value)
    return value
