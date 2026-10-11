# intercom

Windows-only text-to-speech tool built on Pocket TTS (`pocket-tts`), shipped as a CLI (`intercom`)
and an MCP server (`intercom-mcp`) so a local agent can speak. Keep it simple: it does one thing,
speaks text. Don't add features (streaming, queues, speed/pitch, cross-platform playback) unless asked.

## Layout

- `src/main.py` — the engine and CLI. `synthesize()` / `load_voice()` cache models and voice
  states; voice and language tables live here (single source of truth).
- `src/mcp_server.py` — MCP server (`intercom`, `stop_speaking`, `list_voices`) over stdio (default) or
  streamable HTTP (`--transport streamable-http`, loopback only unless `--allow-remote`). SSE is
  deliberately not supported. Imports `main` as `engine`.
- `src/download_voices.py` — pre-downloads voices; imports its voice data from `main`.
- Modules are flat `py-modules` under `src/` (see `pyproject.toml`), not a package. The folder is
  still named `ptts` on disk; the project was renamed to `intercom`.

## Commands

- `uv sync` — install; `uv run intercom "text"` — run the CLI; `uv run intercom-mcp` — run the server.
- No test suite. Verify the server by driving it with a real MCP client over stdio
  (`mcp.client.stdio.stdio_client`), not just by importing it.

## Gotchas

- `mcp` is 2.x: use `from mcp.server.mcpserver import MCPServer`, not `FastMCP`. Raise
  `mcp.server.mcpserver.exceptions.ToolError` for errors the agent should see; any other exception
  becomes an opaque "Error executing tool".
- In stdio mode the server speaks MCP over stdout. Never `print()` to stdout in server code; use stderr.
- The HTTP transport has no auth. Keep the loopback-by-default guard; the tool makes sound on the host.
- To test HTTP, start the server in the background on a spare port, use
  `mcp.client.streamable_http.streamable_http_client`, and kill the server afterwards.
- Playback must block in the CLI (`winsound.PlaySound` without `SND_ASYNC`): the process exits and
  the temp file is deleted right after. The server is long-lived, so it uses `SND_ASYNC` and keeps
  the temp file until the next clip, stop, or exit.
- pocket_tts reads its YAML configs with the locale encoding, which breaks on Windows;
  `patch_config_loading()` re-implements the load as UTF-8. Keep it.
- Don't run `intercom` or the MCP tools for real unless needed; they play audio on the user's speakers.

## Conventions

- Update `README.md` and `pyproject.toml` when commands, tools or file paths change.
- Commit only when asked. Commit messages end with the Co-Authored-By line from the session's attribution reminder.
- Generated audio (`*.wav`) is gitignored; don't leave stray output files in the repo.
