import argparse
import os
import sys
from typing import Any

from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from elevenlabs.play import play, save
from elevenlabs.types import DialogueInput, VoiceSettings

from elspeech.script import DialogueLine, Script, load_script

load_dotenv()


DEFAULT_REQUEST = {
    "voice_id": "HIGUfNOdjuWQwwapnTRW",
    # "model_id": "eleven_v4",
    "model_id": "eleven_v4_turbo",
    "output_format": "mp3_24000_48",
    "language_code": "ja",
}


def generate_speech(
    text: str,
    voice_settings: dict[str, Any] | None = None,
    **request: Any,
) -> bytes:
    elevenlabs = ElevenLabs(
        api_key=os.getenv("ELEVENLABS_API_KEY"),
    )
    return b"".join(
        elevenlabs.text_to_speech.convert(
            text=text,
            voice_settings=VoiceSettings(**voice_settings) if voice_settings else None,
            **{**DEFAULT_REQUEST, **request},
        )
    )


# Voice settings supported by the dialogue API, mapped to its setting names.
DIALOGUE_SETTINGS_MAP = {"stability": "stability", "similarity_boost": "similarity"}
# Above this, the API may terminate early or reject the request.
DIALOGUE_MAX_CHARS = 2000


def generate_dialogue(
    lines: list[DialogueLine],
    voice_settings: dict[str, Any] | None = None,
    **request: Any,
) -> bytes:
    unsupported = set(voice_settings or {}) - DIALOGUE_SETTINGS_MAP.keys()
    if unsupported:
        raise ValueError(
            f"voice settings not supported in dialogue mode: "
            f"{', '.join(sorted(unsupported))}"
        )
    settings = {DIALOGUE_SETTINGS_MAP[k]: v for k, v in (voice_settings or {}).items()}

    elevenlabs = ElevenLabs(
        api_key=os.getenv("ELEVENLABS_API_KEY"),
    )
    request = {**DEFAULT_REQUEST, **request}
    request.pop("voice_id")  # each dialogue line carries its own voice
    return b"".join(
        elevenlabs.text_to_dialogue.convert(
            inputs=[DialogueInput(text=l.text, voice_id=l.voice_id) for l in lines],
            settings=settings or None,
            **request,
        )
    )


def main():
    parser = argparse.ArgumentParser(description="Generate speech using Eleven Labs.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("-t", "--text", type=str, help="Text to convert to speech")
    source.add_argument(
        "-i", "--input", type=str, help="Input text file to convert to speech"
    )
    parser.add_argument(
        "-p", "--play", action="store_true", help="Play the generated speech"
    )
    parser.add_argument(
        "-o",
        "--outfile",
        type=str,
        help="Output file for the generated speech",
    )
    parser.add_argument(
        "-l",
        "--language",
        type=str,
        help="Language code for the speech (overrides the front matter)",
    )

    args = parser.parse_args()

    if not (args.play or args.outfile):
        parser.error("at least one of -p/--play or -o/--outfile is required")

    if args.input:
        try:
            script = load_script(args.input)
        except (OSError, ValueError) as e:
            parser.error(f"{args.input}: {e}")
    else:
        script = Script(text=args.text)

    request = dict(script.request)
    if args.language:
        request["language_code"] = args.language

    if script.dialogue:
        total = sum(len(l.text) for l in script.dialogue)
        if total > DIALOGUE_MAX_CHARS:
            print(
                f"warning: dialogue has {total} characters; more than "
                f"{DIALOGUE_MAX_CHARS} may fail or be cut off",
                file=sys.stderr,
            )
        try:
            audio = generate_dialogue(script.dialogue, script.voice_settings, **request)
        except ValueError as e:
            parser.error(str(e))
    else:
        audio = generate_speech(script.text, script.voice_settings, **request)
    if args.play:
        play(audio)
    if args.outfile:
        save(audio, args.outfile)


if __name__ == "__main__":
    main()
