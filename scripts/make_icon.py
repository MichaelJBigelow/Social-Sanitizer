"""Draw the app icon.

    python scripts/make_icon.py OUT.png    1024x1024 PNG
    python scripts/make_icon.py OUT.ico    Windows icon (256x256)

The committed src/social_sanitizer/assets/icon.png comes from this script; re-run it
there if you change the design.
"""

import sys
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QGuiApplication, QImage, QLinearGradient, QPainter, QPainterPath, QPen

SIZE = 1024


def draw(path: str) -> None:
    image = QImage(SIZE, SIZE, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    p = QPainter(image)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    # macOS-style rounded square with a sunset gradient.
    margin = 100
    tile = QRectF(margin, margin, SIZE - 2 * margin, SIZE - 2 * margin)
    gradient = QLinearGradient(tile.topLeft(), tile.bottomRight())
    gradient.setColorAt(0.0, QColor("#f9a03f"))
    gradient.setColorAt(0.5, QColor("#e1306c"))
    gradient.setColorAt(1.0, QColor("#7b3fe4"))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(gradient)
    p.drawRoundedRect(tile, 185, 185)

    # White shield.
    cx, top, w, h = SIZE / 2, 250, 420, 520
    shield = QPainterPath(QPointF(cx, top))
    shield.cubicTo(cx + w * 0.30, top + 60, cx + w * 0.50, top + 50, cx + w * 0.5, top + 50)
    shield.lineTo(cx + w * 0.5, top + h * 0.45)
    shield.cubicTo(cx + w * 0.5, top + h * 0.75, cx + w * 0.2, top + h * 0.92, cx, top + h)
    shield.cubicTo(cx - w * 0.2, top + h * 0.92, cx - w * 0.5, top + h * 0.75, cx - w * 0.5, top + h * 0.45)
    shield.lineTo(cx - w * 0.5, top + 50)
    shield.cubicTo(cx - w * 0.50, top + 50, cx - w * 0.30, top + 60, cx, top)
    p.setBrush(QColor("white"))
    p.drawPath(shield)

    # Check mark cut into the shield.
    pen = QPen(QColor("#e1306c"), 64, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    check = QPainterPath(QPointF(cx - 115, top + 270))
    check.lineTo(cx - 30, top + 355)
    check.lineTo(cx + 125, top + 195)
    p.drawPath(check)

    p.end()
    if Path(path).suffix.lower() == ".ico":
        # Windows' largest standard icon size; it scales this down for small views.
        image = image.scaled(256, 256, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
    if not image.save(path):
        raise SystemExit(f"couldn't write {path}")


if __name__ == "__main__":
    app = QGuiApplication(["make_icon", "-platform", "offscreen"])
    draw(sys.argv[1])
