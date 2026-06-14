from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageStat


def analyze_image(image_path: str | None) -> tuple[str, list[str]]:
    if not image_path:
        return "", []

    path = Path(image_path)
    if not path.exists():
        return "Image file was referenced but could not be found.", ["Image path missing on disk"]

    try:
        with Image.open(path) as image:
            width, height = image.size
            mode = image.mode
            thumbnail = image.convert("L").resize((1, 1))
            brightness = ImageStat.Stat(thumbnail).mean[0]
    except Exception as exc:  # pragma: no cover - defensive for corrupted images
        return f"Image could not be analyzed locally: {exc}", ["Upload a valid image file"]

    notes: list[str] = []
    if width < 640 or height < 480:
        notes.append("Image is small; a wider street-level photo would improve evidence.")
    if brightness < 45:
        notes.append("Image appears dark; a clearer daylight image may help.")
    if brightness > 230:
        notes.append("Image appears very bright; details may be washed out.")

    summary = f"Uploaded image: {width}x{height}px, mode {mode}, estimated brightness {brightness:.0f}/255."
    return summary, notes
