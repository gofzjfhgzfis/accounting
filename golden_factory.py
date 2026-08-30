# -*- coding: utf-8 -*-
"""
سیستەمی حیساباتی کارگە
"""
import sys, os, re, sqlite3, shutil, datetime, configparser

from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtWidgets import *

APP_TITLE = "سیستەمی کارگە"
APP_DIR   = os.path.join(os.path.expanduser("~"), "FactoryAccounting")
os.makedirs(APP_DIR, exist_ok=True)

# Data saved under the folder this app used to have is carried over once,
# so renaming the app does not look like the records disappeared.
_OLD_DIR = os.path.join(os.path.expanduser("~"), "GoldenBaseFactory")
if os.path.isdir(_OLD_DIR):
    for _old, _new in [("config.ini", "config.ini"), ("golden_factory.db", "factory.db")]:
        _a, _b = os.path.join(_OLD_DIR, _old), os.path.join(APP_DIR, _new)
        if os.path.exists(_a) and not os.path.exists(_b):
            try: shutil.copy2(_a, _b)
            except Exception: pass

CFG_PATH  = os.path.join(APP_DIR, "config.ini")

# config.ini stays on THIS computer, so the database can live elsewhere
# (a network folder, a synced Drive folder) without touching anything else.
_cfg = configparser.ConfigParser()
_cfg.read(CFG_PATH, encoding="utf-8")
if "app" not in _cfg:
    _cfg["app"] = {}

DB_PATH = _cfg["app"].get("db_path", "") or os.path.join(APP_DIR, "factory.db")


def save_cfg(**kw):
    for k, v in kw.items():
        _cfg["app"][k] = str(v)
    with open(CFG_PATH, "w", encoding="utf-8") as f:
        _cfg.write(f)

# ---------------------------------------------------------------- تەختەڕەنگ
PALETTES = {
    "dark": dict(
        BG="#1A1D24", PANEL="#232A34", SURFACE="#2A3140", FIELD="#161B23",
        BORDER="#3B4555", DIVIDER="#2E3847", TEXT="#E8EAF0", TITLE="#F5F7FB",
        MUTED="#8E98A8", FAINT="#7A8598",
        GOLD="#DEB145", GOLD_HI="#F5D876", GOLD_PRESS="#C9A03A", ON_GOLD="#13150A",
        NAV_FG="#A0AABC", NAV_HOVER="#2E3847", NAV_ACTIVE="#35404D",
        BTN="#39434F", BTN_BORDER="#556273", BTN_HOVER="#454F5D",
        BTN_HOVER_BORDER="#6B7A8E", BTN_PRESS="#2F3742",
        INPUT_BORDER="#556273", MENU_BG="#232A34", HEADER_BG="#1F2632",
        ROW_LINE="#2E3847", SEL_BG="#3D3820", DLG_BG="#1A1D24",
        SCROLL="#404D5C", SCROLL_HI="#4E5D70",
        DANGER_FG="#E8949A", DANGER_BORDER="#4A3536",
        DANGER_BG="#3A2527", DANGER_BORDER_HI="#6B4248",
        GREEN="#4FC9A0", BLUE="#5E9FFF", RED="#F07676",
        VIOLET="#A089E8", ORANGE="#F5A366",
    ),
    "light": dict(
        BG="#FAF9F7", PANEL="#FFFFFF", SURFACE="#FFFFFF", FIELD="#FFFFFF",
        BORDER="#EDE8E0", DIVIDER="#E6DFD5", TEXT="#3D424D", TITLE="#1F242C",
        MUTED="#8A9199", FAINT="#9AA3AD",
        GOLD="#C49B2E", GOLD_HI="#A68318", GOLD_PRESS="#B59125", ON_GOLD="#FFFFFF",
        NAV_FG="#6F7A88", NAV_HOVER="#F5F2EA", NAV_ACTIVE="#F9F5ED",
        BTN="#FFFFFF", BTN_BORDER="#C9BFAE", BTN_HOVER="#F5F2EA",
        BTN_HOVER_BORDER="#A89C88", BTN_PRESS="#F0EDE5",
        INPUT_BORDER="#C9BFAE", MENU_BG="#FFFFFF", HEADER_BG="#F5F2EA",
        ROW_LINE="#F0EDE5", SEL_BG="#FEFAF0", DLG_BG="#FDFBF8",
        SCROLL="#D9D2C7", SCROLL_HI="#C4BCB0",
        DANGER_FG="#D94C54", DANGER_BORDER="#F0D4CE",
        DANGER_BG="#FCEAE5", DANGER_BORDER_HI="#E8BAAD",
        GREEN="#3D9D6F", BLUE="#3D7FD4", RED="#D94C54",
        VIOLET="#7B5FC4", ORANGE="#D97C3F",
    ),
}


def apply_palette(name):
    """Swap the active colour names in this module's namespace."""
    globals().update(PALETTES.get(name, PALETTES["dark"]))


apply_palette("dark")

SCHEMA = """
CREATE TABLE IF NOT EXISTS settings(k TEXT PRIMARY KEY, v TEXT);
CREATE TABLE IF NOT EXISTS items(
    id INTEGER PRIMARY KEY, name TEXT, kind TEXT, unit TEXT,
    qty REAL DEFAULT 0, cost REAL DEFAULT 0, price REAL DEFAULT 0, minq REAL DEFAULT 0);
CREATE TABLE IF NOT EXISTS dispatch(
    id INTEGER PRIMARY KEY, date TEXT, item_id INTEGER, qty REAL,
    cost REAL, dest TEXT, note TEXT);
CREATE TABLE IF NOT EXISTS purchases(
    id INTEGER PRIMARY KEY, date TEXT, supplier TEXT, item_id INTEGER,
    qty REAL, price REAL, note TEXT);
CREATE TABLE IF NOT EXISTS production(
    id INTEGER PRIMARY KEY, date TEXT, item_id INTEGER, qty REAL,
    mat_cost REAL, labor REAL, overhead REAL, total REAL, note TEXT);
CREATE TABLE IF NOT EXISTS prod_inputs(
    id INTEGER PRIMARY KEY, prod_id INTEGER, item_id INTEGER, qty REAL, cost REAL);
CREATE TABLE IF NOT EXISTS expenses(
    id INTEGER PRIMARY KEY, date TEXT, category TEXT, amount REAL, note TEXT);
CREATE TABLE IF NOT EXISTS employees(
    id INTEGER PRIMARY KEY, name TEXT, position TEXT, salary REAL, phone TEXT);
CREATE TABLE IF NOT EXISTS salaries(
    id INTEGER PRIMARY KEY, date TEXT, employee_id INTEGER, amount REAL, note TEXT);
"""


# ---------------------------------------------------------------- داتابەیس
class DB:
    def __init__(self):
        self.con = sqlite3.connect(DB_PATH)
        self.con.row_factory = sqlite3.Row
        self.con.executescript(SCHEMA)
        self.con.commit()
        for k, v in [("company", ""), ("phone", ""), ("address", ""),
                     ("currency", "د.ع"), ("usd", "1320"), ("backup", ""), ("theme", "dark")]:
            if not self.one("SELECT v FROM settings WHERE k=?", (k,)):
                self.x("INSERT INTO settings(k,v) VALUES(?,?)", (k, v))

    def q(self, sql, p=()):   return self.con.execute(sql, p).fetchall()
    def one(self, sql, p=()): return self.con.execute(sql, p).fetchone()

    def x(self, sql, p=()):
        c = self.con.execute(sql, p); self.con.commit(); return c.lastrowid

    def get(self, k, d=""):
        r = self.one("SELECT v FROM settings WHERE k=?", (k,))
        return r["v"] if r else d

    def set(self, k, v):
        self.x("INSERT INTO settings(k,v) VALUES(?,?) ON CONFLICT(k) DO UPDATE SET v=?",
               (k, str(v), str(v)))


db = DB()


# ---------------------------------------------------------------- یارمەتیدەر
def fmt(n):
    try: n = float(n)
    except Exception: return "0"
    return f"{n:,.0f}" if abs(n - round(n)) < 0.01 else f"{n:,.2f}"


def today(): return QDate.currentDate().toString("yyyy-MM-dd")


def msg(parent, text, title="ئاگاداری"):
    QMessageBox.information(parent, title, text)


def ask(parent, text):
    return QMessageBox.question(parent, "دڵنیابوونەوە", text,
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) == QMessageBox.StandardButton.Yes


def btn(text, fn=None, kind=""):
    b = QPushButton(text)
    if kind: b.setObjectName(kind)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    if fn: b.clicked.connect(fn)
    return b


def table(headers):
    t = QTableWidget(); t.setColumnCount(len(headers))
    t.setHorizontalHeaderLabels(headers)
    t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    t.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    t.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    t.setShowGrid(False)
    t.setAlternatingRowColors(False)
    t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    t.horizontalHeader().setHighlightSections(False)
    t.verticalHeader().setVisible(False)
    t.verticalHeader().setDefaultSectionSize(42)
    return t


LRM = "\u200e"
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def lrm(v):
    """Pin a digit-only string so RTL bidi can't reorder it (0750 123 4567)."""
    v = str(v).strip()
    return LRM + v if v else v


def ltr(v):
    v = str(v)
    return LRM + v if DATE_RE.match(v) else v


def fill(t, rows):
    t.setRowCount(len(rows))
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            it = QTableWidgetItem(ltr(val))
            it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            t.setItem(i, j, it)


def fit(t, stretch):
    """Size every column to its content and let one column absorb the slack."""
    h = t.horizontalHeader()
    for i in range(t.columnCount()):
        h.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
    h.setSectionResizeMode(stretch, QHeaderView.ResizeMode.Stretch)


def picked_id(t, col=0):
    r = t.currentRow()
    if r < 0: return None
    try: return int(t.item(r, col).text())
    except Exception: return None


def date_edit():
    d = QDateEdit(QDate.currentDate())
    d.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
    d.setCalendarPopup(True)
    d.setDisplayFormat("yyyy-MM-dd")
    return d


def num(mx=1e12, dec=0):
    s = QDoubleSpinBox(); s.setRange(0, mx); s.setDecimals(dec)
    s.setGroupSeparatorShown(True)
    s.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
    return s


def combo():
    c = QComboBox()
    # the built-in popup delegate ignores the stylesheet's row height,
    # so the list comes out cramped; a plain delegate honours it.
    c.setItemDelegate(QStyledItemDelegate(c))
    c.view().setSpacing(1)
    return c


def heading(text):
    l = QLabel(text); l.setObjectName("secTitle"); return l


def dialog(parent, title, w=430):
    d = QDialog(parent); d.setWindowTitle(title); d.setMinimumWidth(w)
    d.setObjectName("dlg")
    return d


def dlg_buttons(d, form):
    bb = QDialogButtonBox()
    ok = bb.addButton("پاشەکەوتکردن", QDialogButtonBox.ButtonRole.AcceptRole)
    ok.setObjectName("primary")
    cancel = bb.addButton("پاشگەزبوونەوە", QDialogButtonBox.ButtonRole.RejectRole)
    cancel.setCursor(Qt.CursorShape.PointingHandCursor)
    ok.setCursor(Qt.CursorShape.PointingHandCursor)
    bb.accepted.connect(d.accept); bb.rejected.connect(d.reject)
    form.addRow(bb)


# ---------------------------------------------------------------- کارتی ئامار
class StatCard(QFrame):
    def __init__(self, caption, accent):
        super().__init__()
        self.accent = accent          # palette key, resolved at paint time
        self.setObjectName("statCard")
        self.setMinimumHeight(96); self.setMaximumHeight(122)
        h = QHBoxLayout(self); h.setContentsMargins(18, 16, 18, 16); h.setSpacing(14)

        self.bar = QFrame(); self.bar.setFixedSize(3, 52)
        h.addWidget(self.bar, 0, Qt.AlignmentFlag.AlignVCenter)
        self.restyle()

        v = QVBoxLayout(); v.setSpacing(5); v.setContentsMargins(0, 0, 0, 0)
        cap = QLabel(caption); cap.setObjectName("statCap")
        self.val = QLabel("0"); self.val.setObjectName("statVal")
        v.addWidget(cap); v.addWidget(self.val)
        h.addLayout(v); h.addStretch()

    def set(self, text):
        self.val.setText(str(text))

    def restyle(self):
        self.bar.setStyleSheet(
            f"background:{globals()[self.accent]};border-radius:2px;")


# ---------------------------------------------------------------- داشبۆرد
class Dashboard(QWidget):
    SPECS = [("بەهای مەخزەن", "VIOLET"), ("مادەی خامی کەمبوو", "ORANGE"),
             ("بەرهەمی ئەم مانگە", "GREEN"), ("تێچووی بەرهەمهێنان", "GOLD"),
             ("مەسروفات و مووچە", "BLUE"), ("دەرچووی ئەم مانگە", "RED")]

    def __init__(self):
        super().__init__()
        v = QVBoxLayout(self); v.setSpacing(18); v.setContentsMargins(0, 0, 0, 0)
        g = QGridLayout(); g.setSpacing(14)
        self.c = {}
        for i, (cap, accent) in enumerate(self.SPECS):
            card = StatCard(cap, accent); self.c[cap] = card
            g.addWidget(card, i // 3, i % 3)
        v.addLayout(g)
        v.addWidget(heading("دواین بەچەکانی بەرهەمهێنان"))
        self.tbl = table(["بەروار", "بەرهەم", "بڕ", "تێچووی یەکە"]); fit(self.tbl, 1)
        v.addWidget(self.tbl)

    def refresh(self):
        cur = db.get("currency")
        m = today()[:7]
        stock = db.one("SELECT IFNULL(SUM(qty*cost),0) t FROM items")["t"]
        low = db.one("SELECT COUNT(*) c FROM items WHERE qty<=minq AND minq>0")["c"]
        pq = db.one("SELECT IFNULL(SUM(qty),0) q FROM production WHERE date LIKE ?", (m + "%",))["q"]
        pt = db.one("SELECT IFNULL(SUM(total),0) t FROM production WHERE date LIKE ?", (m + "%",))["t"]
        exp = db.one("SELECT IFNULL(SUM(amount),0) t FROM expenses WHERE date LIKE ?", (m + "%",))["t"]
        sal = db.one("SELECT IFNULL(SUM(amount),0) t FROM salaries WHERE date LIKE ?", (m + "%",))["t"]
        out = db.one("SELECT IFNULL(SUM(qty),0) q FROM dispatch WHERE date LIKE ?", (m + "%",))["q"]

        self.c["بەهای مەخزەن"].set(f"{fmt(stock)} {cur}")
        self.c["مادەی خامی کەمبوو"].set(str(low))
        self.c["بەرهەمی ئەم مانگە"].set(fmt(pq))
        self.c["تێچووی بەرهەمهێنان"].set(f"{fmt(pt)} {cur}")
        self.c["مەسروفات و مووچە"].set(f"{fmt(exp + sal)} {cur}")
        self.c["دەرچووی ئەم مانگە"].set(fmt(out))

        rows = db.q("SELECT p.*, it.name FROM production p JOIN items it ON it.id=p.item_id "
                    "ORDER BY p.id DESC LIMIT 10")
        fill(self.tbl, [(r["date"], r["name"], fmt(r["qty"]),
                         fmt(r["total"] / r["qty"] if r["qty"] else 0)) for r in rows])


# ---------------------------------------------------------------- مەخزەن
class Inventory(QWidget):
    KINDS = ["مادەی خام", "بەرهەم"]

    def __init__(self, app):
        super().__init__(); self.app = app
        v = QVBoxLayout(self); v.setSpacing(14); v.setContentsMargins(0, 0, 0, 0)
        top = QHBoxLayout(); top.setSpacing(9)
        top.addWidget(btn("کاڵای نوێ", self.add, "primary"))
        top.addWidget(btn("دەستکاری", self.edit))
        top.addWidget(btn("کڕین / زیادکردنی بڕ", self.purchase))
        top.addWidget(btn("سڕینەوە", self.rm, "danger"))
        top.addStretch()
        self.filt = combo(); self.filt.addItems(["هەموو جۆرەکان"] + self.KINDS)
        self.filt.setMinimumWidth(180)
        self.filt.currentIndexChanged.connect(self.refresh)
        top.addWidget(self.filt); v.addLayout(top)
        self.tbl = table(["#", "ناو", "جۆر", "یەکە", "بڕ", "تێچوو/یەکە", "نرخی فرۆشتن", "کەمترین بڕ"])
        v.addWidget(self.tbl)

    def refresh(self):
        k = self.filt.currentText()
        rows = db.q("SELECT * FROM items ORDER BY name") if k == "هەموو جۆرەکان" else \
               db.q("SELECT * FROM items WHERE kind=? ORDER BY name", (k,))
        fill(self.tbl, [(r["id"], r["name"], r["kind"], r["unit"] or "—", fmt(r["qty"]),
                         fmt(r["cost"]), fmt(r["price"]), fmt(r["minq"])) for r in rows])
        for i, r in enumerate(rows):
            if r["minq"] and r["qty"] <= r["minq"]:
                for j in range(self.tbl.columnCount()):
                    self.tbl.item(i, j).setForeground(QColor(RED))

    def form(self, r=None):
        d = dialog(self, "کاڵا"); f = QFormLayout(d); f.setSpacing(12)
        name = QLineEdit(); kind = combo(); kind.addItems(self.KINDS)
        unit = QLineEdit(); unit.setPlaceholderText("لیتر / کارتۆن / کیلۆ")
        cost, price, minq = num(dec=2), num(dec=2), num(dec=2)
        if r:
            name.setText(r["name"]); kind.setCurrentText(r["kind"]); unit.setText(r["unit"] or "")
            cost.setValue(r["cost"]); price.setValue(r["price"]); minq.setValue(r["minq"])
        f.addRow("ناو", name); f.addRow("جۆر", kind); f.addRow("یەکە", unit)
        f.addRow("تێچووی یەکە", cost); f.addRow("نرخی فرۆشتن", price)
        f.addRow("کەمترین بڕ", minq)
        dlg_buttons(d, f)
        if d.exec() and name.text().strip():
            return (name.text().strip(), kind.currentText(), unit.text(),
                    cost.value(), price.value(), minq.value())
        return None

    def add(self):
        v = self.form()
        if v:
            db.x("INSERT INTO items(name,kind,unit,cost,price,minq) VALUES(?,?,?,?,?,?)", v)
            self.app.refresh_all()

    def edit(self):
        i = picked_id(self.tbl)
        if not i: return msg(self, "سەرەتا کاڵایەک هەڵبژێرە")
        v = self.form(db.one("SELECT * FROM items WHERE id=?", (i,)))
        if v:
            db.x("UPDATE items SET name=?,kind=?,unit=?,cost=?,price=?,minq=? WHERE id=?", (*v, i))
            self.app.refresh_all()

    def rm(self):
        i = picked_id(self.tbl)
        if not i: return msg(self, "سەرەتا کاڵایەک هەڵبژێرە")
        if ask(self, "دڵنیایت لە سڕینەوە؟"):
            db.x("DELETE FROM items WHERE id=?", (i,)); self.app.refresh_all()

    def purchase(self):
        i = picked_id(self.tbl)
        if not i: return msg(self, "سەرەتا کاڵایەک هەڵبژێرە")
        it = db.one("SELECT * FROM items WHERE id=?", (i,))
        d = dialog(self, f"کڕین — {it['name']}"); f = QFormLayout(d); f.setSpacing(12)
        dt, sup, qty, pr, nt = date_edit(), QLineEdit(), num(dec=2), num(dec=2), QLineEdit()
        pr.setValue(it["cost"])
        f.addRow("بەروار", dt); f.addRow("دابینکەر", sup); f.addRow("بڕ", qty)
        f.addRow("نرخی یەکە", pr); f.addRow("تێبینی", nt)
        dlg_buttons(d, f)
        if d.exec() and qty.value() > 0:
            oq, oc = it["qty"], it["cost"]
            nq = oq + qty.value()
            nc = ((oq * oc) + (qty.value() * pr.value())) / nq if nq else pr.value()
            db.x("UPDATE items SET qty=?, cost=? WHERE id=?", (nq, nc, i))
            db.x("INSERT INTO purchases(date,supplier,item_id,qty,price,note) VALUES(?,?,?,?,?,?)",
                 (dt.date().toString("yyyy-MM-dd"), sup.text(), i, qty.value(), pr.value(), nt.text()))
            self.app.refresh_all()


# ---------------------------------------------------------------- بەرهەمهێنان
class Production(QWidget):
    def __init__(self, app):
        super().__init__(); self.app = app
        self.inputs = []
        main = QHBoxLayout(self); main.setSpacing(16); main.setContentsMargins(0, 0, 0, 0)
        box = QGroupBox("تۆماری بەرهەمهێنانی نوێ"); v = QVBoxLayout(box); v.setSpacing(12)
        f = QFormLayout(); f.setSpacing(11)
        self.dt = date_edit(); self.out = combo(); self.oqty = num(dec=2)
        self.labor, self.over = num(dec=2), num(dec=2); self.note = QLineEdit()
        self.oqty.valueChanged.connect(self.calc)
        self.labor.valueChanged.connect(self.calc)
        self.over.valueChanged.connect(self.calc)
        f.addRow("بەروار", self.dt); f.addRow("بەرهەمی درووستکراو", self.out)
        f.addRow("بڕی بەرهەمهاتوو", self.oqty)
        f.addRow("مووچەی کرێکار", self.labor)
        f.addRow("تێچووی گشتی", self.over)
        f.addRow("تێبینی", self.note)
        v.addLayout(f)

        v.addWidget(heading("مادەی خامی بەکارهاتوو"))
        h = QGridLayout(); h.setSpacing(9)
        self.raw = combo()
        self.raw.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.rqty = num(dec=2)
        h.addWidget(QLabel("مادە"), 0, 0); h.addWidget(self.raw, 0, 1)
        h.addWidget(QLabel("بڕ"), 1, 0); h.addWidget(self.rqty, 1, 1)
        h.addWidget(btn("زیادکردن", self.add_in), 2, 1)
        v.addLayout(h)
        self.it = table(["مادە", "بڕ", "تێچوو"]); fit(self.it, 0)
        v.addWidget(self.it)
        v.addWidget(btn("لابردنی ڕیزی هەڵبژێردراو", self.rm_in, "danger"))

        self.sum_lbl = QLabel(); self.sum_lbl.setObjectName("summary")
        self.sum_lbl.setWordWrap(True)
        v.addWidget(self.sum_lbl)
        v.addWidget(btn("تۆمارکردنی بەرهەمهێنان", self.save, "primary"))
        main.addWidget(box, 5)

        box2 = QGroupBox("تۆمارەکانی بەرهەمهێنان"); v2 = QVBoxLayout(box2)
        self.tbl = table(["بەروار", "بەرهەم", "بڕ", "تێچووی یەکە"])
        fit(self.tbl, 1); self.tbl.setColumnWidth(1, 130)
        self.tbl.setTextElideMode(Qt.TextElideMode.ElideRight)
        v2.addWidget(self.tbl); main.addWidget(box2, 4)

    def refresh(self):
        self.out.clear(); self.raw.clear()
        for i in db.q("SELECT id,name FROM items WHERE kind='بەرهەم' ORDER BY name"):
            self.out.addItem(i["name"], i["id"])
        for i in db.q("SELECT id,name,qty FROM items WHERE kind='مادەی خام' ORDER BY name"):
            self.raw.addItem(f"{i['name']}   ·   بڕ {fmt(i['qty'])}", i["id"])
        rows = db.q("SELECT p.*, it.name FROM production p JOIN items it ON it.id=p.item_id "
                    "ORDER BY p.id DESC LIMIT 200")
        fill(self.tbl, [(r["date"], r["name"], fmt(r["qty"]),
                         fmt(r["total"] / r["qty"] if r["qty"] else 0)) for r in rows])
        self.calc()

    def add_in(self):
        i = self.raw.currentData()
        if not i or self.rqty.value() <= 0: return
        it = db.one("SELECT * FROM items WHERE id=?", (i,))
        # what is already in this batch counts against the stock too
        already = sum(x["qty"] for x in self.inputs if x["id"] == i)
        if already + self.rqty.value() > it["qty"]:
            if not ask(self, f"بڕی بەردەست تەنها {fmt(it['qty'])}ە. بەردەوام بم؟"): return
        for x in self.inputs:
            if x["id"] == i:
                x["qty"] += self.rqty.value()
                break
        else:
            self.inputs.append({"id": i, "name": it["name"], "qty": self.rqty.value(), "cost": it["cost"]})
        self.calc()

    def rm_in(self):
        r = self.it.currentRow()
        if r >= 0: self.inputs.pop(r); self.calc()

    def calc(self):
        fill(self.it, [(x["name"], fmt(x["qty"]), fmt(x["qty"] * x["cost"])) for x in self.inputs])
        mat = sum(x["qty"] * x["cost"] for x in self.inputs)
        tot = mat + self.labor.value() + self.over.value()
        u = tot / self.oqty.value() if self.oqty.value() else 0
        self.sum_lbl.setText(
            f"تێچووی مادە <b>{fmt(mat)}</b> &nbsp;·&nbsp; کۆی تێچوو <b>{fmt(tot)}</b> "
            f"&nbsp;·&nbsp; <span style='color:{GOLD_HI};'>تێچووی یەک یەکە <b>{fmt(u)}</b></span>")

    def save(self):
        if not self.inputs: return msg(self, "هیچ مادەی خامێک زیاد نەکراوە")
        if self.oqty.value() <= 0: return msg(self, "بڕی بەرهەمهاتوو دیاری بکە")
        oid = self.out.currentData()
        if not oid: return msg(self, "سەرەتا کاڵایەکی جۆری «بەرهەم» درووست بکە")
        mat = sum(x["qty"] * x["cost"] for x in self.inputs)
        tot = mat + self.labor.value() + self.over.value()
        unit = tot / self.oqty.value()
        pid = db.x("INSERT INTO production(date,item_id,qty,mat_cost,labor,overhead,total,note) "
                   "VALUES(?,?,?,?,?,?,?,?)",
                   (self.dt.date().toString("yyyy-MM-dd"), oid, self.oqty.value(),
                    mat, self.labor.value(), self.over.value(), tot, self.note.text()))
        for x in self.inputs:
            db.x("INSERT INTO prod_inputs(prod_id,item_id,qty,cost) VALUES(?,?,?,?)",
                 (pid, x["id"], x["qty"], x["cost"]))
            db.x("UPDATE items SET qty=qty-? WHERE id=?", (x["qty"], x["id"]))
        o = db.one("SELECT qty,cost FROM items WHERE id=?", (oid,))
        nq = o["qty"] + self.oqty.value()
        nc = ((o["qty"] * o["cost"]) + tot) / nq if nq else unit
        db.x("UPDATE items SET qty=?, cost=? WHERE id=?", (nq, nc, oid))
        self.inputs = []; self.labor.setValue(0); self.over.setValue(0); self.note.clear()
        self.app.refresh_all()
        msg(self, f"تۆمارکرا. تێچووی یەک یەکە: {fmt(unit)} {db.get('currency')}")


# ---------------------------------------------------------------- دەرچوون
class Dispatch(QWidget):
    """Finished goods leaving the plant — to the shop, a customer, anywhere."""

    def __init__(self, app):
        super().__init__(); self.app = app
        main = QHBoxLayout(self); main.setSpacing(16); main.setContentsMargins(0, 0, 0, 0)

        box = QGroupBox("دەرچوونی نوێ"); f = QFormLayout(box); f.setSpacing(11)
        self.dt = date_edit(); self.item = combo()
        self.item.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.qty = num(dec=2); self.dest = QLineEdit(); self.note = QLineEdit()
        self.dest.setPlaceholderText("دووکان / کڕیار / شوێنی گەیاندن")
        f.addRow("بەروار", self.dt); f.addRow("بەرهەم", self.item)
        f.addRow("بڕ", self.qty); f.addRow("بۆ کوێ", self.dest)
        f.addRow("تێبینی", self.note)
        f.addRow(btn("تۆمارکردنی دەرچوون", self.save, "primary"))
        main.addWidget(box, 4)

        box2 = QGroupBox("تۆمارەکانی دەرچوون"); v2 = QVBoxLayout(box2); v2.setSpacing(12)
        self.tbl = table(["#", "بەروار", "بەرهەم", "بڕ", "بۆ کوێ"]); fit(self.tbl, 2)
        v2.addWidget(self.tbl)
        v2.addWidget(btn("سڕینەوە — بڕەکە دەگەڕێتەوە مەخزەن", self.rm, "danger"))
        main.addWidget(box2, 5)

    def refresh(self):
        self.item.clear()
        for i in db.q("SELECT id,name,qty FROM items WHERE kind='بەرهەم' ORDER BY name"):
            self.item.addItem(f"{i['name']}   ·   بڕ {fmt(i['qty'])}", i["id"])
        rows = db.q("SELECT d.*, it.name FROM dispatch d JOIN items it ON it.id=d.item_id "
                    "ORDER BY d.id DESC LIMIT 300")
        fill(self.tbl, [(r["id"], r["date"], r["name"], fmt(r["qty"]), r["dest"] or "—")
                        for r in rows])

    def save(self):
        i = self.item.currentData()
        if not i: return msg(self, "سەرەتا بەرهەمێک درووست بکە")
        if self.qty.value() <= 0: return msg(self, "بڕەکە دیاری بکە")
        it = db.one("SELECT * FROM items WHERE id=?", (i,))
        if self.qty.value() > it["qty"]:
            if not ask(self, f"بڕی بەردەست تەنها {fmt(it['qty'])}ە. بەردەوام بم؟"): return
        db.x("INSERT INTO dispatch(date,item_id,qty,cost,dest,note) VALUES(?,?,?,?,?,?)",
             (self.dt.date().toString("yyyy-MM-dd"), i, self.qty.value(),
              it["cost"], self.dest.text(), self.note.text()))
        db.x("UPDATE items SET qty=qty-? WHERE id=?", (self.qty.value(), i))
        self.qty.setValue(0); self.dest.clear(); self.note.clear()
        self.app.refresh_all()
        msg(self, "تۆمارکرا")

    def rm(self):
        i = picked_id(self.tbl)
        if not i: return msg(self, "سەرەتا ڕیزێک هەڵبژێرە")
        if not ask(self, "بسڕدرێتەوە؟ بڕەکە دەگەڕێتەوە مەخزەن."): return
        r = db.one("SELECT * FROM dispatch WHERE id=?", (i,))
        db.x("UPDATE items SET qty=qty+? WHERE id=?", (r["qty"], r["item_id"]))
        db.x("DELETE FROM dispatch WHERE id=?", (i,))
        self.app.refresh_all()


# ---------------------------------------------------------------- مەسروفات و مووچە
class Expenses(QWidget):
    CATS = ["کارەبا", "سووتەمەنی", "کرێ", "گواستنەوە", "چاککردنەوە", "بازرگانی", "هیتر"]

    def __init__(self, app):
        super().__init__(); self.app = app
        v = QVBoxLayout(self); v.setContentsMargins(0, 0, 0, 0)
        tabs = QTabWidget(); v.addWidget(tabs)

        w1 = QWidget(); v1 = QVBoxLayout(w1); v1.setSpacing(14); v1.setContentsMargins(0, 16, 0, 0)
        h = QHBoxLayout(); h.setSpacing(9)
        h.addWidget(btn("مەسروفی نوێ", self.add_exp, "primary"))
        h.addWidget(btn("سڕینەوە", self.rm_exp, "danger"))
        h.addStretch(); v1.addLayout(h)
        self.et = table(["#", "بەروار", "جۆر", "بڕ", "تێبینی"]); v1.addWidget(self.et)
        tabs.addTab(w1, "مەسروفات")

        w2 = QWidget(); v2 = QVBoxLayout(w2); v2.setSpacing(14); v2.setContentsMargins(0, 16, 0, 0)
        h2 = QHBoxLayout(); h2.setSpacing(9)
        h2.addWidget(btn("کارمەندی نوێ", self.add_emp, "primary"))
        h2.addWidget(btn("دانی مووچە", self.pay_sal))
        h2.addWidget(btn("سڕینەوە", self.rm_emp, "danger"))
        h2.addStretch(); v2.addLayout(h2)
        self.mt = table(["#", "ناو", "پۆست", "مووچە", "مۆبایل"]); v2.addWidget(self.mt)
        v2.addWidget(heading("مووچە دراوەکان"))
        self.st = table(["بەروار", "کارمەند", "بڕ", "تێبینی"]); v2.addWidget(self.st)
        tabs.addTab(w2, "کارمەندان و مووچە")

    def refresh(self):
        fill(self.et, [(r["id"], r["date"], r["category"], fmt(r["amount"]), r["note"] or "—")
                       for r in db.q("SELECT * FROM expenses ORDER BY id DESC LIMIT 300")])
        fill(self.mt, [(r["id"], r["name"], r["position"] or "—", fmt(r["salary"]), r["phone"] or "—")
                       for r in db.q("SELECT * FROM employees ORDER BY name")])
        fill(self.st, [(r["date"], r["n"], fmt(r["amount"]), r["note"] or "—")
                       for r in db.q("SELECT s.*, e.name n FROM salaries s "
                                     "JOIN employees e ON e.id=s.employee_id ORDER BY s.id DESC LIMIT 200")])

    def add_exp(self):
        d = dialog(self, "مەسروف"); f = QFormLayout(d); f.setSpacing(12)
        dt, cat, am, nt = date_edit(), combo(), num(), QLineEdit()
        cat.addItems(self.CATS); cat.setEditable(True)
        f.addRow("بەروار", dt); f.addRow("جۆر", cat); f.addRow("بڕ", am); f.addRow("تێبینی", nt)
        dlg_buttons(d, f)
        if d.exec() and am.value() > 0:
            db.x("INSERT INTO expenses(date,category,amount,note) VALUES(?,?,?,?)",
                 (dt.date().toString("yyyy-MM-dd"), cat.currentText(), am.value(), nt.text()))
            self.app.refresh_all()

    def rm_exp(self):
        i = picked_id(self.et)
        if not i: return msg(self, "سەرەتا ڕیزێک هەڵبژێرە")
        if ask(self, "بسڕدرێتەوە؟"):
            db.x("DELETE FROM expenses WHERE id=?", (i,)); self.app.refresh_all()

    def add_emp(self):
        d = dialog(self, "کارمەند"); f = QFormLayout(d); f.setSpacing(12)
        n, p, s, ph = QLineEdit(), QLineEdit(), num(), QLineEdit()
        f.addRow("ناو", n); f.addRow("پۆست", p)
        f.addRow("مووچەی مانگانە", s); f.addRow("مۆبایل", ph)
        dlg_buttons(d, f)
        if d.exec() and n.text().strip():
            db.x("INSERT INTO employees(name,position,salary,phone) VALUES(?,?,?,?)",
                 (n.text().strip(), p.text(), s.value(), ph.text()))
            self.app.refresh_all()

    def rm_emp(self):
        i = picked_id(self.mt)
        if not i: return msg(self, "سەرەتا کارمەندێک هەڵبژێرە")
        if ask(self, "بسڕدرێتەوە؟"):
            db.x("DELETE FROM employees WHERE id=?", (i,)); self.app.refresh_all()

    def pay_sal(self):
        i = picked_id(self.mt)
        if not i: return msg(self, "سەرەتا کارمەندێک هەڵبژێرە")
        e = db.one("SELECT * FROM employees WHERE id=?", (i,))
        d = dialog(self, f"مووچە — {e['name']}"); f = QFormLayout(d); f.setSpacing(12)
        dt, am, nt = date_edit(), num(), QLineEdit(); am.setValue(e["salary"])
        f.addRow("بەروار", dt); f.addRow("بڕ", am); f.addRow("تێبینی", nt)
        dlg_buttons(d, f)
        if d.exec() and am.value() > 0:
            db.x("INSERT INTO salaries(date,employee_id,amount,note) VALUES(?,?,?,?)",
                 (dt.date().toString("yyyy-MM-dd"), i, am.value(), nt.text()))
            self.app.refresh_all()


# ---------------------------------------------------------------- ڕاپۆرت
class Reports(QWidget):
    def __init__(self, app):
        super().__init__(); self.app = app
        v = QVBoxLayout(self); v.setSpacing(14); v.setContentsMargins(0, 0, 0, 0)
        h = QHBoxLayout(); h.setSpacing(9)
        self.f = date_edit(); self.f.setDate(QDate.currentDate().addDays(-30))
        self.t = date_edit()
        h.addWidget(QLabel("لە")); h.addWidget(self.f)
        h.addWidget(QLabel("بۆ")); h.addWidget(self.t)
        h.addWidget(btn("پیشاندانی ڕاپۆرت", self.run, "primary"))
        h.addWidget(btn("هەناردەکردن بۆ CSV", self.csv))
        h.addStretch(); v.addLayout(h)
        self.out = QTextBrowser(); v.addWidget(self.out)

    def refresh(self): pass

    def run(self):
        a, b = self.f.date().toString("yyyy-MM-dd"), self.t.date().toString("yyyy-MM-dd")
        cur = db.get("currency")
        prod = db.one("SELECT IFNULL(SUM(total),0) t, IFNULL(SUM(qty),0) q, COUNT(*) c, "
                      "IFNULL(SUM(mat_cost),0) mat, IFNULL(SUM(labor),0) lab, "
                      "IFNULL(SUM(overhead),0) ovh FROM production "
                      "WHERE date BETWEEN ? AND ?", (a, b))
        exp = db.one("SELECT IFNULL(SUM(amount),0) t FROM expenses WHERE date BETWEEN ? AND ?", (a, b))["t"]
        sal = db.one("SELECT IFNULL(SUM(amount),0) t FROM salaries WHERE date BETWEEN ? AND ?", (a, b))["t"]
        pur = db.one("SELECT IFNULL(SUM(qty*price),0) t FROM purchases WHERE date BETWEEN ? AND ?", (a, b))["t"]
        out = db.one("SELECT IFNULL(SUM(qty),0) q, IFNULL(SUM(qty*cost),0) v FROM dispatch "
                     "WHERE date BETWEEN ? AND ?", (a, b))
        unit = prod["t"] / prod["q"] if prod["q"] else 0

        per_item = db.q("SELECT it.name n, SUM(p.qty) q, SUM(p.total) t FROM production p "
                        "JOIN items it ON it.id=p.item_id WHERE p.date BETWEEN ? AND ? "
                        "GROUP BY it.id ORDER BY t DESC LIMIT 10", (a, b))
        used = db.q("SELECT it.name n, SUM(pi.qty) q, SUM(pi.qty*pi.cost) v FROM prod_inputs pi "
                    "JOIN production p ON p.id=pi.prod_id JOIN items it ON it.id=pi.item_id "
                    "WHERE p.date BETWEEN ? AND ? GROUP BY it.id ORDER BY v DESC LIMIT 10", (a, b))
        low = db.q("SELECT * FROM items WHERE minq>0 AND qty<=minq")

        th = (f"background:{HEADER_BG};color:{MUTED};padding:10px;"
              f"text-align:right;font-weight:600;")
        td = f"padding:10px;border-bottom:1px solid {ROW_LINE};text-align:right;"

        def line(label, value, strong=False, accent=None):
            c = accent or (TEXT if strong else MUTED)
            w = "700" if strong else "400"
            return (f"<tr><td style='{td}color:{MUTED};'>{label}</td>"
                    f"<td style='{td}text-align:left;color:{c};font-weight:{w};'>{value}</td></tr>")

        items = "".join(f"<tr><td style='{td}'>{r['n']}</td><td style='{td}'>{fmt(r['q'])}</td>"
                        f"<td style='{td}'>{fmt(r['t'])}</td>"
                        f"<td style='{td}'>{fmt(r['t']/r['q'] if r['q'] else 0)}</td></tr>"
                        for r in per_item) or \
                f"<tr><td style='{td}' colspan='4'>هیچ بەرهەمهێنانێک نییە</td></tr>"
        mats = "".join(f"<tr><td style='{td}'>{r['n']}</td><td style='{td}'>{fmt(r['q'])}</td>"
                       f"<td style='{td}'>{fmt(r['v'])}</td></tr>" for r in used) or \
               f"<tr><td style='{td}' colspan='3'>هیچ مادەیەک بەکارنەهاتووە</td></tr>"
        lows = "".join(f"<tr><td style='{td}'>{r['name']}</td>"
                       f"<td style='{td}color:{RED};'>{fmt(r['qty'])}</td>"
                       f"<td style='{td}'>{fmt(r['minq'])}</td></tr>" for r in low) or \
               f"<tr><td style='{td}' colspan='3'>هیچ کاڵایەک کەم نەبووە</td></tr>"

        self.out.setHtml(f"""
        <div dir="rtl" style="font-family:'Segoe UI',Tahoma;font-size:14px;color:{TEXT};">
        <div style="color:{GOLD};font-size:19px;font-weight:700;margin-bottom:4px;">
            ڕاپۆرتی کارگە</div>
        <div style="color:{MUTED};font-size:12px;margin-bottom:18px;">
            {lrm(a)} &nbsp;تا&nbsp; {lrm(b)}</div>

        <table width="100%" cellspacing="0" cellpadding="0">
        {line(f"بەچەکانی بەرهەمهێنان", f"{prod['c']}", True)}
        {line("کۆی بڕی بەرهەمهاتوو", fmt(prod['q']), True)}
        {line("تێچووی مادەی خام", f"{fmt(prod['mat'])} {cur}")}
        {line("مووچەی کرێکاران لە بەچەکاندا", f"{fmt(prod['lab'])} {cur}")}
        {line("تێچووی گشتی لە بەچەکاندا", f"{fmt(prod['ovh'])} {cur}")}
        {line("کۆی تێچووی بەرهەمهێنان", f"{fmt(prod['t'])} {cur}", True)}
        {line("تێچووی ناوەندی یەک یەکە", f"{fmt(unit)} {cur}", True, GOLD_HI)}
        {line("کڕینی مادەی خام", f"{fmt(pur)} {cur}")}
        {line("مەسروفاتی دەرەوەی بەچەکان", f"{fmt(exp)} {cur}")}
        {line("مووچەی دەرەوەی بەچەکان", f"{fmt(sal)} {cur}")}
        {line("دەرچوو", f"{fmt(out['q'])} یەکە · {fmt(out['v'])} {cur}", True)}
        </table>

        <div style="color:{GOLD};font-size:15px;font-weight:600;margin:26px 0 8px 0;">
            بەرهەمهێنان بەپێی کاڵا</div>
        <table width="100%" cellspacing="0" cellpadding="0">
        <tr><th style="{th}">بەرهەم</th><th style="{th}">بڕ</th>
            <th style="{th}">کۆی تێچوو</th><th style="{th}">تێچووی یەکە</th></tr>
        {items}</table>

        <div style="color:{GOLD};font-size:15px;font-weight:600;margin:26px 0 8px 0;">
            مادەی خامی بەکارهاتوو</div>
        <table width="100%" cellspacing="0" cellpadding="0">
        <tr><th style="{th}">مادە</th><th style="{th}">بڕ</th><th style="{th}">بەها</th></tr>
        {mats}</table>

        <div style="color:{GOLD};font-size:15px;font-weight:600;margin:26px 0 8px 0;">
            کاڵای کەمبوو</div>
        <table width="100%" cellspacing="0" cellpadding="0">
        <tr><th style="{th}">کاڵا</th><th style="{th}">بڕی ماوە</th><th style="{th}">کەمترین بڕ</th></tr>
        {lows}</table>
        </div>""")

    def csv(self):
        import csv as _csv
        p = QFileDialog.getExistingDirectory(self, "فۆڵدەری پاشەکەوت", APP_DIR)
        if not p: return
        with open(os.path.join(p, "inventory.csv"), "w", newline="", encoding="utf-8-sig") as f:
            w = _csv.writer(f); w.writerow(["ناو", "جۆر", "یەکە", "بڕ", "تێچوو"])
            for r in db.q("SELECT * FROM items"):
                w.writerow([r["name"], r["kind"], r["unit"], r["qty"], r["cost"]])
        with open(os.path.join(p, "production.csv"), "w", newline="", encoding="utf-8-sig") as f:
            w = _csv.writer(f)
            w.writerow(["بەروار", "بەرهەم", "بڕ", "مادە", "مووچە", "گشتی", "کۆ", "تێچووی یەکە"])
            for r in db.q("SELECT p.*, it.name n FROM production p "
                          "JOIN items it ON it.id=p.item_id ORDER BY p.date"):
                w.writerow([r["date"], r["n"], r["qty"], r["mat_cost"], r["labor"],
                            r["overhead"], r["total"],
                            r["total"] / r["qty"] if r["qty"] else 0])
        msg(self, "هەناردەکرا بۆ:\n" + p)


# ---------------------------------------------------------------- ڕێکخستن
class Settings(QWidget):
    def __init__(self, app):
        super().__init__(); self.app = app
        outer = QVBoxLayout(self); outer.setContentsMargins(0, 0, 0, 0)
        row = QHBoxLayout(); row.setSpacing(16)

        g = QGroupBox("زانیاری کارگە"); f = QFormLayout(g); f.setSpacing(12)
        self.co, self.ph, self.ad = QLineEdit(), QLineEdit(), QLineEdit()
        self.cu, self.usd = QLineEdit(), num(1e6, 2)
        f.addRow("ناوی کارگە", self.co); f.addRow("مۆبایل", self.ph)
        f.addRow("ناونیشان", self.ad); f.addRow("دراو", self.cu)
        f.addRow("نرخی دۆلار", self.usd)
        f.addRow(btn("پاشەکەوتکردن", self.save, "primary"))
        row.addWidget(g, 1)

        g3 = QGroupBox("شوێنی داتابەیس"); f3 = QVBoxLayout(g3); f3.setSpacing(10)
        self.dbl = QLabel(); self.dbl.setWordWrap(True); self.dbl.setObjectName("hint")
        f3.addWidget(self.dbl)
        dh = QLabel("ئەگەر دەتەوێت چەند کۆمپیوتەرێکی کارگە هەمان داتا بەکاربهێنن، "
                    "لە هەموویان هەمان فۆڵدەری هاوبەش دیاری بکە.")
        dh.setWordWrap(True); dh.setObjectName("hint"); f3.addWidget(dh)
        f3.addWidget(btn("گۆڕینی شوێنی داتابەیس", self.move_db))
        f3.addStretch()
        row.addWidget(g3, 1)

        g2 = QGroupBox("باکئەپ و کلاود"); f2 = QVBoxLayout(g2); f2.setSpacing(10)
        self.bl = QLabel(); self.bl.setWordWrap(True); f2.addWidget(self.bl)
        hint = QLabel("فۆڵدەرێکی هاوبەش یان فۆڵدەری کلاودی سەر کۆمپیوتەرەکەت هەڵبژێرە. "
                      "هەر جارێک بەرنامەکە دادەخرێت، کۆپییەک خۆکارانە دەنێردرێت.")
        hint.setWordWrap(True); hint.setObjectName("hint"); f2.addWidget(hint)
        f2.addWidget(btn("هەڵبژاردنی فۆڵدەری باکئەپ", self.pick, "primary"))
        f2.addWidget(btn("باکئەپکردنی ئێستا", self.backup))
        f2.addWidget(btn("گەڕاندنەوەی باکئەپ", self.restore))
        f2.addStretch()
        row.addWidget(g2, 1)

        outer.addLayout(row); outer.addStretch()

    def refresh(self):
        self.co.setText(db.get("company")); self.ph.setText(db.get("phone"))
        self.ad.setText(db.get("address")); self.cu.setText(db.get("currency"))
        self.usd.setValue(float(db.get("usd") or 0))
        p = db.get("backup")
        self.bl.setText(f"فۆڵدەری ئێستا:  {p if p else 'دیارینەکراوە'}")
        self.bl.setStyleSheet(f"color:{GOLD_HI if p else MUTED};font-weight:600;")
        self.dbl.setText(DB_PATH)

    def save(self):
        for k, w in [("company", self.co), ("phone", self.ph),
                     ("address", self.ad), ("currency", self.cu)]:
            db.set(k, w.text())
        db.set("usd", self.usd.value()); self.app.refresh_all(); msg(self, "پاشەکەوتکرا")

    def move_db(self):
        folder = QFileDialog.getExistingDirectory(self, "فۆڵدەری داتابەیس")
        if not folder: return
        target = os.path.join(folder, "factory.db")
        if os.path.abspath(target) == os.path.abspath(DB_PATH):
            return msg(self, "هەمان شوێنە")
        if os.path.exists(target):
            if not ask(self, "لەم فۆڵدەرەدا داتابەیسێک هەیە.\n"
                             "بەکاری بهێنم؟ (داتای ئێستات دەمێنێتەوە لە شوێنی کۆنی خۆی)"):
                return
        else:
            try:
                db.con.commit(); shutil.copy2(DB_PATH, target)
            except Exception as e:
                return msg(self, f"نەتوانرا کۆپی بکرێت:\n{e}")
        save_cfg(db_path=target)
        msg(self, f"شوێنی داتابەیس گۆڕدرا بۆ:\n{target}\n\n"
                  "تکایە بەرنامەکە دابخە و دووبارە بیکەرەوە.")
        QApplication.quit()

    def pick(self):
        p = QFileDialog.getExistingDirectory(self, "فۆڵدەری باکئەپ")
        if p: db.set("backup", p); self.refresh()

    def backup(self):
        p = db.get("backup")
        if not p or not os.path.isdir(p): return msg(self, "سەرەتا فۆڵدەری باکئەپ دیاری بکە")
        name = f"golden_base_{datetime.datetime.now():%Y-%m-%d_%H-%M}.db"
        shutil.copy2(DB_PATH, os.path.join(p, name))
        old = sorted(f for f in os.listdir(p) if f.startswith("golden_base_") and f.endswith(".db"))
        for f in old[:-20]:
            try: os.remove(os.path.join(p, f))
            except Exception: pass
        msg(self, f"باکئەپ درووستکرا:\n{name}")

    def restore(self):
        p, _ = QFileDialog.getOpenFileName(self, "فایلی باکئەپ", db.get("backup") or APP_DIR, "DB (*.db)")
        if not p: return
        if ask(self, "هەموو داتای ئێستا دەگۆڕدرێت بە باکئەپەکە. دڵنیایت؟"):
            db.con.close(); shutil.copy2(p, DB_PATH)
            msg(self, "گەڕێندرایەوە. تکایە بەرنامەکە دووبارە بکەرەوە")
            QApplication.quit()


# ---------------------------------------------------------------- پەنجەرەی سەرەکی
class Main(QMainWindow):
    PAGES = [
        ("dash", "داشبۆرد",          "پوختەی کارگەکە لە یەک ڕوانیندا"),
        ("inv",  "مەخزەن",           "مادەی خام و بەرهەمە تەواوەکان"),
        ("prod", "بەرهەمهێنان",      "تۆماری بەچ و حیسابی تێچووی یەکە"),
        ("disp", "دەرچوون",          "بەرهەمی دەرچوو لە کارگە"),
        ("exp",  "مەسروفات و مووچە", "خەرجییەکان و کرێکاران"),
        ("rep",  "ڕاپۆرت",           "تێچووی بەرهەمهێنان و مادەی بەکارهاتوو"),
        ("st",   "ڕێکخستن",          "زانیاری کارگە و باکئەپ"),
    ]

    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.resize(1360, 850); self.setMinimumSize(1120, 700)

        self.dash = Dashboard(); self.inv = Inventory(self); self.prod = Production(self)
        self.disp = Dispatch(self); self.exp = Expenses(self)
        self.rep = Reports(self); self.st = Settings(self)

        root = QWidget(); root.setObjectName("root")
        row = QHBoxLayout(root); row.setContentsMargins(0, 0, 0, 0); row.setSpacing(0)
        row.addWidget(self._sidebar())

        right = QWidget(); rv = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0); rv.setSpacing(0)
        rv.addWidget(self._header())

        self.stack = QStackedWidget()
        holder = QWidget(); hv = QVBoxLayout(holder)
        hv.setContentsMargins(26, 22, 26, 26); hv.addWidget(self.stack)
        for k, _, _ in self.PAGES:
            self.stack.addWidget(getattr(self, k))
        rv.addWidget(holder)
        row.addWidget(right, 1)

        self.setCentralWidget(root)
        self.nav[0].setChecked(True)
        self.go(0)
        self.apply_theme()

    def _sidebar(self):
        bar = QFrame(); bar.setObjectName("sidebar"); bar.setFixedWidth(238)
        v = QVBoxLayout(bar); v.setContentsMargins(16, 24, 16, 20); v.setSpacing(4)
        self.brand = QLabel(); self.brand.setObjectName("brand")
        self.brand.setWordWrap(True)
        sub_l = QLabel("کارگەی ڕۆن"); sub_l.setObjectName("brandSub")
        v.addWidget(self.brand); v.addWidget(sub_l); v.addSpacing(22)
        self.refresh_brand()

        self.nav = []
        for i, (_, name, _) in enumerate(self.PAGES):
            b = QPushButton(name); b.setObjectName("navBtn")
            b.setCheckable(True); b.setAutoExclusive(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda _, n=i: self.go(n))
            self.nav.append(b); v.addWidget(b)

        v.addStretch()
        self.theme_btn = QPushButton(); self.theme_btn.setObjectName("themeBtn")
        self.theme_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.theme_btn.clicked.connect(self.toggle_theme)
        v.addWidget(self.theme_btn); v.addSpacing(10)
        self.foot = QLabel(); self.foot.setObjectName("hint"); self.foot.setWordWrap(True)
        v.addWidget(self.foot)
        return bar

    def _header(self):
        h = QFrame(); h.setObjectName("header"); h.setFixedHeight(84)
        lay = QHBoxLayout(h); lay.setContentsMargins(26, 0, 26, 0)
        col = QVBoxLayout(); col.setSpacing(2)
        self.title = QLabel(); self.title.setObjectName("pageTitle")
        self.sub = QLabel(); self.sub.setObjectName("pageSub")
        col.addWidget(self.title); col.addWidget(self.sub)
        lay.addLayout(col); lay.addStretch()
        self.datelbl = QLabel(); self.datelbl.setObjectName("hint")
        self.datelbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        lay.addWidget(self.datelbl)
        return h

    def toggle_theme(self):
        db.set("theme", "light" if db.get("theme", "dark") == "dark" else "dark")
        self.apply_theme()

    def apply_theme(self):
        theme = db.get("theme", "dark")
        apply_palette(theme)
        QApplication.instance().setStyleSheet(build_qss())
        for card in self.dash.c.values():
            card.restyle()
        self.theme_btn.setText("دۆخی ڕووناک" if theme == "dark" else "دۆخی تاریک")
        self.refresh_all()

    def go(self, i):
        k, name, desc = self.PAGES[i]
        self.stack.setCurrentIndex(i)
        self.title.setText(name); self.sub.setText(desc)
        try: getattr(self, k).refresh()
        except Exception as e: print("refresh error:", e)

    def refresh_brand(self):
        """Show the plant's own name wherever the app identifies itself."""
        name = db.get("company") or "کارگە"
        self.brand.setText(name)
        self.setWindowTitle(f"{name} — {APP_TITLE}")

    def refresh_all(self):
        for k, _, _ in self.PAGES:
            try: getattr(self, k).refresh()
            except Exception as e: print("refresh error:", e)
        self.refresh_brand()
        self.foot.setText(f"{db.get('company')}\nکارگە · وەشانی ١٫٠")
        self.datelbl.setText(lrm(QDate.currentDate().toString("yyyy-MM-dd")))

    def closeEvent(self, e):
        p = db.get("backup")
        if p and os.path.isdir(p):
            try:
                shutil.copy2(DB_PATH, os.path.join(
                    p, f"factory_{datetime.datetime.now():%Y-%m-%d}.db"))
            except Exception:
                pass
        e.accept()


def build_qss():
    """Stylesheet for the palette that is currently active."""
    return f"""
QWidget {{ background:{BG}; color:{TEXT}; font-size:15px; }}
QLabel {{ background:transparent; }}
#root {{ background:{BG}; }}

/* ---------- لای ناڤیگەیشن ---------- */
#sidebar {{ background:{PANEL}; border-left:1px solid {DIVIDER}; }}
#brand {{ color:{GOLD}; font-size:16px; font-weight:700; letter-spacing:3px; }}
#brandSub {{ color:{MUTED}; font-size:13px; }}
#navBtn {{
    background:transparent; border:none; border-radius:14px;
    padding:14px 18px; text-align:right; color:{NAV_FG}; font-size:15px;
}}
#navBtn:hover {{ background:{NAV_HOVER}; color:{TEXT}; }}
#navBtn:checked {{ background:{NAV_ACTIVE}; color:{GOLD_HI}; font-weight:700; }}
#themeBtn {{
    background:transparent; border:1px solid {BTN_BORDER}; border-radius:14px;
    padding:12px 18px; color:{MUTED}; font-size:14px; text-align:center;
}}
#themeBtn:hover {{ background:{NAV_HOVER}; color:{TEXT}; }}

/* ---------- سەرەوە ---------- */
#header {{ background:{BG}; border-bottom:1px solid {DIVIDER}; }}
#pageTitle {{ font-size:25px; font-weight:700; color:{TITLE}; }}
#pageSub {{ color:{MUTED}; font-size:14px; }}
#hint {{ color:{FAINT}; font-size:13px; }}
#secTitle {{ color:{MUTED}; font-size:13px; font-weight:600; letter-spacing:1px; }}
#summary {{ color:{MUTED}; font-size:15px; padding:9px 0; }}

/* ---------- کارتەکان ---------- */
#statCard {{ background:{SURFACE}; border:1px solid {BORDER}; border-radius:20px; }}
#statCap {{ color:{MUTED}; font-size:13px; }}
#statVal {{ color:{TITLE}; font-size:27px; font-weight:700; }}

/* ---------- دوگمەکان ---------- */
QPushButton {{
    background:{BTN}; color:{TEXT}; border:1px solid {BTN_BORDER};
    border-radius:12px; padding:9px 20px; min-height:20px; font-weight:600;
}}
QPushButton:hover {{ background:{BTN_HOVER}; border-color:{BTN_HOVER_BORDER}; }}
QPushButton:pressed {{ background:{BTN_PRESS}; }}
QPushButton#primary {{ background:{GOLD}; color:{ON_GOLD}; border:none; font-weight:700; }}
QPushButton#primary:hover {{ background:{GOLD_HI}; color:{ON_GOLD}; }}
QPushButton#primary:pressed {{ background:{GOLD_PRESS}; }}
QPushButton#danger {{ color:{DANGER_FG}; border-color:{DANGER_BORDER}; }}
QPushButton#danger:hover {{ background:{DANGER_BG}; border-color:{DANGER_BORDER_HI}; }}

/* ---------- خانەکان ---------- */
QLineEdit, QComboBox, QDoubleSpinBox, QDateEdit {{
    background:{FIELD}; border:1px solid {INPUT_BORDER}; border-radius:12px;
    padding:9px 14px; color:{TEXT}; min-height:20px;
    selection-background-color:{GOLD}; selection-color:{ON_GOLD};
}}
QLineEdit:hover, QComboBox:hover, QDoubleSpinBox:hover, QDateEdit:hover {{
    border-color:{BTN_HOVER_BORDER};
}}
QLineEdit:focus, QComboBox:focus, QDoubleSpinBox:focus, QDateEdit:focus {{
    border:2px solid {GOLD}; padding:8px 13px;
}}
QComboBox::drop-down {{ border:none; width:28px; }}
QComboBox QAbstractItemView {{
    background:{MENU_BG}; border:1px solid {INPUT_BORDER}; border-radius:12px;
    padding:6px; outline:none; color:{TEXT};
}}
QComboBox QAbstractItemView::item {{
    min-height:32px; padding:6px 12px; border-radius:8px; color:{TEXT};
}}
QComboBox QAbstractItemView::item:hover {{ background:{NAV_HOVER}; }}
QComboBox QAbstractItemView::item:selected {{
    background:{GOLD}; color:{ON_GOLD}; font-weight:600;
}}
QCalendarWidget QWidget {{ background:{MENU_BG}; }}
QCalendarWidget QAbstractItemView {{
    background:{MENU_BG}; color:{TEXT};
    selection-background-color:{GOLD}; selection-color:{ON_GOLD};
}}

/* ---------- خشتەکان ---------- */
QTableWidget {{
    background:{FIELD}; border:1px solid {BORDER}; border-radius:18px;
    gridline-color:transparent; outline:none;
}}
QTableWidget::item {{ border-bottom:1px solid {ROW_LINE}; padding:9px 8px; }}
QTableWidget::item:selected {{ background:{SEL_BG}; color:{GOLD_HI}; }}
QHeaderView::section {{
    background:{HEADER_BG}; color:{MUTED}; padding:15px 8px; border:none;
    border-bottom:1px solid {INPUT_BORDER}; font-weight:600; font-size:13px;
}}

/* ---------- گرووپ و تاب ---------- */
QGroupBox {{
    background:{SURFACE}; border:1px solid {BORDER}; border-radius:18px;
    margin-top:16px; padding:22px 16px 16px 16px; font-weight:600;
}}
QGroupBox::title {{
    subcontrol-origin:margin; subcontrol-position:top right;
    right:20px; padding:0 10px; color:{GOLD};
}}
QTabWidget::pane {{ border:none; }}
QTabBar::tab {{
    background:transparent; color:{MUTED}; padding:13px 26px;
    border:none; border-bottom:2px solid transparent; margin-left:6px;
}}
QTabBar::tab:hover {{ color:{TEXT}; }}
QTabBar::tab:selected {{ color:{GOLD_HI}; border-bottom:2px solid {GOLD}; font-weight:600; }}

/* ---------- ڕاپۆرت و دیالۆگ ---------- */
QTextBrowser {{
    background:{FIELD}; border:1px solid {BORDER}; border-radius:18px; padding:24px;
}}
#dlg {{ background:{DLG_BG}; }}
QDialog {{ background:{DLG_BG}; }}
QMessageBox {{ background:{DLG_BG}; }}
QMessageBox QLabel {{ color:{TEXT}; }}
QMessageBox QPushButton {{ min-width:100px; }}

/* ---------- سکڕۆڵ ---------- */
QScrollBar:vertical {{ background:transparent; width:12px; margin:5px; }}
QScrollBar::handle:vertical {{ background:{SCROLL}; border-radius:6px; min-height:40px; }}
QScrollBar::handle:vertical:hover {{ background:{SCROLL_HI}; }}
QScrollBar:horizontal {{ background:transparent; height:12px; margin:5px; }}
QScrollBar::handle:horizontal {{ background:{SCROLL}; border-radius:6px; min-width:40px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height:0; width:0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background:transparent; }}
"""


def first_run():
    """Ask for the plant's own details the first time the app is opened."""
    d = QDialog(); d.setObjectName("dlg")
    d.setWindowTitle("بەخێربێیت")
    d.setMinimumWidth(460)
    v = QVBoxLayout(d); v.setSpacing(14); v.setContentsMargins(26, 24, 26, 22)

    t = QLabel("ناوی کارگەکەت بنووسە")
    t.setStyleSheet(f"color:{TITLE};font-size:20px;font-weight:700;")
    v.addWidget(t)
    h = QLabel("ئەم ناوە لە سەرەوەی بەرنامەکە و لەسەر ڕاپۆرتەکان دەردەکەوێت. "
               "دواتر دەتوانیت لە بەشی ڕێکخستن بیگۆڕیت.")
    h.setWordWrap(True); h.setObjectName("hint"); v.addWidget(h)

    f = QFormLayout(); f.setSpacing(11)
    co, ph, ad = QLineEdit(), QLineEdit(), QLineEdit()
    co.setPlaceholderText("پێویستە")
    f.addRow("ناوی کارگە", co)
    f.addRow("مۆبایل", ph)
    f.addRow("ناونیشان", ad)
    v.addLayout(f)

    ok = btn("دەستپێکردن", kind="primary")
    ok.setEnabled(False)
    co.textChanged.connect(lambda s: ok.setEnabled(bool(s.strip())))
    ok.clicked.connect(d.accept)
    co.returnPressed.connect(lambda: ok.isEnabled() and d.accept())
    v.addWidget(ok)

    if d.exec() and co.text().strip():
        db.set("company", co.text().strip())
        db.set("phone", ph.text().strip())
        db.set("address", ad.text().strip())


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    for fam in ["Segoe UI", "Tahoma", "Arial"]:
        f = QFont(fam, 10)
        if f.exactMatch() or fam == "Arial":
            app.setFont(f); break
    apply_palette(db.get("theme", "dark"))
    app.setStyleSheet(build_qss())

    if not db.get("company"):
        first_run()

    w = Main(); w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
