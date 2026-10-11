import argparse
import os
import sys
import tempfile
import winsound

import numpy as np
import scipy.io.wavfile

POCKET_TTS_VOICES = {
    "en": ["alba", "anna", "azelma", "bill_boerst", "caro_davy", "charles", "cosette", "eponine", "eve", "fantine", "george", "jane", "jean", "javert", "marius", "mary", "michael", "paul", "peter_yearsley", "stuart_bell", "vera"],
    "it": ["giovanni"],
    "es": ["lola"],
    "de": ["juergen"],
    "pt": ["rafael"],
    "fr": ["estelle"],
    "nl": ["daan"],
}

# Language code -> pocket_tts model language
LANGUAGE_NAMES = {
    "en": "english",
    "it": "italian",
    "es": "spanish",
    "de": "german",
    "pt": "portuguese",
    "fr": "french",
    "nl": "dutch",
}

DEFAULT_VOICE = "anna"


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        prog="intercom",
        description="Convert text to speech with Pocket TTS and play it.",
    )
    parser.add_argument(
        "text",
        nargs="*",
        help="Text to speak. If omitted (or '-'), text is read from stdin.",
    )
    parser.add_argument(
        "-v", "--voice",
        default=DEFAULT_VOICE,
        help=f"Pre-made voice name, local audio file, or hf:// URL (default: {DEFAULT_VOICE}).",
    )
    parser.add_argument(
        "-l", "--lang",
        choices=sorted(LANGUAGE_NAMES),
        help="Model language. Inferred from the voice for pre-made voices; "
             "otherwise defaults to en (set this for custom voice files in another language).",
    )
    parser.add_argument(
        "-o", "--output",
        metavar="FILE",
        help="Also save the generated audio to this WAV file.",
    )
    parser.add_argument(
        "--no-play",
        action="store_true",
        help="Do not play the audio (useful with --output).",
    )
    parser.add_argument(
        "--list-voices",
        action="store_true",
        help="List the pre-made voices and exit.",
    )
    return parser.parse_args(argv)


def list_voices():
    for lang, voices in POCKET_TTS_VOICES.items():
        print(f"{lang}: {', '.join(voices)}")


def language_for_voice(voice):
    for lang, voices in POCKET_TTS_VOICES.items():
        if voice in voices:
            return lang
    return None


def patch_config_loading():
    """pocket_tts reads its YAML configs with the locale encoding, which breaks on
    Windows (cp1252) for the non-English configs. Re-implement the load as UTF-8."""
    import yaml
    from pocket_tts.models import tts_model
    from pocket_tts.utils.config import Config
    from pocket_tts.utils.utils import download_if_necessary

    def load_config_utf8(yaml_path):
        path = download_if_necessary(str(yaml_path))
        with open(path, "r", encoding="utf-8") as f:
            return Config(**yaml.safe_load(f))

    tts_model.load_config = load_config_utf8


def get_text(args):
    if args.text and args.text != ["-"]:
        return " ".join(args.text)
    if sys.stdin.isatty():
        print("Enter text, then press Ctrl+Z and Enter to finish:", file=sys.stderr)
    return sys.stdin.read()


def to_pcm16(audio):
    """Convert float audio in [-1, 1] to 16-bit PCM, which winsound can play."""
    return (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)


_models = {}
_voice_states = {}


def resolve_language(voice, lang=None):
    return lang or language_for_voice(voice) or "en"


def load_voice(voice=DEFAULT_VOICE, lang=None):
    """Load (and cache) the model and voice state; returns (model, voice_state)."""
    # Imported late so --help and --list-voices stay fast.
    from pocket_tts import TTSModel

    lang = resolve_language(voice, lang)
    if lang not in _models:
        patch_config_loading()
        _models[lang] = TTSModel.load_model(language=LANGUAGE_NAMES[lang])
    tts_model = _models[lang]
    if (lang, voice) not in _voice_states:
        _voice_states[(lang, voice)] = tts_model.get_state_for_audio_prompt(voice)
    return tts_model, _voice_states[(lang, voice)]


def synthesize(text, voice=DEFAULT_VOICE, lang=None):
    """Generate speech and return (pcm16 samples, sample rate).

    Models and voice states are cached, so repeated calls in a long-lived process
    (like the MCP server) only pay the load cost once."""
    tts_model, voice_state = load_voice(voice, lang)
    audio = tts_model.generate_audio(voice_state, text)
    # Audio is a 1D torch tensor containing PCM data.
    return to_pcm16(audio.numpy()), tts_model.sample_rate


def main(argv=None):
    args = parse_args(argv)

    if args.list_voices:
        list_voices()
        return 0

    text = get_text(args).strip()
    if not text:
        print("intercom: no text provided", file=sys.stderr)
        return 1
    if args.no_play and not args.output:
        print("intercom: --no-play requires --output", file=sys.stderr)
        return 1

    pcm, sample_rate = synthesize(text, args.voice, args.lang)

    if args.output:
        scipy.io.wavfile.write(args.output, sample_rate, pcm)

    if not args.no_play:
        fd, path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        try:
            scipy.io.wavfile.write(path, sample_rate, pcm)
            # Blocks until playback finishes
            winsound.PlaySound(path, winsound.SND_FILENAME)
        finally:
            os.unlink(path)

    return 0


if __name__ == "__main__":
    sys.exit(main())
