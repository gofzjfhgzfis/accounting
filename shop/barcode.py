# -*- coding: utf-8 -*-
"""بارکۆد: کۆدکردنی Code 128، درووستکردنی ژمارەی نوێ و نەخشاندنی لەیبڵ.

Code 128 هەڵبژێردراوە چونکە هەموو سکانەرێکی USB دەیخوێنێتەوە و هەم
ژمارە و هەم پیتی ئینگلیزی وەردەگرێت.
"""
import random

from PyQt6.QtCore import Qt, QRectF, QSizeF, QMarginsF
from PyQt6.QtGui import QColor, QFont, QFontMetrics, QPageSize, QPageLayout
from PyQt6.QtPrintSupport import QPrinter

# پانی هێڵ و بۆشایی هەر نیشانەیەک بە «مۆدیول»، بەپێی ستانداردی Code 128.
# هەر نیشانەیەک ٣ هێڵ و ٣ بۆشاییە (کۆی ١١)؛ نیشانەی کۆتایی ٤ هێڵە (کۆی ١٣).
PATTERNS = (
    "212222", "222122", "222221", "121223", "121322", "131222", "122213", "122312",
    "132212", "221213", "221312", "231212", "112232", "122132", "122231", "113222",
    "123122", "123221", "223211", "221132", "221231", "213212", "223112", "312131",
    "311222", "321122", "321221", "312212", "322112", "322211", "212123", "212321",
    "232121", "111323", "131123", "131321", "112313", "132113", "132311", "211313",
    "231113", "231311", "112133", "112331", "132131", "113123", "113321", "133121",
    "313121", "211331", "231131", "213113", "213311", "213131", "311123", "311321",
    "331121", "312113", "312311", "332111", "314111", "221411", "431111", "111224",
    "111422", "121124", "121421", "141122", "141221", "112214", "112412", "122114",
    "122411", "142112", "142211", "241211", "221114", "413111", "241112", "134111",
    "111242", "121142", "121241", "114212", "124112", "124211", "411212", "421112",
    "421211", "212141", "214121", "412121", "111143", "111341", "131141", "114113",
    "114311", "411113", "411311", "113141", "114131", "311141", "411131", "211412",
    "211214", "211232", "2331112",
)
START_B, START_C, STOP = 104, 105, 106
QUIET = 10                       # بۆشایی پێویست لە هەردوو لاوە، بە مۆدیول

_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")


def norm(code):
    """Clean a typed or scanned code.

    A scanner "types" like a keyboard, so with the Kurdish layout active the
    digits can arrive as ١٢٣ — they are turned back into 123 here.
    """
    return "".join(str(code or "").translate(_DIGITS).split())


def valid(code):
    return bool(code) and all(32 < ord(ch) < 127 for ch in code)


def encode(code):
    """Code 128 symbol values for `code`: start, data, checksum, stop."""
    if not valid(code):
        raise ValueError("بارکۆد تەنها ژمارە و پیتی ئینگلیزی وەردەگرێت")
    if code.isdigit() and len(code) % 2 == 0:
        # جۆری C: هەر دوو ژمارە یەک نیشانەیە، بۆیە بارکۆدەکە کورتتر دەبێت
        vals = [START_C] + [int(code[i:i + 2]) for i in range(0, len(code), 2)]
    else:
        vals = [START_B] + [ord(ch) - 32 for ch in code]
    check = (vals[0] + sum(i * v for i, v in enumerate(vals[1:], 1))) % 103
    return vals + [check, STOP]


def widths(code):
    """Alternating bar/space widths in modules, starting with a bar."""
    return [int(w) for v in encode(code) for w in PATTERNS[v]]


def generate(exists):
    """A new 12-digit in-shop code that `exists(code)` says is unused.

    It starts with 2, the range kept for codes a shop prints itself, so it
    cannot clash with a manufacturer's barcode.
    """
    while True:
        code = "2" + "".join(random.choice("0123456789") for _ in range(11))
        if not exists(code):
            return code


# ---------------------------------------------------------------- نەخشاندن
def draw_bars(p, rect, code):
    """Paint the bars of `code` filling `rect` (quiet zones included)."""
    ws = widths(code)
    total = sum(ws) + 2 * QUIET
    unit = rect.width() / total
    x = rect.left() + QUIET * unit
    p.save()
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#000000"))
    for i, w in enumerate(ws):
        if i % 2 == 0:
            p.drawRect(QRectF(x, rect.top(), w * unit, rect.height()))
        x += w * unit
    p.restore()


def _fit(p, text, font, width):
    return QFontMetrics(font, p.device()).elidedText(text, Qt.TextElideMode.ElideRight, int(width))


def draw_label(p, rect, name, code, price=""):
    """One sticker: item name, bars, the code in digits and (optionally) price."""
    h, w = rect.height(), rect.width()
    pad = min(w, h) * 0.06
    r = rect.adjusted(pad, pad * 0.8, -pad, -pad * 0.8)
    rows = [0.22, 0.46, 0.14, 0.18] if price else [0.26, 0.56, 0.18, 0]
    y = r.top()
    boxes = []
    for frac in rows:
        boxes.append(QRectF(r.left(), y, r.width(), r.height() * frac))
        y += r.height() * frac

    p.save()
    p.setPen(QColor("#000000"))
    f = QFont("Segoe UI"); f.setBold(True); f.setPixelSize(max(6, int(boxes[0].height() * 0.62)))
    p.setFont(f)
    p.drawText(boxes[0], Qt.AlignmentFlag.AlignCenter, _fit(p, name, f, boxes[0].width()))

    # بارکۆدەکە نابێت لە ٨٠٪ی پانی لەیبڵەکە زیاتر بێت، تا سکانەر بە ئاسانی بیخوێنێتەوە
    bars = boxes[1].adjusted(0, boxes[1].height() * 0.06, 0, 0)
    bw = min(bars.width(), (sum(widths(code)) + 2 * QUIET) * bars.width() / 95)
    bars = QRectF(bars.center().x() - bw / 2, bars.top(), bw, bars.height())
    draw_bars(p, bars, code)

    f = QFont("Consolas"); f.setPixelSize(max(5, int(boxes[2].height() * 0.78)))
    p.setFont(f)
    p.drawText(boxes[2], Qt.AlignmentFlag.AlignCenter, code)
    if price:
        f = QFont("Segoe UI"); f.setBold(True); f.setPixelSize(max(6, int(boxes[3].height() * 0.72)))
        p.setFont(f)
        p.drawText(boxes[3], Qt.AlignmentFlag.AlignCenter, price)
    p.restore()


# ---------------------------------------------------------------- پەڕەکان
LAYOUTS = [
    # (ناو، پانی لەیبڵ، بەرزی، ستوون، ڕیز) — بە ملیمەتر
    ("پەڕەی A4 — ٢٤ لەیبڵ (٣ × ٨)", 70.0, 37.125, 3, 8),
    ("پەڕەی A4 — ٤٠ لەیبڵ (٤ × ١٠)", 52.5, 29.7, 4, 10),
    ("پرینتەری لەیبڵ — ٥٠ × ٣٠ mm", 50.0, 30.0, 1, 1),
    ("پرینتەری لەیبڵ — ٤٠ × ٢٥ mm", 40.0, 25.0, 1, 1),
]


def setup_printer(pr, layout):
    _, lw, lh, cols, rows = LAYOUTS[layout]
    if cols * rows == 1:
        pr.setPageSize(QPageSize(QSizeF(lw, lh), QPageSize.Unit.Millimeter, "label"))
    else:
        pr.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    pr.setPageOrientation(QPageLayout.Orientation.Portrait)
    pr.setFullPage(True)
    pr.setPageMargins(QMarginsF(0, 0, 0, 0), QPageLayout.Unit.Millimeter)


def paint_labels(p, pr, layout, count, name, code, price=""):
    """Lay `count` copies of one label out on the printer's pages."""
    _, lw, lh, cols, rows = LAYOUTS[layout]
    dpmm = pr.resolution() / 25.4
    per_page = cols * rows
    for n in range(count):
        if n and n % per_page == 0:
            pr.newPage()
        i = n % per_page
        c, r = i % cols, i // cols
        # پەڕەکە لە ڕاستەوە پڕ دەکرێتەوە، وەک خوێندنەوەی کوردی
        x = (cols - 1 - c) * lw * dpmm
        draw_label(p, QRectF(x, r * lh * dpmm, lw * dpmm, lh * dpmm), name, code, price)
