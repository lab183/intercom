"""MCP server that lets a local agent speak through Pocket TTS.

Run it with `intercom-mcp` (or `uv run src/mcp_server.py`): over stdio by default, or as an
HTTP server with `--transport streamable-http`. See README.md for client configuration.
"""
import argparse
import asyncio
import sys
import threading
from pathlib import Path

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

import main as engine
import player

mcp = MCPServer(
    "intercom",
    instructions="Text-to-speech 'intercom': use `intercom` to say something out loud on "
                 "the user's computer, `stop_speaking` to cut it off, and `list_voices` "
                 "to see which voices exist.",
)

# Pocket TTS models aren't safe to drive from several threads at once.
_synth_lock = threading.Lock()


def _synthesize(text, voice, lang):
    with _synth_lock:
        return engine.synthesize(text, voice, lang)


def _warm_up():
    """Load the default model and voice so the first message isn't slow."""
    try:
        with _synth_lock:
            engine.load_voice()
    except Exception as e:
        print(f"intercom: warm-up failed: {e}", file=sys.stderr)


def _check_voice(voice):
    """Fail early, with a useful message, on voices that can't possibly load."""
    if engine.language_for_voice(voice) or voice.startswith(("hf://", "http")):
        return
    if not Path(voice).is_file():
        raise ToolError(
            f"unknown voice {voice!r}: use a name from list_voices, an hf:// URL, "
            "or the path to an audio file"
        )


def _play(pcm, sample_rate, wait):
    try:
        player.play(pcm, sample_rate, block=wait)  # replaces any clip still playing
    except player.PlaybackError as e:
        raise ToolError(str(e)) from e


@mcp.tool()
async def intercom(
    message: str,
    voice: str = engine.DEFAULT_VOICE,
    lang: str | None = None,
    wait: bool = False,
) -> str:
    """Speak a message out loud on the user's computer using text-to-speech.

    Args:
        message: The text to speak.
        voice: A pre-made voice name (see list_voices), a local audio file to clone, or an
            hf:// URL. Defaults to "anna".
        lang: Model language code (en, it, es, de, pt, fr, nl). Inferred from pre-made
            voices; set it only when using a custom voice file in another language.
        wait: If true, return only after the audio has finished playing. By default the
            call returns as soon as playback starts. Starting a new message interrupts
            one that is still playing.
    """
    message = message.strip()
    if not message:
        raise ToolError("message is empty")
    if lang is not None and lang not in engine.LANGUAGE_NAMES:
        raise ToolError(f"unknown lang {lang!r}; choose from {', '.join(engine.LANGUAGE_NAMES)}")
    _check_voice(voice)

    try:
        pcm, sample_rate = await asyncio.to_thread(_synthesize, message, voice, lang)
    except Exception as e:
        raise ToolError(f"speech generation failed: {e}") from e
    await asyncio.to_thread(_play, pcm, sample_rate, wait)

    return f"Spoke {len(pcm) / sample_rate:.1f}s of audio with voice {voice!r}."


@mcp.tool()
def stop_speaking() -> str:
    """Immediately stop any speech that is currently playing."""
    try:
        player.stop()
    except player.PlaybackError as e:
        raise ToolError(str(e)) from e
    return "Stopped playback."


@mcp.tool()
def list_voices() -> dict[str, list[str]]:
    """List the pre-made voices, grouped by language code."""
    return engine.POCKET_TTS_VOICES


LOOPBACK_HOSTS = ("127.0.0.1", "localhost", "::1")


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        prog="intercom-mcp",
        description="MCP server that speaks text with Pocket TTS.",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http"],
        default="stdio",
        help="stdio (default; the client launches the server) or streamable-http "
             "(a long-running server at http://HOST:PORT/mcp).",
    )
    parser.add_argument("--host", default="127.0.0.1", help="streamable-http bind address (default: 127.0.0.1).")
    parser.add_argument("--port", type=int, default=8000, help="streamable-http port (default: 8000).")
    parser.add_argument(
        "--allow-remote",
        action="store_true",
        help="Allow binding to a non-loopback address. There is no authentication: "
             "anyone who can reach the port can make this computer speak.",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    if (
        args.transport == "streamable-http"
        and args.host not in LOOPBACK_HOSTS
        and not args.allow_remote
    ):
        print(
            f"intercom-mcp: refusing to bind to {args.host!r} without authentication; "
            "pass --allow-remote to override",
            file=sys.stderr,
        )
        return 1

    threading.Thread(target=_warm_up, daemon=True).start()
    if args.transport == "stdio":
        mcp.run()
    else:
        mcp.run("streamable-http", host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
