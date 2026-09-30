import pytest

from tom.pi_bridge import handle, make_memory


@pytest.mark.asyncio
async def test_pi_bridge_persists_and_projects_tom_memory(tmp_path):
    memory = make_memory(str(tmp_path / "tom.sqlite"))
    await handle(memory, {
        "command": "ingest",
        "session_id": "pi",
        "events": [{"id": "u1", "type": "user", "content": "Never edit generated files"}],
    })
    await handle(memory, {"command": "compact", "session_id": "pi", "budget": 256})

    result = await handle(memory, {"command": "context", "session_id": "pi", "budget": 256})

    assert result["llm_calls"] == 0
    assert "Never edit generated files" in result["text"]


@pytest.mark.asyncio
async def test_pi_bridge_compacts_empty_session(tmp_path):
    memory = make_memory(str(tmp_path / "tom.sqlite"))
    await handle(memory, {"command": "context", "session_id": "pi", "budget": 256})
    assert await handle(memory, {"command": "compact", "session_id": "pi", "budget": 256}) == {
        "ok": True, "llm_calls": 0,
    }
    await memory.aclose()
