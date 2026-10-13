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


@dataclass
class Script:
    text: str
    request: dict[str, Any] = field(default_factory=dict)
    voice_settings: dict[str, Any] = field(default_factory=dict)


def parse_script(source: str) -> Script:
    """Parse text with optional TOML front matter delimited by `+++` lines."""
    lines = source.splitlines()
    if not lines or lines[0].strip() != DELIMITER:
        return Script(text=source.strip())

    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == DELIMITER)
    except StopIteration:
        raise ValueError(f"front matter is not closed with '{DELIMITER}'") from None

    meta = tomllib.loads("\n".join(lines[1:end]))
    unknown = meta.keys() - REQUEST_KEYS - VOICE_SETTINGS_KEYS
    if unknown:
        raise ValueError(f"unknown front matter keys: {', '.join(sorted(unknown))}")

    return Script(
        text="\n".join(lines[end + 1 :]).strip(),
        request={k: v for k, v in meta.items() if k in REQUEST_KEYS},
        voice_settings={k: v for k, v in meta.items() if k in VOICE_SETTINGS_KEYS},
    )


def load_script(path: str | Path) -> Script:
    return parse_script(Path(path).read_text(encoding="utf-8"))
