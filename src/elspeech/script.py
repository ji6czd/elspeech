import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DELIMITER = "+++"

# Keys passed straight through to text_to_speech.convert().
REQUEST_KEYS = {"language_code", "voice_id", "model_id", "output_format", "seed"}
# Keys collected into the VoiceSettings object.
VOICE_SETTINGS_KEYS = {
    "stability",
    "similarity_boost",
    "style",
    "speed",
    "use_speaker_boost",
}
# Front matter table mapping speaker names to voice ids (enables dialogue mode).
SPEAKERS_KEY = "speakers"

# "name: text" at the start of a body line (ASCII name, half- or full-width colon).
SPEAKER_LINE = re.compile(r"^([A-Za-z0-9_-]+)\s*[:：]\s*(.*)$")


@dataclass
class DialogueLine:
    voice_id: str
    text: str


@dataclass
class Script:
    text: str
    request: dict[str, Any] = field(default_factory=dict)
    voice_settings: dict[str, Any] = field(default_factory=dict)
    # Non-empty only in dialogue mode (front matter has a [speakers] table).
    dialogue: list[DialogueLine] = field(default_factory=list)


def parse_dialogue(body: str, speakers: dict[str, str]) -> list[DialogueLine]:
    """Split `name: text` lines into dialogue lines.

    A line without a speaker label continues the previous speaker's line.
    """
    names: list[str] = []
    texts: list[str] = []
    for lineno, line in enumerate(body.splitlines(), 1):
        if not line.strip():
            continue
        m = SPEAKER_LINE.match(line.strip())
        if m:
            name, text = m.groups()
            if name not in speakers:
                raise ValueError(f"unknown speaker '{name}' in body line {lineno}")
            names.append(name)
            texts.append(text)
        elif texts:
            texts[-1] += "\n" + line.strip()
        else:
            raise ValueError(f"body line {lineno} has no speaker label")
    return [DialogueLine(speakers[n], t) for n, t in zip(names, texts) if t]


def split_front_matter(source: str) -> tuple[dict[str, Any], str]:
    """Split text into (TOML front matter delimited by `+++` lines, body)."""
    lines = source.splitlines()
    if not lines or lines[0].strip() != DELIMITER:
        return {}, source.strip()

    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == DELIMITER)
    except StopIteration:
        raise ValueError(f"front matter is not closed with '{DELIMITER}'") from None

    meta = tomllib.loads("\n".join(lines[1:end]))
    return meta, "\n".join(lines[end + 1 :]).strip()


def parse_script(source: str) -> Script:
    """Parse text with optional TOML front matter delimited by `+++` lines."""
    meta, body = split_front_matter(source)
    if not meta:
        return Script(text=body)

    unknown = meta.keys() - REQUEST_KEYS - VOICE_SETTINGS_KEYS - {SPEAKERS_KEY}
    if unknown:
        raise ValueError(f"unknown front matter keys: {', '.join(sorted(unknown))}")

    request = {k: v for k, v in meta.items() if k in REQUEST_KEYS}
    voice_settings = {k: v for k, v in meta.items() if k in VOICE_SETTINGS_KEYS}

    dialogue: list[DialogueLine] = []
    if SPEAKERS_KEY in meta:
        speakers = meta[SPEAKERS_KEY]
        if not isinstance(speakers, dict) or not speakers:
            raise ValueError(f"'{SPEAKERS_KEY}' must be a non-empty table")
        if not all(isinstance(v, str) for v in speakers.values()):
            raise ValueError(f"'{SPEAKERS_KEY}' values must be voice id strings")
        if "voice_id" in request:
            raise ValueError(f"'voice_id' cannot be combined with '{SPEAKERS_KEY}'")
        dialogue = parse_dialogue(body, speakers)
        if not dialogue:
            raise ValueError("dialogue has no lines")

    return Script(
        text=body,
        request=request,
        voice_settings=voice_settings,
        dialogue=dialogue,
    )


def load_script(path: str | Path) -> Script:
    return parse_script(Path(path).read_text(encoding="utf-8"))
