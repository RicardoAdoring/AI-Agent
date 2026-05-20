from app.core.config import get_settings
from app.mcp.config import load_mcp_config


def test_load_claude_style_amap_mcp_config(tmp_path, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "amap_maps_api_key", "test-key")
    path = tmp_path / "mcp.json"
    path.write_text(
        '{"mcpServers":{"amap-maps":{"command":"npx.cmd","args":["-y","@amap/amap-maps-mcp-server"],"env":{"AMAP_MAPS_API_KEY":"${AMAP_MAPS_API_KEY}"}}}}',
        encoding="utf-8",
    )

    servers = load_mcp_config(path)

    assert len(servers) == 1
    assert servers[0].name == "amap-maps"
    assert servers[0].enabled is True
    assert servers[0].env["AMAP_MAPS_API_KEY"] == "test-key"


def test_load_servers_array_config(tmp_path):
    path = tmp_path / "mcp.json"
    path.write_text('{"servers":[{"name":"demo","command":"python","enabled":true}]}', encoding="utf-8")

    servers = load_mcp_config(path)

    assert servers[0].name == "demo"
    assert servers[0].command == "python"
    assert servers[0].enabled is True
