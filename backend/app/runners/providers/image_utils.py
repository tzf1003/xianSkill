from __future__ import annotations

import io
from dataclasses import dataclass

from PIL import Image, ImageOps


_FORMAT_TO_MIME = {
    "GIF": "image/gif",
    "JPEG": "image/jpeg",
    "MPO": "image/mpo",
    "PNG": "image/png",
    "WEBP": "image/webp",
}


@dataclass(frozen=True)
class PreparedInputImage:
    data: bytes
    mime: str
    original_mime: str
    original_format: str
    transcoded: bool


def prepare_input_image(image_bytes: bytes, supported_mimes: set[str]) -> PreparedInputImage:
    try:
        probe = Image.open(io.BytesIO(image_bytes))
        probe.verify()
        image = Image.open(io.BytesIO(image_bytes))
    except Exception as exc:
        raise RuntimeError(
            "上传的文件不是有效的图片格式，请上传 JPEG/PNG/GIF/WebP/常见照片格式"
        ) from exc

    original_format = (image.format or "").upper() or "UNKNOWN"
    original_mime = _FORMAT_TO_MIME.get(original_format, f"image/{original_format.lower()}")
    frame_count = getattr(image, "n_frames", 1)

    if frame_count > 1:
        image.seek(0)

    image = ImageOps.exif_transpose(image)

    if original_mime in supported_mimes and frame_count == 1 and original_format != "MPO":
        return PreparedInputImage(
            data=image_bytes,
            mime=original_mime,
            original_mime=original_mime,
            original_format=original_format,
            transcoded=False,
        )

    has_alpha = image.mode in ("RGBA", "LA") or (
        image.mode == "P" and "transparency" in image.info
    )
    if has_alpha and "image/png" in supported_mimes:
        converted = image.convert("RGBA")
        target_format = "PNG"
        target_mime = "image/png"
        save_kwargs = {"format": "PNG", "optimize": True}
    else:
        converted = image.convert("RGB")
        target_format = "JPEG"
        target_mime = "image/jpeg"
        save_kwargs = {"format": "JPEG", "quality": 95, "optimize": True}

    buf = io.BytesIO()
    converted.save(buf, **save_kwargs)
    return PreparedInputImage(
        data=buf.getvalue(),
        mime=target_mime,
        original_mime=original_mime,
        original_format=target_format,
        transcoded=True,
    )