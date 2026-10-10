# ptts

A small command-line tool that converts text to speech with
[Pocket TTS](https://pypi.org/project/pocket-tts/) and plays it. Windows only (uses `winsound`).

## Install

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```
uv tool install .
```

This puts a `ptts` command on your PATH. After editing the code, reinstall with
`uv tool install --reinstall .`, or use `uv tool install --editable .` while developing.

You can also run it without installing: `uv run ptts "Hello"`.

## Usage

```
ptts "Hello world, this is a test."
echo "Piped text" | ptts
ptts -v jane "Different voice"
ptts -v lola "Hola mundo"          # language is picked from the voice
ptts -o out.wav "Speak and also save"
ptts --no-play -o out.wav "Save only"
ptts --list-voices
```

| Option | Description |
| --- | --- |
| `text` | Text to speak. If omitted (or `-`), text is read from stdin. |
| `-v`, `--voice` | Pre-made voice name, local audio file, or `hf://` URL (default: `anna`). |
| `-l`, `--lang` | Model language code (`en`, `it`, `es`, `de`, `pt`, `fr`, `nl`). Inferred automatically for pre-made voices, otherwise defaults to `en`. Set it when using a custom voice file in another language. |
| `-o`, `--output FILE` | Also save the generated audio to a WAV file. |
| `--no-play` | Don't play the audio (requires `--output`). |
| `--list-voices` | List the pre-made voices and exit. |

## Utility: download_voices.py

The first time a voice is used, its data is downloaded from Hugging Face. `download_voices.py`
fetches voices ahead of time into the same cache so `ptts` doesn't have to.

```
uv run download_voices.py anna
uv run download_voices.py jane george mary      # or: jane,george,mary
uv run download_voices.py --lang en             # every voice for a language code
uv run download_voices.py --all
uv run download_voices.py --list
```

This only covers voices. The model weights are still downloaded on the first run of `ptts`.
