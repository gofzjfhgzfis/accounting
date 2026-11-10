# -*- coding: utf-8 -*-
"""ڕەنگەکان، ئایکۆنەکان و شێوازی گشتی بەرنامەکە."""
import os, tempfile

from PyQt6.QtCore import Qt, QByteArray, QRectF, QSize
from PyQt6.QtGui import QColor, QPalette, QPixmap, QPainter, QIcon
from PyQt6.QtSvg import QSvgRenderer

PALETTES = {
    "dark": dict(
        BG="#0E1117", SIDE="#0A0D12", CARD="#161B24", CARD_HI="#1B212C", FIELD="#0F131A",
        BORDER="#252C38", BORDER_HI="#3B4556", LINE="#1E2530",
        TEXT="#DFE3EA", TITLE="#F6F8FB", MUTED="#8D97A8", FAINT="#667082",
        GOLD="#E2B84F", GOLD_HI="#EFCB70", GOLD_HOVER="#EDC864", GOLD_PRESS="#C99F3A",
        ON_GOLD="#1A1503",
        BTN="#1D2430", BTN_HOVER="#273040", BTN_PRESS="#181E28",
        SCROLL="#2C3543", SCROLL_HI="#3F4A5C",
        GREEN="#47C79B", RED="#F0797F", BLUE="#6CA6FF", VIOLET="#A890F2", ORANGE="#F3A566",
    ),
    "light": dict(
        BG="#F2F4F8", SIDE="#FFFFFF", CARD="#FFFFFF", CARD_HI="#FAFBFD", FIELD="#FFFFFF",
        BORDER="#E1E6EE", BORDER_HI="#C3CCD9", LINE="#ECEFF4",
        TEXT="#2B3441", TITLE="#111823", MUTED="#687385", FAINT="#98A2B1",
        GOLD="#DDB246", GOLD_HI="#94700F", GOLD_HOVER="#E6BE58", GOLD_PRESS="#C99D33",
        ON_GOLD="#1F1903",
        BTN="#FFFFFF", BTN_HOVER="#F4F6FA", BTN_PRESS="#E9EDF3",
        SCROLL="#CBD2DD", SCROLL_HI="#AFB9C7",
        GREEN="#1C9468", RED="#D2414C", BLUE="#2C6FCB", VIOLET="#6C4EC4", ORANGE="#C76B27",
    ),
}


class _Theme:
    """The active palette: `T.GOLD`, `T.CARD`… plus `T.name`."""
    name = "dark"

    def soft(self, color, t=0.15):
        """A quiet tint of `color` that sits on a card (for pills, icon tiles)."""
        return mix(self.CARD, color, t)


T = _Theme()


def mix(a, b, t):
    """Blend hex colour `a` towards `b` by `t` (0–1)."""
    ca, cb = QColor(a), QColor(b)
    return "#%02X%02X%02X" % (round(ca.red() + (cb.red() - ca.red()) * t),
                              round(ca.green() + (cb.green() - ca.green()) * t),
                              round(ca.blue() + (cb.blue() - ca.blue()) * t))


def apply_palette(name):
    T.name = name if name in PALETTES else "dark"
    T.__dict__.update(PALETTES[T.name])


apply_palette("dark")

# ---------------------------------------------------------------- ئایکۆنەکان
# هێڵکاریی سادەی ٢٤×٢٤؛ ڕەنگەکەیان لە کاتی نەخشاندندا دیاری دەکرێت.
ICONS = {
    "dash": '<rect x="3" y="3" width="7.5" height="9" rx="1.5"/><rect x="13.5" y="3" width="7.5" height="5" rx="1.5"/>'
            '<rect x="13.5" y="12" width="7.5" height="9" rx="1.5"/><rect x="3" y="16" width="7.5" height="5" rx="1.5"/>',
    "sale": '<path d="M6 2.5h12a1 1 0 0 1 1 1V21l-2.5-1.6L14 21l-2-1.6L10 21l-2.5-1.6L5 21V3.5a1 1 0 0 1 1-1z"/>'
            '<path d="M9 8h6M9 12h6M9 16h3"/>',
    "cust": '<circle cx="9" cy="8" r="3.6"/><path d="M2.5 20.5v-1a5.5 5.5 0 0 1 5.5-5.5h2a5.5 5.5 0 0 1 5.5 5.5v1"/>'
            '<path d="M16 4.6a3.6 3.6 0 0 1 0 6.8M21.5 20.5v-1a5.5 5.5 0 0 0-3.6-5.1"/>',
    "inv":  '<path d="M21 8l-9-5-9 5v8l9 5 9-5z"/><path d="M3 8l9 5 9-5M12 13v8"/>',
    "sup":  '<path d="M1.5 5.5h12.5v11H1.5z"/><path d="M14 9.5h4l4 4v3h-8z"/>'
            '<circle cx="6" cy="18" r="2"/><circle cx="18" cy="18" r="2"/>',
    "exp":  '<path d="M3 7.5a2.5 2.5 0 0 1 2.5-2.5H18v4"/>'
            '<path d="M3 7.5V17a2 2 0 0 0 2 2h15a1 1 0 0 0 1-1v-8a1 1 0 0 0-1-1H5.5A2.500 2.500 0 0 1 3 7.5z"/>'
            '<path d="M16.500 14h.5"/>',
    "rep":  '<path d="M3 21h18"/><path d="M6 21v-8M11 21V5M16 21v-11M21 21v-5"/>',
    "st":   '<path d="M4 6h9M19 6h1M4 12h2M12 12h8M4 18h7M17 18h3"/>'
            '<circle cx="16" cy="6" r="2.200"/><circle cx="9" cy="12" r="2.200"/><circle cx="14" cy="18" r="2.200"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "cash": '<rect x="2" y="6" width="20" height="12" rx="2"/><circle cx="12" cy="12" r="2.800"/><path d="M6 10v4M18 10v4"/>',
    "trend": '<path d="M3 17l6-6 4 4 8-8"/><path d="M15 7h6v6"/>',
    "alert": '<path d="M12 3.500l9.500 16.500h-19z"/><path d="M12 10v4.500M12 17.500v.2"/>',
    "sun":  '<circle cx="12" cy="12" r="4"/><path d="M12 2.500v2M12 19.500v2M2.500 12h2M19.500 12h2M5.300 5.300l1.400 1.400M17.300 17.300l1.400 1.400M5.300 18.700l1.400-1.400M17.300 6.700l1.400-1.400"/>',
    "moon": '<path d="M20.500 14.500A8.500 8.500 0 0 1 9.500 3.500a8.500 8.500 0 1 0 11 11z"/>',
    "lock": '<rect x="4.500" y="10.500" width="15" height="10" rx="2"/><path d="M8 10.500V7.500a4 4 0 0 1 8 0v3"/>',
    "print": '<path d="M7 8V3.500h10V8"/><rect x="3" y="8" width="18" height="9" rx="2"/><path d="M7 14h10v6.500H7z"/>',
    "pdf":  '<path d="M14 2.500H7a2 2 0 0 0-2 2v15a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7.500z"/><path d="M14 2.500v5h5M12 11.500v6M9.500 15l2.500 2.500 2.500-2.500"/>',
    "chev": '<path d="M6 9.500l6 6 6-6"/>',
    "cal":  '<rect x="3.500" y="5" width="17" height="15.500" rx="2"/><path d="M3.500 10h17M8 3v4M16 3v4"/>',
}


def pixmap(name, color, size=18, width=1.8):
    """Render one of the line icons in `color` at `size` logical pixels."""
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
           f'stroke="{color}" stroke-width="{width}" stroke-linecap="round" '
           f'stroke-linejoin="round">{ICONS[name]}</svg>')
    scale = 3                      # crisp on any display scaling
    pm = QPixmap(size * scale, size * scale)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    QSvgRenderer(QByteArray(svg.encode("utf-8"))).render(p, QRectF(0, 0, size * scale, size * scale))
    p.end()
    pm.setDevicePixelRatio(scale)
    return pm


def icon(name, color, size=18):
    return QIcon(pixmap(name, color, size))


def nav_icon(name):
    """Icon that turns gold while its (checkable) button is the active page."""
    ic = QIcon()
    ic.addPixmap(pixmap(name, T.MUTED, 19), QIcon.Mode.Normal, QIcon.State.Off)
    ic.addPixmap(pixmap(name, T.GOLD_HI, 19), QIcon.Mode.Normal, QIcon.State.On)
    return ic


_IMG_DIR = os.path.join(tempfile.gettempdir(), "oilshop_ui")


def _img(name, color):
    """Write an icon to disk so the stylesheet can point `image:` at it."""
    os.makedirs(_IMG_DIR, exist_ok=True)
    path = os.path.join(_IMG_DIR, f"{name}_{color.lstrip('#')}.png")
    if not os.path.exists(path):
        pixmap(name, color, 14, 2.2).save(path)
    return path.replace("\\", "/")


def qt_palette():
    """Fusion's own colours, so the widgets the stylesheet does not reach
    (calendar popup, completer list, file dialog) follow the theme too."""
    p = QPalette()
    R = QPalette.ColorRole
    for role, c in [(R.Window, T.BG), (R.WindowText, T.TEXT), (R.Base, T.FIELD),
                    (R.AlternateBase, T.CARD), (R.Text, T.TEXT), (R.Button, T.BTN),
                    (R.ButtonText, T.TEXT), (R.ToolTipBase, T.CARD), (R.ToolTipText, T.TEXT),
                    (R.Highlight, T.GOLD), (R.HighlightedText, T.ON_GOLD),
                    (R.PlaceholderText, T.FAINT), (R.Light, T.BORDER_HI), (R.Midlight, T.BORDER),
                    (R.Mid, T.BORDER), (R.Dark, T.LINE), (R.Shadow, T.SIDE)]:
        p.setColor(role, QColor(c))
    p.setColor(QPalette.ColorGroup.Disabled, R.Text, QColor(T.FAINT))
    p.setColor(QPalette.ColorGroup.Disabled, R.ButtonText, QColor(T.FAINT))
    return p


def build_qss():
    """Stylesheet for the palette that is currently active."""
    t = T
    gold_soft = t.soft(t.GOLD, 0.14)
    chev = _img("chev", t.MUTED)
    tones = "".join(
        f'#pill[tone="{n}"] {{ background:{t.soft(c, 0.16)}; color:{c}; }}\n'
        for n, c in [("good", t.GREEN), ("bad", t.RED), ("gold", t.GOLD_HI),
                     ("blue", t.BLUE), ("warn", t.ORANGE), ("violet", t.VIOLET)])
    return f"""
QWidget {{ color:{t.TEXT}; font-size:15px; }}
QMainWindow, QDialog, #root {{ background:{t.BG}; }}
QLabel {{ background:transparent; }}
QToolTip {{
    background:{t.CARD}; color:{t.TEXT}; border:1px solid {t.BORDER_HI};
    padding:6px 10px; border-radius:6px;
}}

/* ---------- لای ناڤیگەیشن ---------- */
#sidebar {{ background:{t.SIDE}; border-left:1px solid {t.LINE}; }}
#logo {{
    background:{t.GOLD}; color:{t.ON_GOLD}; border-radius:12px;
    font-size:22px; font-weight:800;
}}
#brand {{ color:{t.TITLE}; font-size:16px; font-weight:700; }}
#brandSub {{ color:{t.FAINT}; font-size:13px; }}
#navBtn {{
    background:transparent; border:none; border-radius:10px;
    padding:11px 14px; text-align:right; color:{t.MUTED};
    font-size:15px; font-weight:500;
}}
#navBtn:hover {{ background:{t.BTN}; color:{t.TEXT}; }}
#navBtn:checked {{ background:{gold_soft}; color:{t.GOLD_HI}; font-weight:700; }}

/* ---------- سەرەوە ---------- */
#header {{ background:{t.BG}; border-bottom:1px solid {t.LINE}; }}
#pageTitle {{ font-size:22px; font-weight:700; color:{t.TITLE}; }}
#pageSub {{ color:{t.MUTED}; font-size:14px; }}
#tag {{
    background:{t.CARD}; border:1px solid {t.BORDER}; border-radius:9px;
    padding:7px 12px; color:{t.MUTED}; font-size:13.5px;
}}

/* ---------- دەق ---------- */
#hint {{ color:{t.MUTED}; font-size:13.5px; }}
#secTitle {{ color:{t.MUTED}; font-size:13px; font-weight:700; }}
#panelTitle {{ color:{t.TITLE}; font-size:16px; font-weight:700; }}
#big {{ color:{t.GOLD_HI}; font-size:27px; font-weight:800; }}
#txtStrong {{ color:{t.TITLE}; font-weight:700; }}
#txtGood {{ color:{t.GREEN}; font-weight:700; }}
#txtBad {{ color:{t.RED}; font-weight:700; }}
#txtGold {{ color:{t.GOLD_HI}; font-weight:700; }}
#txtMuted {{ color:{t.MUTED}; }}

/* ---------- کارتەکان ---------- */
#card, #statCard, #pickCard {{
    background:{t.CARD}; border:1px solid {t.BORDER}; border-radius:14px;
}}
#statCap {{ color:{t.MUTED}; font-size:14px; }}
#statVal {{ color:{t.TITLE}; font-size:23px; font-weight:700; }}
#statSub {{ color:{t.MUTED}; font-size:13px; }}
#pickCard:hover {{ background:{t.CARD_HI}; border-color:{t.BORDER_HI}; }}
#pickCard[picked="true"] {{
    background:{t.soft(t.GOLD, 0.07)}; border:1px solid {t.GOLD};
}}
#cardTitle {{ color:{t.TITLE}; font-size:16px; font-weight:700; }}
#cardMeta {{ color:{t.MUTED}; font-size:13.5px; }}
#cardKey {{ color:{t.MUTED}; font-size:14px; }}
#avatar {{
    background:{gold_soft}; color:{t.GOLD_HI}; border-radius:19px;
    font-size:16px; font-weight:700;
}}
#pill {{
    background:{t.BTN}; color:{t.MUTED}; border-radius:9px;
    padding:3px 10px; font-size:12.5px; font-weight:700;
}}
{tones}
#cardSep {{ background:{t.LINE}; border:none; }}

/* ---------- دوگمەکان ---------- */
QPushButton {{
    background:{t.BTN}; color:{t.TEXT}; border:1px solid {t.BORDER};
    border-radius:9px; padding:8px 16px; min-height:20px; font-weight:600;
}}
QPushButton:hover {{ background:{t.BTN_HOVER}; border-color:{t.BORDER_HI}; }}
QPushButton:pressed {{ background:{t.BTN_PRESS}; }}
QPushButton:disabled {{ background:{t.BTN}; color:{t.FAINT}; border-color:{t.LINE}; }}
QPushButton#primary {{
    background:{t.GOLD}; color:{t.ON_GOLD}; border:1px solid {t.GOLD}; font-weight:700;
}}
QPushButton#primary:hover {{ background:{t.GOLD_HOVER}; border-color:{t.GOLD_HOVER}; }}
QPushButton#primary:pressed {{ background:{t.GOLD_PRESS}; border-color:{t.GOLD_PRESS}; }}
QPushButton#primary:disabled {{ background:{t.BTN}; color:{t.FAINT}; border-color:{t.LINE}; }}
QPushButton#danger {{
    background:transparent; color:{t.RED}; border-color:{t.soft(t.RED, 0.35)};
}}
QPushButton#danger:hover {{ background:{t.soft(t.RED, 0.14)}; border-color:{t.soft(t.RED, 0.6)}; }}
QPushButton#ghost {{ background:transparent; border-color:transparent; color:{t.MUTED}; }}
QPushButton#ghost:hover {{ background:{t.BTN}; color:{t.TEXT}; }}
QPushButton#chip {{
    background:transparent; border:1px solid {t.BORDER}; border-radius:15px;
    padding:5px 14px; min-height:18px; color:{t.MUTED}; font-weight:500; font-size:14px;
}}
QPushButton#chip:hover {{ color:{t.TEXT}; border-color:{t.BORDER_HI}; }}
QPushButton#chip:checked {{
    background:{gold_soft}; border-color:{t.soft(t.GOLD, 0.5)};
    color:{t.GOLD_HI}; font-weight:700;
}}
QPushButton#navBtn {{ border:none; }}

/* ---------- خانەکان ---------- */
QLineEdit, QComboBox, QAbstractSpinBox {{
    background:{t.FIELD}; border:1px solid {t.BORDER}; border-radius:9px;
    padding:8px 12px; color:{t.TEXT}; min-height:20px;
    selection-background-color:{t.GOLD}; selection-color:{t.ON_GOLD};
}}
QLineEdit:hover, QComboBox:hover, QAbstractSpinBox:hover {{ border-color:{t.BORDER_HI}; }}
QLineEdit:focus, QComboBox:focus, QAbstractSpinBox:focus {{ border-color:{t.GOLD}; }}
QLineEdit:disabled, QComboBox:disabled, QAbstractSpinBox:disabled {{ color:{t.FAINT}; }}
QComboBox QLineEdit, QAbstractSpinBox QLineEdit {{ border:none; padding:0; background:transparent; min-height:0; }}
QComboBox::drop-down, QDateEdit::drop-down {{ border:none; width:30px; }}
QComboBox::down-arrow, QDateEdit::down-arrow {{ image:url({chev}); width:14px; height:14px; }}
QComboBox QAbstractItemView, QListView {{
    background:{t.CARD}; color:{t.TEXT}; border:1px solid {t.BORDER_HI};
    selection-background-color:{gold_soft}; selection-color:{t.GOLD_HI}; outline:none;
}}
QComboBox QAbstractItemView {{ border-radius:10px; padding:5px; }}
QComboBox QAbstractItemView::item, QListView::item {{
    min-height:30px; padding:4px 10px; border-radius:7px;
}}
QComboBox QAbstractItemView::item:hover {{ background:{t.BTN_HOVER}; }}
QComboBox QAbstractItemView::item:selected, QListView::item:selected {{
    background:{gold_soft}; color:{t.GOLD_HI};
}}
QCalendarWidget QWidget#qt_calendar_navigationbar {{ background:{t.CARD}; }}
QCalendarWidget QToolButton {{
    background:transparent; color:{t.TEXT}; border:none; padding:6px 10px; font-weight:600;
}}
QCalendarWidget QToolButton:hover {{ background:{t.BTN_HOVER}; border-radius:6px; }}
QCalendarWidget QAbstractItemView {{
    background:{t.CARD}; border:none;
    selection-background-color:{t.GOLD}; selection-color:{t.ON_GOLD};
}}
QCalendarWidget QSpinBox {{ padding:2px 6px; min-height:0; }}
QMenu {{ background:{t.CARD}; border:1px solid {t.BORDER_HI}; padding:5px; }}
QMenu::item {{ padding:7px 18px; border-radius:6px; }}
QMenu::item:selected {{ background:{gold_soft}; color:{t.GOLD_HI}; }}

/* ---------- خشتەکان ---------- */
QTableWidget {{
    background:{t.CARD}; border:1px solid {t.BORDER}; border-radius:12px;
    gridline-color:transparent; outline:none;
}}
QTableWidget#flat {{ border:none; border-radius:0; }}
QTableWidget::item {{ border:none; border-bottom:1px solid {t.LINE}; padding:6px 8px; }}
QTableWidget::item:selected {{ background:{gold_soft}; color:{t.TITLE}; }}
QHeaderView {{ background:transparent; }}
QHeaderView::section {{
    background:{t.CARD}; color:{t.FAINT}; padding:10px 8px; border:none;
    border-bottom:1px solid {t.BORDER}; font-weight:700; font-size:13px;
}}
QTableCornerButton::section {{ background:{t.CARD}; border:none; }}

/* ---------- تاب ---------- */
QTabWidget::pane {{ border:none; }}
QTabBar {{ qproperty-drawBase:0; background:transparent; }}
QTabBar::tab {{
    background:transparent; color:{t.MUTED}; padding:8px 20px; margin-left:6px;
    border:1px solid transparent; border-radius:10px; font-weight:600;
}}
QTabBar::tab:hover {{ color:{t.TEXT}; }}
QTabBar::tab:selected {{
    background:{t.CARD}; color:{t.GOLD_HI}; border:1px solid {t.BORDER}; font-weight:700;
}}

/* ---------- جۆراوجۆر ---------- */
QScrollArea {{ background:transparent; border:none; }}
QScrollArea > QWidget > QWidget {{ background:transparent; }}
QTextBrowser {{
    background:{t.CARD}; border:1px solid {t.BORDER}; border-radius:12px; padding:18px;
}}
QMessageBox QLabel {{ color:{t.TEXT}; }}
QMessageBox QPushButton, QDialogButtonBox QPushButton {{ min-width:92px; }}
#toast {{
    background:{t.TITLE}; color:{t.BG}; border-radius:11px;
    padding:11px 20px; font-weight:700; font-size:13.5px;
}}

QScrollBar:vertical {{ background:transparent; width:10px; margin:3px; }}
QScrollBar::handle:vertical {{ background:{t.SCROLL}; border-radius:2px; min-height:40px; }}
QScrollBar::handle:vertical:hover {{ background:{t.SCROLL_HI}; }}
QScrollBar:horizontal {{ background:transparent; height:10px; margin:3px; }}
QScrollBar::handle:horizontal {{ background:{t.SCROLL}; border-radius:2px; min-width:40px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height:0; width:0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background:transparent; }}
"""


def apply_theme(app, name):
    apply_palette(name)
    app.setPalette(qt_palette())
    app.setStyleSheet(build_qss())
