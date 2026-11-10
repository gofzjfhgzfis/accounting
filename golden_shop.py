# -*- coding: utf-8 -*-
"""
سیستەمی حیساباتی دووکانی جوملە

    shop/core.py      داتابەیس و یارمەتیدەرەکان
    shop/theme.py     ڕەنگ، ئایکۆن و شێواز
    shop/ui.py        پارچە هاوبەشەکانی ڕووکار
    shop/pages_a.py   داشبۆرد، فرۆشتن، کڕیاران
    shop/pages_b.py   مەخزەن، دابینکەران، مەسروفات، ڕاپۆرت، ڕێکخستن
"""
import sys, os, datetime

from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont, QShortcut, QKeySequence
from PyQt6.QtWidgets import *

from shop.core import db, fmt, lrm, pin_hash, APP_TITLE, VERSION
from shop.theme import T, apply_theme, nav_icon, icon
from shop.ui import btn, label, form, dialog, dlg_buttons, restyle_tree, Toast
from shop.pages_a import Dashboard, Sales, Customers
from shop.pages_b import Inventory, Suppliers, Expenses, Reports, Settings


class Main(QMainWindow):
    PAGES = [
        ("dash", "داشبۆرد",          "پوختەی دووکانەکە لە یەک ڕوانیندا"),
        ("sale", "فرۆشتن",           "دەرکردنی پسووڵە و بەڕێوەبردنی فرۆشتن"),
        ("cust", "کڕیاران",          "قەرز، وەرگرتنی پارە و کەشف حساب"),
        ("inv",  "مەخزەن",           "کاڵاکان، کڕین و ئاگاداری کەمبوون"),
        ("sup",  "دابینکەران",       "قەرزی دابینکەران و مێژووی کڕین"),
        ("exp",  "مەسروفات و مووچە", "خەرجییەکان و کارمەندان"),
        ("rep",  "ڕاپۆرت",           "قازانج، فرۆشتن و هەناردەکردن"),
        ("st",   "ڕێکخستن",          "زانیاری دووکان، پاراستن و باکئەپ"),
    ]

    def __init__(self):
        super().__init__()
        self.skip_backup = False
        self.setWindowTitle(APP_TITLE)
        self.resize(1380, 860); self.setMinimumSize(1200, 720)

        self.dash = Dashboard(self); self.sale = Sales(self); self.cust = Customers(self)
        self.inv = Inventory(self); self.sup = Suppliers(self); self.exp = Expenses(self)
        self.rep = Reports(self); self.st = Settings(self)

        root = QWidget(); root.setObjectName("root")
        row = QHBoxLayout(root); row.setContentsMargins(0, 0, 0, 0); row.setSpacing(0)
        row.addWidget(self._sidebar())

        right = QWidget(); rv = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0); rv.setSpacing(0)
        rv.addWidget(self._header())
        self.stack = QStackedWidget()
        holder = QWidget(); hv = QVBoxLayout(holder)
        hv.setContentsMargins(24, 18, 24, 22); hv.addWidget(self.stack)
        for k, _, _ in self.PAGES:
            self.stack.addWidget(getattr(self, k))
        rv.addWidget(holder)
        row.addWidget(right, 1)
        self.setCentralWidget(root)

        self._toast = Toast(root)
        for i in range(len(self.PAGES)):
            QShortcut(QKeySequence(f"Ctrl+{i + 1}"), self, lambda n=i: self.go(n))
        QShortcut(QKeySequence("Ctrl+N"), self, self.new_invoice)
        QShortcut(QKeySequence("F5"), self, self.refresh_all)

        self.go(0)
        self.restyle()

    # ---- پێکهاتە ----
    def _sidebar(self):
        bar = QFrame(); bar.setObjectName("sidebar"); bar.setFixedWidth(232)
        v = QVBoxLayout(bar); v.setContentsMargins(14, 20, 14, 16); v.setSpacing(3)

        head = QHBoxLayout(); head.setSpacing(11); head.setContentsMargins(4, 0, 4, 0)
        self.logo = QLabel(); self.logo.setObjectName("logo")
        self.logo.setFixedSize(42, 42); self.logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        col = QVBoxLayout(); col.setSpacing(0)
        self.brand = label("", "brand", wrap=True)
        col.addWidget(self.brand); col.addWidget(label("دووکانی جوملە", "brandSub"))
        head.addWidget(self.logo); head.addLayout(col, 1)
        v.addLayout(head); v.addSpacing(20)

        self.nav = []
        for i, (key, name, _) in enumerate(self.PAGES):
            b = QPushButton("  " + name); b.setObjectName("navBtn")
            b.setCheckable(True); b.setAutoExclusive(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setToolTip(f"Ctrl+{i + 1}")
            b.clicked.connect(lambda _, n=i: self.go(n))
            self.nav.append(b); v.addWidget(b)
            if key in ("sale", "sup", "rep"): v.addSpacing(10)   # sell / stock / money groups

        v.addStretch()
        self.theme_btn = btn("", self.toggle_theme, "ghost", "sun")
        v.addWidget(self.theme_btn); v.addSpacing(6)
        self.foot = label("", "hint"); self.foot.setContentsMargins(6, 0, 6, 0)
        v.addWidget(self.foot)
        return bar

    def _header(self):
        h = QFrame(); h.setObjectName("header"); h.setFixedHeight(72)
        lay = QHBoxLayout(h); lay.setContentsMargins(24, 0, 24, 0); lay.setSpacing(8)
        col = QVBoxLayout(); col.setSpacing(0)
        col.addStretch()
        self.title = label("", "pageTitle"); self.sub = label("", "pageSub")
        col.addWidget(self.title); col.addWidget(self.sub); col.addStretch()
        lay.addLayout(col); lay.addStretch()
        self.rate = label("", "tag"); self.datelbl = label("", "tag")
        for w in (self.rate, self.datelbl):
            lay.addWidget(w, 0, Qt.AlignmentFlag.AlignVCenter)
        lay.addSpacing(4)
        b = btn("پسووڵەی نوێ", self.new_invoice, "primary", "plus"); b.setToolTip("Ctrl+N")
        lay.addWidget(b)
        return h

    # ---- ڕووکار ----
    def toggle_theme(self):
        db.set("theme", "light" if db.get("theme", "dark") == "dark" else "dark")
        apply_theme(QApplication.instance(), db.get("theme", "dark"))
        self.restyle()

    def restyle(self):
        dark = T.name == "dark"
        for b, (key, _, _) in zip(self.nav, self.PAGES):
            b.setIcon(nav_icon(key)); b.setIconSize(b.iconSize().expandedTo(self.logo.size() * 0.45))
        self.theme_btn.setProperty("ico", "sun" if dark else "moon")
        self.theme_btn.setText("  دۆخی ڕووناک" if dark else "  دۆخی تاریک")
        restyle_tree(self)
        self.refresh_all()

    def toast(self, text):
        self._toast.show_text(text)

    # ---- گەڕان ----
    def go(self, i):
        k, name, desc = self.PAGES[i]
        self.nav[i].setChecked(True)
        self.stack.setCurrentIndex(i)
        self.title.setText(name); self.sub.setText(desc)
        self.refresh_all()

    def new_invoice(self):
        self.go(1); self.sale.new_invoice()

    def refresh_all(self):
        """Redraw the page on screen; the others redraw when they are opened."""
        k = self.PAGES[self.stack.currentIndex()][0]
        try: getattr(self, k).refresh()
        except Exception as e: print("refresh error:", k, repr(e))
        name = db.get("company") or "دووکان"
        self.brand.setText(name); self.logo.setText(name.strip()[:1])
        self.setWindowTitle(f"{name} — {APP_TITLE}")
        self.foot.setText(f"وەشانی {VERSION}")
        self.datelbl.setText(lrm(QDate.currentDate().toString("yyyy-MM-dd")))
        try: rate = float(db.get("usd") or 0)
        except Exception: rate = 0
        self.rate.setVisible(rate > 0)
        self.rate.setText(f"{lrm('$1')} = {fmt(rate)} {db.get('currency')}")

    def closeEvent(self, e):
        if not self.skip_backup:
            try:
                p = db.get("backup")
                if p and os.path.isdir(p):
                    db.backup_to(p, "%Y-%m-%d")      # one file per day, newest 20 kept
            except Exception:
                pass
        e.accept()


def first_run():
    """Ask for the shop's own details the first time the app is opened."""
    d = QDialog(); d.setWindowTitle("بەخێربێیت"); d.setMinimumWidth(460)
    v = QVBoxLayout(d); v.setSpacing(14); v.setContentsMargins(26, 24, 26, 22)
    v.addWidget(label("ناوی دووکانەکەت بنووسە", "pageTitle"))
    v.addWidget(label("ئەم ناوە لە سەرەوەی بەرنامەکە و لەسەر پسووڵەکان دەردەکەوێت. "
                      "دواتر دەتوانیت لە بەشی ڕێکخستن بیگۆڕیت.", "hint", wrap=True))
    f = QFormLayout(); f.setSpacing(11)
    co, ph, ad = QLineEdit(), QLineEdit(), QLineEdit()
    co.setPlaceholderText("پێویستە")
    f.addRow("ناوی دووکان", co); f.addRow("مۆبایل", ph); f.addRow("ناونیشان", ad)
    v.addLayout(f)
    ok = btn("دەستپێکردن", kind="primary")
    ok.setEnabled(False)
    co.textChanged.connect(lambda s: ok.setEnabled(bool(s.strip())))
    ok.clicked.connect(d.accept)
    v.addWidget(ok)
    if d.exec() and co.text().strip():
        db.set("company", co.text().strip())
        db.set("phone", ph.text().strip())
        db.set("address", ad.text().strip())


def unlock():
    """Ask for the PIN when one is set. False means the app should not open."""
    while db.get("pin"):
        d = QDialog(); d.setWindowTitle(db.get("company") or APP_TITLE); d.setMinimumWidth(360)
        v = QVBoxLayout(d); v.setSpacing(12); v.setContentsMargins(26, 24, 26, 22)
        v.addWidget(label("بەرنامەکە قفڵ کراوە", "pageTitle"))
        v.addWidget(label("ژمارەی نهێنی بنووسە بۆ بەردەوامبوون.", "hint"))
        e = QLineEdit(); e.setEchoMode(QLineEdit.EchoMode.Password)
        e.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        v.addWidget(e)
        ok = btn("کردنەوە", d.accept, "primary", "lock"); v.addWidget(ok)
        if not d.exec(): return False
        if pin_hash(e.text()) == db.get("pin"): return True
        QMessageBox.warning(None, "هەڵە", "ژمارەی نهێنی هەڵەیە")
    return True


def setup_app(app):
    app.setStyle("Fusion")
    app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    for fam in ["Segoe UI", "Tahoma", "Arial"]:
        f = QFont(fam, 10)
        if f.exactMatch() or fam == "Arial":
            app.setFont(f); break
    apply_theme(app, db.get("theme", "dark"))


def main():
    app = QApplication(sys.argv)
    setup_app(app)
    if not unlock():
        return
    if not db.get("company"):
        first_run()
    w = Main(); w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
