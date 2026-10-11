"""MCP server that lets a local agent speak through Pocket TTS (Windows only).

Run it over stdio with `intercom-mcp` (or `uv run src/mcp_server.py`) and register it with
your MCP client. See README.md for an example configuration.
"""
import asyncio
import atexit
import contextlib
import os
import sys
import tempfile
import threading
import winsound
from pathlib import Path

import scipy.io.wavfile
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

import main as engine

mcp = MCPServer(
    "intercom",
    instructions="Text-to-speech 'intercom': use `intercom` to say something out loud on "
                 "the user's computer, `stop_speaking` to cut it off, and `list_voices` "
                 "to see which voices exist.",
)

# Pocket TTS models aren't safe to drive from several threads at once.
_synth_lock = threading.Lock()
# winsound can't play from memory asynchronously, so the temp file of the clip that is
# currently playing is kept until the next clip, stop, or exit.
_playing_path = None


def _cleanup_playing():
    global _playing_path
    if _playing_path:
        with contextlib.suppress(OSError):
            os.unlink(_playing_path)
        _playing_path = None


atexit.register(_cleanup_playing)


def _synthesize(text, voice, lang):
    # stdout is the MCP protocol channel; keep stray library output off it.
    with _synth_lock, contextlib.redirect_stdout(sys.stderr):
        return engine.synthesize(text, voice, lang)


def _play(pcm, sample_rate, wait):
    global _playing_path
    winsound.PlaySound(None, winsound.SND_PURGE)
    _cleanup_playing()
    fd, path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    scipy.io.wavfile.write(path, sample_rate, pcm)
    if wait:
        try:
            winsound.PlaySound(path, winsound.SND_FILENAME)
        finally:
            os.unlink(path)
    else:
        _playing_path = path
        winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)


@mcp.tool()
async def intercom(
    message: str,
    voice: str = engine.DEFAULT_VOICE,
    lang: str | None = None,
    wait: bool = False,
    output_path: str | None = None,
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
        output_path: Optional path of a .wav file to also save the audio to.
    """
    message = message.strip()
    if not message:
        raise ToolError("message is empty")
    if lang is not None and lang not in engine.LANGUAGE_NAMES:
        raise ToolError(f"unknown lang {lang!r}; choose from {', '.join(engine.LANGUAGE_NAMES)}")
    if output_path and Path(output_path).suffix.lower() != ".wav":
        raise ToolError("output_path must end in .wav")

    pcm, sample_rate = await asyncio.to_thread(_synthesize, message, voice, lang)
    if output_path:
        scipy.io.wavfile.write(output_path, sample_rate, pcm)
    await asyncio.to_thread(_play, pcm, sample_rate, wait)

    seconds = len(pcm) / sample_rate
    saved = f", saved to {output_path}" if output_path else ""
    return f"Spoke {seconds:.1f}s of audio with voice {voice!r}{saved}."


@mcp.tool()
def stop_speaking() -> str:
    """Immediately stop any speech that is currently playing."""
    winsound.PlaySound(None, winsound.SND_PURGE)
    _cleanup_playing()
    return "Stopped playback."


@mcp.tool()
def list_voices() -> dict[str, list[str]]:
    """List the pre-made voices, grouped by language code."""
    return engine.POCKET_TTS_VOICES


def main():
    mcp.run()


if __name__ == "__main__":
    main()
