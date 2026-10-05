"""Configure the official Premiere MCP server without duplicating its bridge."""
import argparse
import json
import re
from pathlib import Path

SERVER_VERSION = "1.19.1"
CORE_TOOLS = (
    "verify_premiere_connection", "get_capabilities", "get_project_info",
    "list_project_items", "get_bin_contents", "create_project", "open_project",
    "save_project", "save_project_as", "create_bin", "import_media",
    "create_sequence", "create_sequence_from_clips", "get_active_sequence",
    "get_sequence_settings", "overwrite_clip", "trim_clip", "move_clip",
    "get_clip_properties", "get_effect_properties", "set_effect_property",
    "add_marker", "create_caption_track", "read_sequence_captions",
    "validate_export_preset", "export_sequence", "export_frame", "set_playhead_position",
)


def configure_codex(path, *, backup):
    """Restrict an already registered server; preserve unrelated configuration."""
    path, backup = Path(path), Path(backup)
    source = path.read_text(encoding="utf-8")
    header = "[mcp_servers.premiere-pro]"
    if source.count(header) != 1:
        raise ValueError("Register premiere-pro with codex mcp add first")
    start = source.index(header) + len(header)
    match = re.search(r"(?m)^\[", source[start:])
    end = start + match.start() if match else len(source)
    section = source[start:end]
    # These keys are owned by this setup step; keep command, args and environment.
    for key in ("enabled_tools", "startup_timeout_sec", "tool_timeout_sec"):
        section = re.sub(rf"(?m)^{key}\s*=\s*(?:\[[\s\S]*?\]|[^\n]*)\n?", "", section)
    section = section.lstrip("\r\n")
    settings = (
        "\nenabled_tools = " + json.dumps(CORE_TOOLS) + "\n"
        "startup_timeout_sec = 30\ntool_timeout_sec = 180\n"
    )
    updated = source[:start] + settings + section + source[end:]
    # Python 3.11+ validates TOML before any mutation.
    try:
        import tomllib
    except ImportError as exc:
        raise RuntimeError("Configuration requires Python 3.11 or later") from exc
    tomllib.loads(updated)
    backup.parent.mkdir(parents=True, exist_ok=True)
    if not backup.exists():
        backup.write_text(source, encoding="utf-8")
    path.write_text(updated, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("config")
    parser.add_argument("--backup", required=True)
    args = parser.parse_args()
    configure_codex(args.config, backup=args.backup)
    print(f"Premiere MCP configured: {len(CORE_TOOLS)} tools; 180s tool timeout")


if __name__ == "__main__":
    main()
