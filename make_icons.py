# -*- coding: utf-8 -*-
"""
درووستکردنی ئایکۆنی بەرنامەکە — shop.ico

python make_icons.py

ئایکۆنەکە چەند قەبارەیەکی تێدایە (16 ... 256) تا لە شریتی ئەرک و
لەسەر دێسکتۆپ ڕوون بێت.
"""
import struct, sys
from PyQt6.QtCore import Qt, QBuffer, QByteArray, QRectF, QPointF
from PyQt6.QtGui import (QImage, QPainter, QPainterPath, QColor, QBrush,
                         QLinearGradient)
from PyQt6.QtWidgets import QApplication

SIZES = [16, 24, 32, 48, 64, 128, 256]

BG_TOP, BG_BOT = "#2B3444", "#1B212B"     # پاشبنەمای تۆخ
GOLD_TOP, GOLD_BOT = "#F2CE74", "#D2A03C"  # زێڕ


def _canvas(px):
    img = QImage(px, px, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    g = QLinearGradient(0, 0, 0, px)
    g.setColorAt(0, QColor(BG_TOP)); g.setColorAt(1, QColor(BG_BOT))
    p.setPen(Qt.PenStyle.NoPen); p.setBrush(QBrush(g))
    p.drawRoundedRect(QRectF(0, 0, px, px), px * 0.22, px * 0.22)
    return img, p


def _gold(p, px):
    g = QLinearGradient(0, px * 0.2, 0, px * 0.85)
    g.setColorAt(0, QColor(GOLD_TOP)); g.setColorAt(1, QColor(GOLD_BOT))
    p.setBrush(QBrush(g)); p.setPen(Qt.PenStyle.NoPen)


def shop(px):
    """دڵۆپێکی ڕۆن — بۆ سیستەمی دووکان."""
    img, p = _canvas(px)
    _gold(p, px)
    u = px / 100.0

    drop = QPainterPath()
    drop.moveTo(50 * u, 20 * u)
    drop.cubicTo(50 * u, 20 * u, 76 * u, 50 * u, 76 * u, 62 * u)
    drop.arcTo(QRectF(24 * u, 36 * u, 52 * u, 52 * u), 0, -180)
    drop.cubicTo(24 * u, 50 * u, 50 * u, 20 * u, 50 * u, 20 * u)
    p.drawPath(drop.simplified())

    # ڕووناکی بچووک لەناو دڵۆپەکە
    p.setBrush(QColor(255, 255, 255, 70))
    p.drawEllipse(QRectF(38 * u, 55 * u, 12 * u, 16 * u))
    p.end()
    return img


def write_ico(path, draw):
    """ICO بە چەند قەبارەیەکەوە (هەر وێنەیەک وەک PNG هەڵدەگیرێت)."""
    blobs = []
    for s in SIZES:
        ba = QByteArray()               # QBuffer تەنها ئاماژەی بۆ دەکات —
        buf = QBuffer(ba)               # بۆیە دەبێت لێرە بمێنێتەوە
        buf.open(QBuffer.OpenModeFlag.WriteOnly)
        draw(s).save(buf, "PNG")
        buf.close()
        blobs.append(bytes(ba))

    out = struct.pack("<HHH", 0, 1, len(SIZES))
    offset = 6 + 16 * len(SIZES)
    for s, b in zip(SIZES, blobs):
        d = 0 if s >= 256 else s
        out += struct.pack("<BBBBHHII", d, d, 0, 0, 1, 32, len(b), offset)
        offset += len(b)
    out += b"".join(blobs)

    with open(path, "wb") as f:
        f.write(out)
    print(f"{path}  ({len(out):,} bytes, {len(SIZES)} sizes)")


def main():
    app = QApplication(sys.argv)    # QPainter پێویستی بە ئەپلیکەیشنە (ڕیفەرێنسی بپارێزە)
    write_ico("shop.ico", shop)
    shop(256).save("preview_shop.png")
    print("preview_shop.png")


if __name__ == "__main__":
    main()
