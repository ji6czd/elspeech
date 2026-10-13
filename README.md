# elspeech

A command-line tool for generating speech using Eleven Labs.

## Installation

```bash
uv sync
```

## Usage

```bash
uv run elspeech -t "こんにちは、世界！" -p
```

## Script files

`-i` reads a text file with optional TOML front matter between `+++` lines
(see `samples/hello.txt`).

### Dialogue (multiple speakers)

If the front matter has a `[speakers]` table, the script is sent to the Text to
Dialogue API. Each body line is `name: text`; a line without a label continues
the previous line. `voice_id` cannot be combined with `[speakers]`.

```
+++
model_id = "eleven_v4"

[speakers]
chuck = "<voice id>"
aya = "<voice id>"
+++
chuck: こんにちは。
aya: [laughs] こんにちは。
```

Only `stability` and `similarity_boost` are accepted as voice settings in
dialogue mode. Keep the total text under about 2,000 characters.
