"""Helpers de exportacion a Excel compartidos.

Consumido por los blueprints de Control de resultados:
  - app/api/control_resultados/historial_ict_pass_fail.py
  - app/api/control_resultados/historial_cambios_parametros_ict.py
  - app/api/control_resultados/historial_vision.py            (2026-05-27)
  - app/api/control_resultados/historial_vision_pass_fail.py  (2026-05-27)

Contenido:
  - _send_excel_download(output, filename)  -> wrapper send_file compatible
    con Flask viejos (attachment_filename) y nuevos (download_name).
  - _create_vision_pass_fail_excel_image(porcentaje_ok, porcentaje_ng)
    -> renderiza el grafico de barra PASS/FAIL como imagen Excel. Tiene
    dos backends:
      * PIL/Pillow si esta disponible (path preferente).
      * Renderer manual PNG (zlib + struct + dibujado vectorial pixel a
        pixel) como fallback. ~16 helpers internos para esto.

Migrado desde app/routes.py el 2026-05-27. routes.py reexporta ambos
para no romper consumidores legacy.

NOTA anti-circular: import directo de openpyxl/struct/zlib/PIL aqui.
No importamos app.api.shared (que importa de routes.py).
"""

import io
import os
import struct
import zlib
from pathlib import Path

from flask import send_file


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

VISION_PASS_FAIL_EXCEL_IMAGE_WIDTH = 430
VISION_PASS_FAIL_EXCEL_IMAGE_HEIGHT = 28


# ---------------------------------------------------------------------------
# Helpers de medicion + carga de fonts
# ---------------------------------------------------------------------------


def _measure_vision_pass_fail_excel_text(draw, text, font):
    if hasattr(draw, "textbbox"):
        left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
        return right - left, bottom - top

    if hasattr(draw, "textsize"):
        return draw.textsize(text, font=font)

    if hasattr(font, "getbbox"):
        left, top, right, bottom = font.getbbox(text)
        return right - left, bottom - top

    if hasattr(font, "getsize"):
        return font.getsize(text)

    return (max(len(text), 1) * 8, 12)


def _load_vision_pass_fail_excel_font(size=12, bold=False):
    from PIL import ImageFont

    windows_font_dir = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
    preferred_font_names = [
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
        "Arial Bold.ttf" if bold else "Arial.ttf",
        "Calibri Bold.ttf" if bold else "Calibri.ttf",
        "arialbd.ttf" if bold else "arial.ttf",
        "calibrib.ttf" if bold else "calibri.ttf",
    ]

    for font_name in preferred_font_names:
        try:
            return ImageFont.truetype(font_name, size=size)
        except OSError:
            continue

    font_candidates = [
        windows_font_dir / ("arialbd.ttf" if bold else "arial.ttf"),
        windows_font_dir / ("calibrib.ttf" if bold else "calibri.ttf"),
        windows_font_dir / ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"),
    ]

    for font_path in font_candidates:
        try:
            if font_path.is_file():
                return ImageFont.truetype(str(font_path), size=size)
        except OSError:
            continue

    return ImageFont.load_default()


# ---------------------------------------------------------------------------
# Path preferente: PIL/Pillow
# ---------------------------------------------------------------------------


def _build_vision_pass_fail_excel_bar_image(porcentaje_ok, porcentaje_ng):
    from io import BytesIO

    from PIL import Image, ImageDraw

    pass_rate = max(0.0, min(100.0, float(porcentaje_ok or 0)))
    fail_rate = max(0.0, min(100.0, float(porcentaje_ng or 0)))

    canvas_width = 430
    canvas_height = 28
    bar_width = 350
    bar_height = 20
    label_gap = 8
    label_width = canvas_width - bar_width - label_gap
    radius = bar_height // 2

    ok_width = int(round((pass_rate / 100.0) * bar_width))
    ok_width = max(0, min(bar_width, ok_width))
    ng_width = max(0, bar_width - ok_width)

    image = Image.new("RGBA", (canvas_width, canvas_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    bar_x = 0
    bar_y = (canvas_height - bar_height) // 2

    # Base dark bar
    draw.rounded_rectangle(
        (bar_x, bar_y, bar_x + bar_width, bar_y + bar_height),
        radius=radius,
        fill="#1A2740",
    )

    # Draw segments inside a rounded mask for clean edges
    segments = Image.new("RGBA", (bar_width, bar_height), (0, 0, 0, 0))
    segments_draw = ImageDraw.Draw(segments)
    if ok_width > 0:
        segments_draw.rectangle((0, 0, ok_width, bar_height), fill="#4CAF63")
    if ng_width > 0:
        segments_draw.rectangle(
            (bar_width - ng_width, 0, bar_width, bar_height), fill="#E45454"
        )

    mask = Image.new("L", (bar_width, bar_height), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle((0, 0, bar_width, bar_height), radius=radius, fill=255)
    image.paste(segments, (bar_x, bar_y), mask)

    pass_label = f"{pass_rate:.2f}%"
    fail_label = f"{fail_rate:.2f}%"

    pass_font = _load_vision_pass_fail_excel_font(size=12, bold=True)
    fail_font = _load_vision_pass_fail_excel_font(size=12, bold=True)

    pass_text_width, pass_text_height = _measure_vision_pass_fail_excel_text(
        draw, pass_label, pass_font
    )
    pass_center_x = bar_x + max(ok_width / 2, min(bar_width / 2, 70))
    pass_text_x = int(
        max(
            bar_x + 10,
            min(pass_center_x - pass_text_width / 2, bar_width - pass_text_width - 10),
        )
    )
    pass_text_y = int(bar_y + (bar_height - pass_text_height) / 2 - 1)
    draw.text(
        (pass_text_x, pass_text_y),
        pass_label,
        font=pass_font,
        fill="#FFFFFF",
    )

    _, fail_text_height = _measure_vision_pass_fail_excel_text(
        draw, fail_label, fail_font
    )
    fail_text_x = bar_width + label_gap
    fail_text_y = int(bar_y + (bar_height - fail_text_height) / 2 - 1)
    draw.text(
        (fail_text_x, fail_text_y),
        fail_label,
        font=fail_font,
        fill="#1F1F1F",
    )

    output = BytesIO()
    image.save(output, format="PNG")
    output.seek(0)
    return output


# ---------------------------------------------------------------------------
# Fallback: renderer PNG manual (vector pixel-a-pixel) si Pillow falla
# ---------------------------------------------------------------------------


def _vision_pass_fail_text_width(text, char_width=10, spacing=3):
    if not text:
        return 0

    width = 0
    for idx, char in enumerate(text):
        width += _get_vision_pass_fail_char_width(char, char_width)
        if idx < len(text) - 1:
            width += spacing
    return width


def _set_vision_pass_fail_pixel(pixels, width, x, y, color):
    if x < 0 or y < 0:
        return

    idx = ((y * width) + x) * 4
    if idx < 0 or idx + 3 >= len(pixels):
        return

    pixels[idx] = color[0]
    pixels[idx + 1] = color[1]
    pixels[idx + 2] = color[2]
    pixels[idx + 3] = color[3]


def _fill_vision_pass_fail_rounded_rect(
    pixels, canvas_width, x, y, width, height, radius, color
):
    radius = max(0, min(radius, width // 2, height // 2))
    radius_sq = radius * radius

    for local_y in range(height):
        for local_x in range(width):
            if radius == 0:
                inside = True
            elif radius <= local_x < width - radius or radius <= local_y < height - radius:
                inside = True
            else:
                corner_x = radius if local_x < radius else width - radius - 1
                corner_y = radius if local_y < radius else height - radius - 1
                delta_x = local_x - corner_x
                delta_y = local_y - corner_y
                inside = (delta_x * delta_x) + (delta_y * delta_y) <= radius_sq

            if inside:
                _set_vision_pass_fail_pixel(
                    pixels, canvas_width, x + local_x, y + local_y, color
                )


def _draw_vision_pass_fail_disc(pixels, canvas_width, center_x, center_y, radius, color):
    radius_sq = radius * radius
    for local_y in range(-radius, radius + 1):
        for local_x in range(-radius, radius + 1):
            if (local_x * local_x) + (local_y * local_y) <= radius_sq:
                _set_vision_pass_fail_pixel(
                    pixels,
                    canvas_width,
                    center_x + local_x,
                    center_y + local_y,
                    color,
                )


def _draw_vision_pass_fail_line(
    pixels, canvas_width, x1, y1, x2, y2, thickness, color
):
    dx = x2 - x1
    dy = y2 - y1
    steps = max(abs(dx), abs(dy), 1)
    radius = max(1, thickness // 2)

    for step in range(steps + 1):
        point_x = int(round(x1 + (dx * step / steps)))
        point_y = int(round(y1 + (dy * step / steps)))
        _draw_vision_pass_fail_disc(
            pixels, canvas_width, point_x, point_y, radius, color
        )


def _draw_vision_pass_fail_segment(
    pixels,
    canvas_width,
    origin_x,
    origin_y,
    segment_name,
    color,
    char_width=10,
    char_height=14,
    thickness=2,
):
    mid_y = origin_y + (char_height // 2)
    bottom_y = origin_y + char_height - thickness
    right_x = origin_x + char_width - thickness
    horizontal_width = char_width - (thickness * 2)
    vertical_height = (char_height // 2) - thickness - 1
    radius = max(1, thickness // 2)

    if segment_name == "top":
        _fill_vision_pass_fail_rounded_rect(
            pixels, canvas_width, origin_x + thickness, origin_y,
            horizontal_width, thickness, radius, color,
        )
    elif segment_name == "middle":
        _fill_vision_pass_fail_rounded_rect(
            pixels, canvas_width, origin_x + thickness, mid_y - (thickness // 2),
            horizontal_width, thickness, radius, color,
        )
    elif segment_name == "bottom":
        _fill_vision_pass_fail_rounded_rect(
            pixels, canvas_width, origin_x + thickness, bottom_y,
            horizontal_width, thickness, radius, color,
        )
    elif segment_name == "upper_left":
        _fill_vision_pass_fail_rounded_rect(
            pixels, canvas_width, origin_x, origin_y + thickness,
            thickness, vertical_height, radius, color,
        )
    elif segment_name == "upper_right":
        _fill_vision_pass_fail_rounded_rect(
            pixels, canvas_width, right_x, origin_y + thickness,
            thickness, vertical_height, radius, color,
        )
    elif segment_name == "lower_left":
        _fill_vision_pass_fail_rounded_rect(
            pixels, canvas_width, origin_x, mid_y + 1,
            thickness, vertical_height, radius, color,
        )
    elif segment_name == "lower_right":
        _fill_vision_pass_fail_rounded_rect(
            pixels, canvas_width, right_x, mid_y + 1,
            thickness, vertical_height, radius, color,
        )


def _get_vision_pass_fail_segments(char):
    segment_map = {
        "0": ("top", "upper_left", "upper_right", "lower_left", "lower_right", "bottom"),
        "1": ("upper_right", "lower_right"),
        "2": ("top", "upper_right", "middle", "lower_left", "bottom"),
        "3": ("top", "upper_right", "middle", "lower_right", "bottom"),
        "4": ("upper_left", "upper_right", "middle", "lower_right"),
        "5": ("top", "upper_left", "middle", "lower_right", "bottom"),
        "6": ("top", "upper_left", "middle", "lower_left", "lower_right", "bottom"),
        "7": ("top", "upper_right", "lower_right"),
        "8": ("top", "upper_left", "upper_right", "middle", "lower_left", "lower_right", "bottom"),
        "9": ("top", "upper_left", "upper_right", "middle", "lower_right", "bottom"),
    }
    return segment_map.get(char, ())


def _get_vision_pass_fail_char_width(char, default_width=10):
    if char == "1":
        return default_width - 2
    if char == ".":
        return 4
    if char == "%":
        return default_width + 2
    if char == " ":
        return max(3, default_width // 2)
    return default_width


def _draw_vision_pass_fail_vector_char(
    pixels, canvas_width, x, y, char, color,
    char_width=10, char_height=14, thickness=2,
):
    actual_width = _get_vision_pass_fail_char_width(char, char_width)

    if char.isdigit():
        for segment_name in _get_vision_pass_fail_segments(char):
            _draw_vision_pass_fail_segment(
                pixels, canvas_width, x, y, segment_name, color,
                char_width=actual_width, char_height=char_height, thickness=thickness,
            )
        return actual_width

    if char == ".":
        radius = max(1, thickness)
        _draw_vision_pass_fail_disc(
            pixels, canvas_width, x + radius, y + char_height - radius - 1,
            radius, color,
        )
        return actual_width

    if char == "%":
        disc_radius = max(1, thickness)
        _draw_vision_pass_fail_disc(pixels, canvas_width, x + 2, y + 3, disc_radius, color)
        _draw_vision_pass_fail_disc(
            pixels, canvas_width, x + actual_width - 3, y + char_height - 3,
            disc_radius, color,
        )
        _draw_vision_pass_fail_line(
            pixels, canvas_width, x + actual_width - 3, y + 1,
            x + 2, y + char_height - 2, thickness, color,
        )
        return actual_width

    return actual_width


def _draw_vision_pass_fail_vector_text(
    pixels, canvas_width, x, y, text, color,
    char_width=10, char_height=14, thickness=2, spacing=3,
):
    cursor_x = x
    for idx, char in enumerate(text):
        cursor_x += _draw_vision_pass_fail_vector_char(
            pixels, canvas_width, cursor_x, y, char, color,
            char_width=char_width, char_height=char_height, thickness=thickness,
        )
        if idx < len(text) - 1:
            cursor_x += spacing


def _build_vision_pass_fail_excel_bar_png_bytes(porcentaje_ok, porcentaje_ng):
    pass_rate = max(0.0, min(100.0, float(porcentaje_ok or 0)))
    fail_rate = max(0.0, min(100.0, float(porcentaje_ng or 0)))

    canvas_width = VISION_PASS_FAIL_EXCEL_IMAGE_WIDTH
    canvas_height = VISION_PASS_FAIL_EXCEL_IMAGE_HEIGHT
    bar_width = 350
    bar_height = 20
    label_gap = 8
    radius = bar_height // 2
    bar_x = 0
    bar_y = (canvas_height - bar_height) // 2

    ok_width = int(round((pass_rate / 100.0) * bar_width))
    ok_width = max(0, min(bar_width, ok_width))
    ng_width = max(0, bar_width - ok_width)

    pixels = bytearray(canvas_width * canvas_height * 4)

    _fill_vision_pass_fail_rounded_rect(
        pixels, canvas_width, bar_x, bar_y, bar_width, bar_height, radius, (26, 39, 64, 255)
    )

    for local_y in range(bar_height):
        for local_x in range(bar_width):
            if radius <= local_x < bar_width - radius or radius <= local_y < bar_height - radius:
                inside = True
            else:
                corner_x = radius if local_x < radius else bar_width - radius - 1
                corner_y = radius if local_y < radius else bar_height - radius - 1
                delta_x = local_x - corner_x
                delta_y = local_y - corner_y
                inside = (delta_x * delta_x) + (delta_y * delta_y) <= radius * radius

            if not inside:
                continue

            if ok_width > 0 and local_x < ok_width:
                color = (76, 175, 99, 255)
            elif ng_width > 0 and local_x >= bar_width - ng_width:
                color = (228, 84, 84, 255)
            else:
                color = (26, 39, 64, 255)

            _set_vision_pass_fail_pixel(
                pixels, canvas_width, bar_x + local_x, bar_y + local_y, color
            )

    pass_label = f"{pass_rate:.2f}%"
    fail_label = f"{fail_rate:.2f}%"

    char_width = 10
    char_height = 14
    thickness = 2
    spacing = 2
    pass_text_width = _vision_pass_fail_text_width(
        pass_label, char_width=char_width, spacing=spacing
    )
    pass_center_x = bar_x + max(ok_width / 2, min(bar_width / 2, 70))
    pass_text_x = int(
        max(
            bar_x + 10,
            min(pass_center_x - pass_text_width / 2, bar_width - pass_text_width - 10),
        )
    )
    pass_text_y = bar_y + max(0, (bar_height - char_height) // 2)
    _draw_vision_pass_fail_vector_text(
        pixels, canvas_width, pass_text_x, pass_text_y,
        pass_label, (255, 255, 255, 255),
        char_width=char_width, char_height=char_height,
        thickness=thickness, spacing=spacing,
    )

    fail_text_x = bar_width + label_gap
    fail_text_y = bar_y + max(0, (bar_height - char_height) // 2)
    _draw_vision_pass_fail_vector_text(
        pixels, canvas_width, fail_text_x, fail_text_y,
        fail_label, (31, 31, 31, 255),
        char_width=char_width, char_height=char_height,
        thickness=thickness, spacing=spacing,
    )

    raw_rows = bytearray()
    stride = canvas_width * 4
    for row_idx in range(canvas_height):
        raw_rows.append(0)
        start = row_idx * stride
        raw_rows.extend(pixels[start : start + stride])

    compressed = zlib.compress(bytes(raw_rows), 9)

    def png_chunk(chunk_type, data):
        return (
            struct.pack(">I", len(data))
            + chunk_type
            + data
            + struct.pack(">I", zlib.crc32(chunk_type + data) & 0xFFFFFFFF)
        )

    png_bytes = bytearray()
    png_bytes.extend(b"\x89PNG\r\n\x1a\n")
    png_bytes.extend(
        png_chunk(
            b"IHDR",
            struct.pack(">IIBBBBB", canvas_width, canvas_height, 8, 6, 0, 0, 0),
        )
    )
    png_bytes.extend(png_chunk(b"IDAT", compressed))
    png_bytes.extend(png_chunk(b"IEND", b""))
    return bytes(png_bytes)


# ---------------------------------------------------------------------------
# API publica
# ---------------------------------------------------------------------------


def _create_vision_pass_fail_excel_image(porcentaje_ok, porcentaje_ng):
    from openpyxl.drawing.image import Image as XLImage

    try:
        image_buffer = _build_vision_pass_fail_excel_bar_image(
            porcentaje_ok, porcentaje_ng
        )
        excel_image = XLImage(image_buffer)
    except Exception:
        png_bytes = _build_vision_pass_fail_excel_bar_png_bytes(
            porcentaje_ok, porcentaje_ng
        )

        class RawPngExcelImage(XLImage):
            def __init__(self, raw_bytes, width, height):
                self.ref = io.BytesIO(raw_bytes)
                self._raw_bytes = raw_bytes
                self.width = width
                self.height = height
                self.format = "png"

            def _data(self):
                return self._raw_bytes

        excel_image = RawPngExcelImage(
            png_bytes,
            VISION_PASS_FAIL_EXCEL_IMAGE_WIDTH,
            VISION_PASS_FAIL_EXCEL_IMAGE_HEIGHT,
        )

    excel_image.width = VISION_PASS_FAIL_EXCEL_IMAGE_WIDTH
    excel_image.height = VISION_PASS_FAIL_EXCEL_IMAGE_HEIGHT
    return excel_image


def _send_excel_download(output, filename):
    send_kwargs = {
        "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "as_attachment": True,
    }

    try:
        return send_file(output, download_name=filename, **send_kwargs)
    except TypeError:
        output.seek(0)
        return send_file(output, attachment_filename=filename, **send_kwargs)
