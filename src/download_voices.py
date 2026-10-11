"""Pre-download Pocket TTS voices so main.py doesn't have to fetch them on first use.

Files land in the Hugging Face cache (the same place pocket_tts reads from).

Examples:
    uv run src/download_voices.py bill_boerst
    uv run src/download_voices.py jane george mary
    uv run src/download_voices.py --all
    uv run src/download_voices.py --lang en
"""
import argparse
import sys

from main import LANGUAGE_NAMES, POCKET_TTS_VOICES

# Voice data lives in main.py; keyed here by pocket_tts language name.
VOICES = {LANGUAGE_NAMES[code]: voices for code, voices in POCKET_TTS_VOICES.items()}
LANG_CODES = LANGUAGE_NAMES
LANGUAGE_OF = {voice: lang for lang, voices in VOICES.items() for voice in voices}


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Download Pocket TTS voices ahead of time.")
    parser.add_argument("voices", nargs="*", help="Voice names to download (comma-separated lists also work).")
    parser.add_argument("--all", action="store_true", help="Download every voice.")
    parser.add_argument(
        "--lang",
        choices=sorted(LANG_CODES),
        help="Download every voice for this language code.",
    )
    parser.add_argument("--list", action="store_true", help="List available voices and exit.")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    if args.list:
        for code, lang in LANG_CODES.items():
            print(f"{code}: {', '.join(VOICES[lang])}")
        return 0

    names = [n for arg in args.voices for n in arg.split(",") if n]
    if args.all:
        names += [v for voices in VOICES.values() for v in voices]
    if args.lang:
        names += VOICES[LANG_CODES[args.lang]]
    names = list(dict.fromkeys(names))  # dedupe, keep order

    if not names:
        print("download_voices: specify voice names, --lang, or --all (see --list)", file=sys.stderr)
        return 1
    unknown = [n for n in names if n not in LANGUAGE_OF]
    if unknown:
        print(f"download_voices: unknown voice(s): {', '.join(unknown)} (see --list)", file=sys.stderr)
        return 1

    # Imported late so --help and --list stay fast.
    from pocket_tts.utils.utils import download_if_necessary, get_predefined_voice

    failed = []
    for name in names:
        try:
            path = download_if_necessary(get_predefined_voice(LANGUAGE_OF[name], name))
            print(f"{name}: {path}")
        except Exception as e:
            print(f"{name}: FAILED ({e})", file=sys.stderr)
            failed.append(name)

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
