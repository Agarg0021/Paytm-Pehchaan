from __future__ import annotations

from pathlib import Path

from hindi import announcement

AMOUNTS = [60, 85, 175, 240, 310]
OUT = Path(__file__).resolve().parents[1] / "frontend" / "public" / "audio"


def generate() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    from gtts import gTTS

    for n in AMOUNTS:
        path = OUT / f"{n}.mp3"
        gTTS(text=announcement(n), lang="hi").save(str(path))
        print("wrote", path)


if __name__ == "__main__":
    generate()
