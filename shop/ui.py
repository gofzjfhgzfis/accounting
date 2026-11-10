# -*- coding: utf-8 -*-
"""پارچە هاوبەشەکانی ڕووکار: دوگمە، خشتە، کارت، چارت، چاپکردن."""
import os

from PyQt6.QtCore import Qt, QDate, QSizeF, QMarginsF, QRectF, QSize, QTimer, QUrl, QPoint
from PyQt6.QtGui import (QFont, QColor, QTextDocument, QPageSize, QPageLayout, QPainter,
                         QPainterPath, QPen, QDesktopServices, QCursor)
from PyQt6.QtPrintSupport import QPrinter, QPrintDialog
from PyQt6.QtWidgets import *

from .core import db, fmt, ltr, lrm, esc, APP_DIR
from .theme import T, pixmap, icon


# ---------------------------------------------------------------- پەیام
def msg(parent, text, title="ئاگاداری"):
    QMessageBox.information(parent, title, text)


def ask(parent, text):
    return QMessageBox.question(parent, "دڵنیابوونەوە", text,
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) == QMessageBox.StandardButton.Yes


# ---------------------------------------------------------------- دوگمە و خانە
def _btn_icon(b):
    kind = b.objectName()
    color = {"primary": T.ON_GOLD, "danger": T.RED, "ghost": T.MUTED}.get(kind, T.TEXT)
    if not b.isEnabled(): color = T.FAINT
    b.setIcon(icon(b.property("ico"), color, 17))
    b.setIconSize(QSize(17, 17))


def btn(text, fn=None, kind="", ico=None):
    b = QPushButton(text)
    if kind: b.setObjectName(kind)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    if ico:
        b.setProperty("ico", ico); _btn_icon(b)
    if fn: b.clicked.connect(fn)
    return b


def restyle_tree(root):
    """Re-colour everything a stylesheet cannot reach after a theme switch."""
    for b in root.findChildren(QPushButton):
        if b.property("ico"): _btn_icon(b)
    for w in root.findChildren(QWidget):
        if hasattr(w, "restyle"): w.restyle()


def chips(labels, on_change, checked=0):
    """A row of mutually exclusive filter chips. Returns (layout, group)."""
    h = QHBoxLayout(); h.setSpacing(6)
    g = QButtonGroup(h); g.setExclusive(True)
    for i, text in enumerate(labels):
        b = QPushButton(text); b.setObjectName("chip"); b.setCheckable(True)
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.setChecked(i == checked)
        g.addButton(b, i); h.addWidget(b)
    g.idClicked.connect(lambda _: on_change())
    return h, g


def search_box(placeholder, on_change, width=240):
    s = QLineEdit(); s.setPlaceholderText(placeholder)
    s.setClearButtonEnabled(True); s.setFixedWidth(width)
    s.textChanged.connect(lambda _: on_change())
    return s


def date_edit():
    d = QDateEdit(QDate.currentDate())
    d.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
    d.setCalendarPopup(True)
    d.setDisplayFormat("yyyy-MM-dd")
    return d


def dstr(d):
    return d.date().toString("yyyy-MM-dd")


def num(mx=1e12, dec=0, val=0):
    s = QDoubleSpinBox(); s.setRange(0, mx); s.setDecimals(dec)
    s.setGroupSeparatorShown(True)
    s.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
    # With the arrows hidden the stylesheet padding is ignored (and a forced
    # LTR direction blanks the field entirely), so pad the inner editor itself.
    s.lineEdit().setTextMargins(12, 0, 12, 0)
    s.setValue(val)
    return s


def combo(editable=False):
    c = QComboBox()
    # the built-in popup delegate ignores the stylesheet's row height,
    # so the list comes out cramped; a plain delegate honours it.
    c.setItemDelegate(QStyledItemDelegate(c))
    c.view().setSpacing(1)
    c.setMaxVisibleItems(12)
    if editable:
        c.setEditable(True)
        c.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        c.completer().setFilterMode(Qt.MatchFlag.MatchContains)
        c.completer().setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        c.completer().setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
    return c


def label(text="", name="", wrap=False):
    l = QLabel(text)
    if name: l.setObjectName(name)
    if wrap: l.setWordWrap(True)
    return l


def heading(text):
    return label(text, "secTitle")


def pill(text, tone=""):
    l = QLabel(text); l.setObjectName("pill"); l.setProperty("tone", tone)
    l.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
    return l


def card(title=None, margins=(18, 16, 18, 16), spacing=12):
    """A plain panel. Returns (frame, its vertical layout)."""
    f = QFrame(); f.setObjectName("card")
    v = QVBoxLayout(f); v.setContentsMargins(*margins); v.setSpacing(spacing)
    if title: v.addWidget(label(title, "panelTitle"))
    return f, v


def field(caption, widget):
    """A caption stacked above its input."""
    v = QVBoxLayout(); v.setSpacing(5); v.setContentsMargins(0, 0, 0, 0)
    v.addWidget(label(caption, "cardMeta")); v.addWidget(widget)
    return v


# ---------------------------------------------------------------- خشتە
def table(headers, stretch=None, flat=False):
    t = QTableWidget(); t.setColumnCount(len(headers))
    t.setHorizontalHeaderLabels(headers)
    t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    t.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    t.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    t.setShowGrid(False)
    t.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    t.horizontalHeader().setHighlightSections(False)
    t.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
    t.verticalHeader().setVisible(False)
    t.verticalHeader().setDefaultSectionSize(40)
    if flat: t.setObjectName("flat")
    h = t.horizontalHeader()
    if stretch is None:
        h.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    else:
        # every column hugs its content and one column absorbs the slack
        for i in range(len(headers)):
            h.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(stretch, QHeaderView.ResizeMode.Stretch)
    return t


def fill(t, rows, colors=None):
    """`colors` maps a column index to a function(row) -> colour or None."""
    t.setRowCount(len(rows))
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            it = QTableWidgetItem(ltr(val))
            it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if colors and j in colors:
                c = colors[j](row)
                if c: it.setForeground(QColor(c))
            t.setItem(i, j, it)


def sel_row(t):
    """Row that is highlighted, or -1."""
    rows = t.selectionModel().selectedRows()
    return rows[0].row() if rows else -1


def picked_id(t, col=0):
    r = sel_row(t)
    if r < 0: return None
    try: return int(t.item(r, col).text().replace("‎", "").lstrip("#"))
    except Exception: return None


# ---------------------------------------------------------------- دیالۆگ
def dialog(parent, title, w=440):
    d = QDialog(parent); d.setWindowTitle(title); d.setMinimumWidth(w)
    return d


def form(d):
    f = QFormLayout(d); f.setSpacing(12); f.setContentsMargins(22, 20, 22, 18)
    f.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    return f


def dlg_buttons(d, lay, ok_text="پاشەکەوتکردن"):
    bb = QDialogButtonBox()
    ok = bb.addButton(ok_text, QDialogButtonBox.ButtonRole.AcceptRole)
    ok.setObjectName("primary")
    cancel = bb.addButton("پاشگەزبوونەوە", QDialogButtonBox.ButtonRole.RejectRole)
    for b in (ok, cancel): b.setCursor(Qt.CursorShape.PointingHandCursor)
    bb.accepted.connect(d.accept); bb.rejected.connect(d.reject)
    if isinstance(lay, QFormLayout): lay.addRow(bb)
    else: lay.addWidget(bb)
    return ok


# ---------------------------------------------------------------- کارتی ئامار
class StatCard(QFrame):
    def __init__(self, caption, accent, ico):
        super().__init__()
        self.accent, self.ico = accent, ico   # palette key, resolved at paint time
        self.setObjectName("statCard")
        self.setMinimumHeight(92)
        h = QHBoxLayout(self); h.setContentsMargins(16, 14, 16, 14); h.setSpacing(13)
        self.tile = QLabel(); self.tile.setFixedSize(44, 44)
        self.tile.setAlignment(Qt.AlignmentFlag.AlignCenter)
        h.addWidget(self.tile, 0, Qt.AlignmentFlag.AlignTop)
        v = QVBoxLayout(); v.setSpacing(2); v.setContentsMargins(0, 0, 0, 0)
        self.val = label("0", "statVal"); self.sub = label("", "statSub")
        v.addWidget(label(caption, "statCap")); v.addWidget(self.val); v.addWidget(self.sub)
        v.addStretch()
        h.addLayout(v, 1)
        self.restyle()

    def set(self, text, sub=""):
        self.val.setText(str(text)); self.sub.setText(sub)

    def restyle(self):
        c = getattr(T, self.accent)
        self.tile.setStyleSheet(f"background:{T.soft(c, 0.16)};border-radius:12px;")
        self.tile.setPixmap(pixmap(self.ico, c, 21))


# ---------------------------------------------------------------- کارتی هەڵبژاردن
CARD_MIN_W = 250          # کەمترین پانی کارتێک


class PickCard(QFrame):
    """A selectable tile. Subclasses fill `self.body` with their own rows."""

    def __init__(self, rid):
        super().__init__()
        self.rid = rid
        self._pick = self._open = None
        self.setObjectName("pickCard")
        self.setProperty("picked", False)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumWidth(CARD_MIN_W)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.body = QVBoxLayout(self)
        self.body.setSpacing(6)
        self.body.setContentsMargins(16, 14, 16, 14)

    # ---- کورتکراوەکانی ناوەڕۆک ----
    def head(self, title, sub="", badge=None, tone="", avatar=False):
        """Title row: optional avatar, title + subtitle, optional status pill."""
        h = QHBoxLayout(); h.setSpacing(11)
        if avatar:
            a = QLabel((title or "؟").strip()[:1]); a.setObjectName("avatar")
            a.setFixedSize(38, 38); a.setAlignment(Qt.AlignmentFlag.AlignCenter)
            h.addWidget(a, 0, Qt.AlignmentFlag.AlignTop)
        v = QVBoxLayout(); v.setSpacing(1)
        v.addWidget(label(title, "cardTitle", wrap=True))
        if sub: v.addWidget(label(sub, "cardMeta"))
        h.addLayout(v, 1)
        if badge: h.addWidget(pill(badge, tone), 0, Qt.AlignmentFlag.AlignTop)
        self.body.addLayout(h)

    def meta(self, text):
        l = label(text, "cardMeta", wrap=True); self.body.addWidget(l); return l

    def sep(self):
        s = QFrame(); s.setObjectName("cardSep"); s.setFixedHeight(1)
        self.body.addSpacing(3); self.body.addWidget(s); self.body.addSpacing(3)

    def row(self, key, value, tone="txtStrong"):
        h = QHBoxLayout(); h.setSpacing(8)
        h.addWidget(label(key, "cardKey")); h.addStretch()
        h.addWidget(label(value, tone))
        self.body.addLayout(h)

    def set_picked(self, on):
        self.setProperty("picked", on)
        self.style().unpolish(self); self.style().polish(self)

    def mousePressEvent(self, e):
        if self._pick: self._pick(self.rid)

    def mouseDoubleClickEvent(self, e):
        if self._pick: self._pick(self.rid)
        if self._open: self._open()


class CardGrid(QWidget):
    """Scrollable grid of PickCards that reflows with the window width."""

    def __init__(self, empty_text="هیچ تۆمارێک نییە", min_w=CARD_MIN_W, on_open=None):
        super().__init__()
        self.cards = []
        self.selected = None
        self.min_w = min_w
        self.on_open = on_open
        self._cols = 0

        v = QVBoxLayout(self); v.setContentsMargins(0, 0, 0, 0); v.setSpacing(0)
        self.area = QScrollArea()
        self.area.setWidgetResizable(True)
        self.area.setFrameShape(QFrame.Shape.NoFrame)
        self.area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        holder = QWidget()
        self.grid = QGridLayout(holder)
        self.grid.setSpacing(12); self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.area.setWidget(holder)
        v.addWidget(self.area)

        self.empty = QLabel(empty_text); self.empty.setObjectName("hint")
        self.empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(self.empty); self.empty.hide()

    def set_cards(self, cards):
        for c in self.cards:
            c.setParent(None); c.deleteLater()
        self.cards = cards
        self._cols = 0
        for c in cards:
            c._pick, c._open = self.pick, self.on_open
        self.empty.setVisible(not cards)
        self.area.setVisible(bool(cards))
        if self.selected not in [c.rid for c in cards]:
            self.selected = None
        self._fit(); self._mark()

    def pick(self, rid):
        self.selected = rid
        self._mark()

    def _mark(self):
        for c in self.cards:
            c.set_picked(c.rid == self.selected)

    def _fit(self):
        w = self.area.viewport().width()
        cols = max(1, (w + self.grid.spacing()) // (self.min_w + self.grid.spacing()))
        if cols == self._cols:
            return
        self._cols = cols
        for c in self.cards:
            self.grid.removeWidget(c)
        for i, c in enumerate(self.cards):
            self.grid.addWidget(c, i // cols, i % cols)
        for c in range(self.grid.columnCount()):
            self.grid.setColumnStretch(c, 1 if c < cols else 0)
        # ڕیزەکان بە بەرزی ناوەڕۆکیان بمێننەوە — شوێنی زیادە بۆ خوارەوە
        used = -(-len(self.cards) // cols) if self.cards else 0
        for r in range(self.grid.rowCount()):
            self.grid.setRowStretch(r, 0)
        self.grid.setRowStretch(used, 1)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._fit()


# ---------------------------------------------------------------- لیستی بچووک
class ListCard(QFrame):
    """A titled panel listing `name … value` rows (top debtors, low stock)."""

    def __init__(self, title, empty_text):
        super().__init__()
        self.setObjectName("card")
        self.empty_text = empty_text
        v = QVBoxLayout(self); v.setContentsMargins(18, 16, 18, 14); v.setSpacing(4)
        v.addWidget(label(title, "panelTitle")); v.addSpacing(6)
        self.rows = QVBoxLayout(); self.rows.setSpacing(0)
        v.addLayout(self.rows); v.addStretch()

    def set_rows(self, rows):
        """rows: (name, value, objectName-for-value)"""
        while self.rows.count():
            it = self.rows.takeAt(0)
            if it.widget(): it.widget().deleteLater()
        if not rows:
            e = label(self.empty_text, "hint"); e.setContentsMargins(0, 10, 0, 10)
            self.rows.addWidget(e); return
        for i, (name, value, tone) in enumerate(rows):
            w = QWidget(); h = QHBoxLayout(w); h.setContentsMargins(0, 8, 0, 8); h.setSpacing(8)
            n = label(name); n.setMinimumWidth(40)
            h.addWidget(n, 1); h.addWidget(label(value, tone))
            self.rows.addWidget(w)
            if i < len(rows) - 1:
                s = QFrame(); s.setObjectName("cardSep"); s.setFixedHeight(1)
                self.rows.addWidget(s)


# ---------------------------------------------------------------- چارت
class BarChart(QWidget):
    """Single-series bar chart; colours are read from the theme at paint time."""

    def __init__(self):
        super().__init__()
        self.data = []            # (label, value, tooltip)
        self.hover = -1
        self.setMinimumHeight(170)
        self.setMouseTracking(True)
        self.setLayoutDirection(Qt.LayoutDirection.LeftToRight)

    def set_data(self, data):
        self.data = data; self.hover = -1; self.update()

    def _plot(self):
        return QRectF(8, 12, self.width() - 16, self.height() - 12 - 26)

    def _bars(self):
        r, n = self._plot(), len(self.data)
        if not n: return []
        top = max((d[1] for d in self.data), default=0) or 1
        slot = r.width() / n
        bw = max(3.0, min(34.0, slot * 0.62))
        out = []
        for i, d in enumerate(self.data):
            h = max(0.0, d[1]) / top * (r.height() - 6)
            x = r.left() + slot * i + (slot - bw) / 2
            out.append(QRectF(x, r.bottom() - h, bw, h))
        return out

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self._plot()
        p.setPen(QPen(QColor(T.LINE), 1))
        for k in range(4):
            y = r.bottom() - (r.height() - 6) * k / 3
            p.drawLine(int(r.left()), int(y), int(r.right()), int(y))
        if not any(d[1] for d in self.data):
            p.setPen(QColor(T.FAINT))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "هێشتا هیچ فرۆشتنێک نییە")
            return
        f = QFont(self.font()); f.setPixelSize(11); p.setFont(f)
        bars = self._bars()
        step = max(1, -(-len(bars) // 12))      # at most ~12 axis labels
        for i, b in enumerate(bars):
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(T.GOLD if i == self.hover else
                              (T.GOLD if T.name == "light" else T.soft(T.GOLD, 0.78))))
            if b.height() >= 1:
                path = QPainterPath()
                rad = min(4.0, b.width() / 2, b.height())
                path.addRoundedRect(b, rad, rad)
                p.drawPath(path)
            if i % step == 0 or i == len(bars) - 1 and step == 1:
                p.setPen(QColor(T.FAINT))
                p.drawText(QRectF(b.center().x() - 30, r.bottom() + 6, 60, 18),
                           Qt.AlignmentFlag.AlignCenter, self.data[i][0])

    def mouseMoveEvent(self, e):
        r, n = self._plot(), len(self.data)
        i = int((e.position().x() - r.left()) / (r.width() / n)) if n else -1
        i = i if 0 <= i < n else -1
        if i != self.hover:
            self.hover = i; self.update()
            if i >= 0: QToolTip.showText(QCursor.pos(), self.data[i][2], self)
            else: QToolTip.hideText()

    def leaveEvent(self, e):
        self.hover = -1; self.update()


# ---------------------------------------------------------------- تۆست
class Toast(QLabel):
    """A short confirmation that fades by itself instead of a blocking dialog."""

    def __init__(self, parent):
        super().__init__(parent)
        self.setObjectName("toast"); self.hide()
        self._timer = QTimer(self); self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)

    def show_text(self, text, ms=2600):
        self.setText(text); self.adjustSize()
        p = self.parentWidget()
        self.move((p.width() - self.width()) // 2, p.height() - self.height() - 30)
        self.raise_(); self.show(); self._timer.start(ms)


# ---------------------------------------------------------------- چاپ و PDF
def _render(html, printer):
    doc = QTextDocument()
    doc.setDefaultFont(QFont("Segoe UI", 10))
    doc.setHtml(html)
    # Without an explicit page size in the printer's own units the document
    # is laid out at its default width and prints microscopically small.
    doc.setPageSize(QSizeF(printer.pageRect(QPrinter.Unit.Point).size()))
    doc.print(printer)


def _printer():
    pr = QPrinter(QPrinter.PrinterMode.HighResolution)
    pr.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    pr.setPageMargins(QMarginsF(14, 14, 14, 14), QPageLayout.Unit.Millimeter)
    return pr


def save_pdf(parent, html, name):
    """Ask where to save, write the PDF and open it. Returns the path or None."""
    path, _ = QFileDialog.getSaveFileName(parent, "پاشەکەوتکردنی PDF",
                                          os.path.join(APP_DIR, name), "PDF (*.pdf)")
    if not path: return None
    pr = _printer()
    pr.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
    pr.setOutputFileName(path)
    _render(html, pr)
    QDesktopServices.openUrl(QUrl.fromLocalFile(path))
    return path


def print_html(parent, html):
    pr = _printer()
    if QPrintDialog(pr, parent).exec():
        _render(html, pr); return True
    return False


def doc_head(title, sub=""):
    """Shop letterhead shared by every printed document."""
    parts = [esc(p) for p in (db.get("address"), lrm(db.get("phone")) if db.get("phone") else "") if p]
    contact = (f'<p align="center" style="font-size:10pt;color:#8A9099;margin-top:6pt;'
               f'margin-bottom:0pt;">{" &nbsp;·&nbsp; ".join(parts)}</p>' if parts else "")
    return f"""
    <p align="center" style="font-size:22pt;font-weight:bold;color:#B8860B;
       margin-top:0pt;margin-bottom:0pt;">{esc(db.get('company'))}</p>
    {contact}
    <table width="100%" cellspacing="0" cellpadding="0" style="margin-top:11pt;margin-bottom:3pt;">
      <tr><td style="background-color:#B8860B;font-size:3pt;">&nbsp;</td></tr></table>
    <table width="100%" cellspacing="0" cellpadding="0" style="margin-bottom:16pt;">
      <tr><td style="background-color:#E2CF95;font-size:1pt;">&nbsp;</td></tr></table>
    <p style="font-size:14pt;font-weight:bold;color:#2B2F36;margin-bottom:3pt;">{title}</p>
    <p style="font-size:10.5pt;color:#5A626C;margin-top:3pt;">{sub}</p>"""


def doc_table(headers, rows, widths=None):
    """A bordered print table. `rows` hold already-formatted, already-escaped cells."""
    ths = "".join(f"<th{' width=' + chr(34) + widths[i] + chr(34) if widths else ''}>{h}</th>"
                  for i, h in enumerate(headers))
    trs = "".join("<tr>" + "".join(f"<td align='center'>{c}</td>" for c in r) + "</tr>"
                  for r in rows) or f"<tr><td colspan='{len(headers)}' align='center'>—</td></tr>"
    return (f'<table width="100%" border="1" cellspacing="0" cellpadding="7" '
            f'style="font-size:10.5pt;border-color:#E4E0D8;margin-top:8pt;">'
            f'<tr style="background-color:#FAF5E8;">{ths}</tr>{trs}</table>')
