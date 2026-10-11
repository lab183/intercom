# intercom

A small command-line tool that converts text to speech with
[Pocket TTS](https://pypi.org/project/pocket-tts/) and plays it. It also ships an
[MCP server](#mcp-server) so a local agent can talk through it. Windows only (uses `winsound`).

## Install

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```
uv tool install .
```

This puts the `intercom` and `intercom-mcp` commands on your PATH. After editing the code, reinstall with
`uv tool install --reinstall .`, or use `uv tool install --editable .` while developing.

You can also run it without installing: `uv run intercom "Hello"`.

## Usage

```
intercom "Hello world, this is a test."
echo "Piped text" | intercom
intercom -v jane "Different voice"
intercom -v lola "Hola mundo"          # language is picked from the voice
intercom -o out.wav "Speak and also save"
intercom --no-play -o out.wav "Save only"
intercom --list-voices
```

| Option | Description |
| --- | --- |
| `text` | Text to speak. If omitted (or `-`), text is read from stdin. |
| `-v`, `--voice` | Pre-made voice name, local audio file, or `hf://` URL (default: `anna`). |
| `-l`, `--lang` | Model language code (`en`, `it`, `es`, `de`, `pt`, `fr`, `nl`). Inferred automatically for pre-made voices, otherwise defaults to `en`. Set it when using a custom voice file in another language. |
| `-o`, `--output FILE` | Also save the generated audio to a WAV file. |
| `--no-play` | Don't play the audio (requires `--output`). |
| `--list-voices` | List the pre-made voices and exit. |

## MCP server

`src/mcp_server.py` exposes the same engine to MCP clients (Claude Code, Claude Desktop, etc.) over
stdio. The model is loaded on the first call and kept in memory, so later messages are much faster
than running the CLI each time.

Register it with your client. For Claude Code:

```
claude mcp add intercom -- uv run --directory C:/path/to/intercom intercom-mcp
```

Or, if you installed it with `uv tool install .`, point the client at the `intercom-mcp` command.
For clients configured with JSON:

```json
{
  "mcpServers": {
    "intercom": {
      "command": "uv",
      "args": ["run", "--directory", "C:/path/to/intercom", "intercom-mcp"]
    }
  }
}
```

| Tool | Description |
| --- | --- |
| `intercom(message, voice?, lang?, wait?, output_path?)` | Speak a message out loud. Returns as soon as playback starts unless `wait` is true. A new message interrupts one still playing. `output_path` (a `.wav`) also saves the audio. |
| `stop_speaking()` | Stop any speech that is currently playing. |
| `list_voices()` | List the pre-made voices by language code. |

`voice` and `lang` behave like `--voice` and `--lang` in the CLI. Requires `mcp` 2.x.

## Utility: src/download_voices.py

The first time a voice is used, its data is downloaded from Hugging Face. `src/download_voices.py`
fetches voices ahead of time into the same cache so `intercom` doesn't have to.

```
uv run src/download_voices.py anna
uv run src/download_voices.py jane george mary      # or: jane,george,mary
uv run src/download_voices.py --lang en             # every voice for a language code
uv run src/download_voices.py --all
uv run src/download_voices.py --list
```

This only covers voices. The model weights are still downloaded on the first run of `intercom`.
