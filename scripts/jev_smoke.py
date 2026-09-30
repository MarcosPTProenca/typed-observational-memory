"""Smoke test for the real Jev API. Requires TYPESAFE_API_KEY.

Run: uv run python scripts/jev_smoke.py
Loads .env if TYPESAFE_API_KEY is not already exported.
"""

import asyncio
import os
from pathlib import Path

from tom.providers.jev import JevClassifier


def _load_env() -> None:
    if os.environ.get("TYPESAFE_API_KEY"):
        return
    env = Path(__file__).resolve().parents[1] / ".env"
    if not env.exists():
        return
    for line in env.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.removeprefix("export ").partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


SAMPLES = [
    "Never deploy to production on Fridays without explicit approval from the on-call lead.",
    "To reset the staging database, run `make db-reset` and then re-seed with `make seed`.",
    "The user prefers dark mode and concise answers.",
    "By the way, the weather was nice yesterday.",
]


async def main() -> None:
    _load_env()
    if not os.environ.get("TYPESAFE_API_KEY"):
        raise SystemExit("TYPESAFE_API_KEY not found (env or .env).")

    jev = JevClassifier()
    try:
        for text in SAMPLES:
            labels = await jev.classify_labels(text)
            gate = await jev.confirm_critical(text)
            print(f"\n> {text}")
            print(
                f"  type={labels.knowledge_type.value}  retention={labels.retention.value}  "
                f"importance={labels.importance.value}  confidence={labels.confidence:.3f}  "
                f"gate_critical={gate:.3f}"
            )
    finally:
        await jev.aclose()

    print(f"\ncalls={jev.last_calls}  est_input_tokens={jev.last_input_tokens}")


if __name__ == "__main__":
    asyncio.run(main())
