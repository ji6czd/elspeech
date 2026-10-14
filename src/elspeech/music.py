import argparse
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from elevenlabs.play import play, save

from elspeech.script import split_front_matter

load_dotenv()

# Keys passed straight through to music.compose().
REQUEST_KEYS = {
    "model_id",
    "music_length_ms",
    "force_instrumental",
    "seed",
    "output_format",
}

DEFAULT_REQUEST = {
    "model_id": "music_v2_5",
    "output_format": "mp3_44100_128",
}


@dataclass
class MusicScript:
    prompt: str
    request: dict[str, Any] = field(default_factory=dict)


def load_music_script(path: str | Path) -> MusicScript:
    """Read a prompt file with optional TOML front matter between `+++` lines."""
    meta, body = split_front_matter(Path(path).read_text(encoding="utf-8"))
    unknown = meta.keys() - REQUEST_KEYS
    if unknown:
        raise ValueError(f"unknown front matter keys: {', '.join(sorted(unknown))}")
    if not body:
        raise ValueError("prompt is empty")
    return MusicScript(prompt=body, request=meta)


def generate_music(prompt: str, **request: Any) -> bytes:
    elevenlabs = ElevenLabs(
        api_key=os.getenv("ELEVENLABS_API_KEY"),
    )
    return b"".join(
        elevenlabs.music.compose(
            prompt=prompt,
            **{**DEFAULT_REQUEST, **request},
        )
    )


def main():
    parser = argparse.ArgumentParser(description="Generate music using Eleven Labs.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("-t", "--text", type=str, help="Prompt describing the music")
    source.add_argument(
        "-i", "--input", type=str, help="Prompt file with optional front matter"
    )
    parser.add_argument(
        "-p", "--play", action="store_true", help="Play the generated music"
    )
    parser.add_argument(
        "-o", "--outfile", type=str, help="Output file for the generated music"
    )
    parser.add_argument(
        "-d",
        "--duration",
        type=float,
        help="Length in seconds, 3 to 600 (overrides the front matter)",
    )
    parser.add_argument(
        "--instrumental",
        action="store_true",
        help="Force instrumental, no vocals (overrides the front matter)",
    )

    args = parser.parse_args()

    if not (args.play or args.outfile):
        parser.error("at least one of -p/--play or -o/--outfile is required")

    if args.input:
        try:
            script = load_music_script(args.input)
        except (OSError, ValueError) as e:
            parser.error(f"{args.input}: {e}")
    else:
        script = MusicScript(prompt=args.text)

    request = dict(script.request)
    if args.duration is not None:
        request["music_length_ms"] = int(args.duration * 1000)
    if args.instrumental:
        request["force_instrumental"] = True

    audio = generate_music(script.prompt, **request)
    if args.play:
        play(audio)
    if args.outfile:
        save(audio, args.outfile)


if __name__ == "__main__":
    main()
