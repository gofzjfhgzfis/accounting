# -*- coding: utf-8 -*-
"""
سیستەمی حیساباتی دووکانی جوملە
"""
import sys, os, re, sqlite3, shutil, datetime, configparser

from PyQt6.QtCore import Qt, QDate, QSizeF, QMarginsF
from PyQt6.QtGui import QFont, QColor, QTextDocument, QPageSize, QPageLayout
from PyQt6.QtPrintSupport import QPrinter
from PyQt6.QtWidgets import *

APP_TITLE = "سیستەمی دووکانی جوملە"
APP_DIR   = os.path.join(os.path.expanduser("~"), "OilShopAccounting")
os.makedirs(APP_DIR, exist_ok=True)

# Data saved under the folder this app used to have is carried over once,
# so renaming the app does not look like the records disappeared.
_OLD_DIR = os.path.join(os.path.expanduser("~"), "GoldenBaseShop")
if os.path.isdir(_OLD_DIR):
    for _old, _new in [("config.ini", "config.ini"), ("golden_shop.db", "oil_shop.db")]:
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

DB_PATH = _cfg["app"].get("db_path", "") or os.path.join(APP_DIR, "oil_shop.db")


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
CREATE TABLE IF NOT EXISTS customers(
    id INTEGER PRIMARY KEY, name TEXT, phone TEXT, address TEXT, note TEXT);
CREATE TABLE IF NOT EXISTS items(
    id INTEGER PRIMARY KEY, name TEXT, kind TEXT, unit TEXT,
    qty REAL DEFAULT 0, cost REAL DEFAULT 0, price REAL DEFAULT 0, minq REAL DEFAULT 0);
CREATE TABLE IF NOT EXISTS invoices(
    id INTEGER PRIMARY KEY, date TEXT, customer_id INTEGER,
    subtotal REAL, discount REAL, total REAL, paid REAL, note TEXT);
CREATE TABLE IF NOT EXISTS invoice_items(
    id INTEGER PRIMARY KEY, invoice_id INTEGER, item_id INTEGER,
    qty REAL, price REAL, cost REAL);
CREATE TABLE IF NOT EXISTS payments(
    id INTEGER PRIMARY KEY, date TEXT, customer_id INTEGER, amount REAL, note TEXT);
CREATE TABLE IF NOT EXISTS purchases(
    id INTEGER PRIMARY KEY, date TEXT, supplier TEXT, item_id INTEGER,
    qty REAL, price REAL, note TEXT);
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

    def balance(self, cid):
        inv = self.one("SELECT IFNULL(SUM(total),0) t, IFNULL(SUM(paid),0) p "
                       "FROM invoices WHERE customer_id=?", (cid,))
        pay = self.one("SELECT IFNULL(SUM(amount),0) a FROM payments WHERE customer_id=?", (cid,))
        return inv["t"] - inv["p"] - pay["a"]


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
    SPECS = [("فرۆشتنی ئەمڕۆ", "GREEN"), ("فرۆشتنی ئەم مانگە", "BLUE"),
             ("کۆی قەرزی کڕیاران", "RED"), ("بەهای مەخزەن", "VIOLET"),
             ("قازانجی ئەم مانگە", "GOLD"), ("کاڵای کەمبوو", "ORANGE")]

    def __init__(self):
        super().__init__()
        v = QVBoxLayout(self); v.setSpacing(18); v.setContentsMargins(0, 0, 0, 0)
        g = QGridLayout(); g.setSpacing(14)
        self.c = {}
        for i, (cap, accent) in enumerate(self.SPECS):
            card = StatCard(cap, accent); self.c[cap] = card
            g.addWidget(card, i // 3, i % 3)
        v.addLayout(g)
        v.addWidget(heading("گەورەترین قەرزداران"))
        self.tbl = table(["کڕیار", "قەرز"]); fit(self.tbl, 0)
        v.addWidget(self.tbl)

    def refresh(self):
        cur = db.get("currency")
        m = today()[:7]
        s1 = db.one("SELECT IFNULL(SUM(total),0) t FROM invoices WHERE date=?", (today(),))["t"]
        s2 = db.one("SELECT IFNULL(SUM(total),0) t FROM invoices WHERE date LIKE ?", (m + "%",))["t"]
        stock = db.one("SELECT IFNULL(SUM(qty*cost),0) t FROM items")["t"]
        low = db.one("SELECT COUNT(*) c FROM items WHERE qty<=minq AND minq>0")["c"]
        cogs = db.one("SELECT IFNULL(SUM(ii.qty*ii.cost),0) t FROM invoice_items ii "
                      "JOIN invoices i ON i.id=ii.invoice_id WHERE i.date LIKE ?", (m + "%",))["t"]
        exp = db.one("SELECT IFNULL(SUM(amount),0) t FROM expenses WHERE date LIKE ?", (m + "%",))["t"]
        sal = db.one("SELECT IFNULL(SUM(amount),0) t FROM salaries WHERE date LIKE ?", (m + "%",))["t"]
        debts = sum(max(db.balance(c["id"]), 0) for c in db.q("SELECT id FROM customers"))

        self.c["فرۆشتنی ئەمڕۆ"].set(f"{fmt(s1)} {cur}")
        self.c["فرۆشتنی ئەم مانگە"].set(f"{fmt(s2)} {cur}")
        self.c["کۆی قەرزی کڕیاران"].set(f"{fmt(debts)} {cur}")
        self.c["بەهای مەخزەن"].set(f"{fmt(stock)} {cur}")
        self.c["قازانجی ئەم مانگە"].set(f"{fmt(s2 - cogs - exp - sal)} {cur}")
        self.c["کاڵای کەمبوو"].set(str(low))

        rows = []
        for c in db.q("SELECT id,name FROM customers"):
            bal = db.balance(c["id"])
            if bal > 0: rows.append((c["name"], bal))
        rows.sort(key=lambda r: -r[1])
        fill(self.tbl, [(n, fmt(bal)) for n, bal in rows[:12]])


# ---------------------------------------------------------------- کڕیاران
class Customers(QWidget):
    def __init__(self, app):
        super().__init__(); self.app = app
        v = QVBoxLayout(self); v.setSpacing(14); v.setContentsMargins(0, 0, 0, 0)
        top = QHBoxLayout(); top.setSpacing(9)
        self.search = QLineEdit(); self.search.setPlaceholderText("گەڕان بە ناو یان مۆبایل…")
        self.search.setMinimumWidth(230)
        self.search.textChanged.connect(self.refresh)
        top.addWidget(btn("کڕیاری نوێ", self.add, "primary"))
        top.addWidget(btn("دەستکاری", self.edit))
        top.addWidget(btn("وەرگرتنی پارە", self.pay))
        top.addWidget(btn("کەشف حساب", self.statement))
        top.addWidget(btn("سڕینەوە", self.rm, "danger"))
        top.addStretch(); top.addWidget(self.search)
        v.addLayout(top)
        self.tbl = table(["#", "ناو", "مۆبایل", "ناونیشان", "قەرز"])
        v.addWidget(self.tbl)

    def refresh(self):
        s = f"%{self.search.text()}%"
        rows = db.q("SELECT * FROM customers WHERE name LIKE ? OR IFNULL(phone,'') LIKE ? ORDER BY name",
                    (s, s))
        fill(self.tbl, [(r["id"], r["name"], r["phone"] or "—", r["address"] or "—",
                         fmt(db.balance(r["id"]))) for r in rows])

    def form(self, r=None):
        d = dialog(self, "کڕیار"); f = QFormLayout(d); f.setSpacing(12)
        name, ph, ad, nt = QLineEdit(), QLineEdit(), QLineEdit(), QLineEdit()
        if r:
            name.setText(r["name"]); ph.setText(r["phone"] or "")
            ad.setText(r["address"] or ""); nt.setText(r["note"] or "")
        f.addRow("ناو", name); f.addRow("مۆبایل", ph)
        f.addRow("ناونیشان", ad); f.addRow("تێبینی", nt)
        dlg_buttons(d, f)
        if d.exec() and name.text().strip():
            return name.text().strip(), ph.text(), ad.text(), nt.text()
        return None

    def add(self):
        v = self.form()
        if v:
            db.x("INSERT INTO customers(name,phone,address,note) VALUES(?,?,?,?)", v)
            self.app.refresh_all()

    def edit(self):
        cid = picked_id(self.tbl)
        if not cid: return msg(self, "سەرەتا کڕیارێک هەڵبژێرە")
        v = self.form(db.one("SELECT * FROM customers WHERE id=?", (cid,)))
        if v:
            db.x("UPDATE customers SET name=?,phone=?,address=?,note=? WHERE id=?", (*v, cid))
            self.app.refresh_all()

    def rm(self):
        cid = picked_id(self.tbl)
        if not cid: return msg(self, "سەرەتا کڕیارێک هەڵبژێرە")
        if db.one("SELECT COUNT(*) c FROM invoices WHERE customer_id=?", (cid,))["c"]:
            return msg(self, "ناتوانرێت بسڕدرێتەوە — پسووڵەی تۆمارکراوی هەیە")
        if ask(self, "دڵنیایت لە سڕینەوە؟"):
            db.x("DELETE FROM customers WHERE id=?", (cid,)); self.app.refresh_all()

    def pay(self):
        cid = picked_id(self.tbl)
        if not cid: return msg(self, "سەرەتا کڕیارێک هەڵبژێرە")
        d = dialog(self, "وەرگرتنی پارە"); f = QFormLayout(d); f.setSpacing(12)
        dt, am, nt = date_edit(), num(), QLineEdit()
        cur = QLabel(f"{fmt(db.balance(cid))} {db.get('currency')}")
        cur.setStyleSheet(f"color:{GOLD_HI};font-size:18px;font-weight:700;")
        f.addRow("قەرزی ئێستا", cur)
        f.addRow("بەروار", dt); f.addRow("بڕی پارە", am); f.addRow("تێبینی", nt)
        dlg_buttons(d, f)
        if d.exec() and am.value() > 0:
            db.x("INSERT INTO payments(date,customer_id,amount,note) VALUES(?,?,?,?)",
                 (dt.date().toString("yyyy-MM-dd"), cid, am.value(), nt.text()))
            self.app.refresh_all()

    def statement(self):
        cid = picked_id(self.tbl)
        if not cid: return msg(self, "سەرەتا کڕیارێک هەڵبژێرە")
        c = db.one("SELECT * FROM customers WHERE id=?", (cid,))
        rows = []
        for i in db.q("SELECT * FROM invoices WHERE customer_id=? ORDER BY date", (cid,)):
            rows.append((i["date"], f"پسووڵە #{i['id']}", fmt(i["total"]), fmt(i["paid"])))
        for p in db.q("SELECT * FROM payments WHERE customer_id=? ORDER BY date", (cid,)):
            rows.append((p["date"], "وەرگرتنی پارە", "—", fmt(p["amount"])))
        rows.sort(key=lambda r: r[0])
        d = dialog(self, f"کەشف حساب — {c['name']}", 720); d.resize(720, 500)
        v = QVBoxLayout(d); v.setSpacing(14)
        t = table(["بەروار", "جۆر", "قەرز", "پارەدان"]); fill(t, rows)
        v.addWidget(t)
        lbl = QLabel(f"ماوە:  {fmt(db.balance(cid))} {db.get('currency')}")
        lbl.setStyleSheet(f"color:{GOLD_HI};font-size:19px;font-weight:700;")
        v.addWidget(lbl)
        d.exec()


# ---------------------------------------------------------------- مەخزەن
class Inventory(QWidget):
    def __init__(self, app):
        super().__init__(); self.app = app
        v = QVBoxLayout(self); v.setSpacing(14); v.setContentsMargins(0, 0, 0, 0)
        top = QHBoxLayout(); top.setSpacing(9)
        top.addWidget(btn("کاڵای نوێ", self.add, "primary"))
        top.addWidget(btn("دەستکاری", self.edit))
        top.addWidget(btn("کڕین / زیادکردنی بڕ", self.purchase))
        top.addWidget(btn("سڕینەوە", self.rm, "danger"))
        top.addStretch()
        self.search = QLineEdit(); self.search.setPlaceholderText("گەڕان بە ناوی کاڵا…")
        self.search.setMinimumWidth(220)
        self.search.textChanged.connect(self.refresh)
        top.addWidget(self.search); v.addLayout(top)
        self.tbl = table(["#", "ناو", "یەکە", "بڕ", "تێچوو/یەکە", "نرخی فرۆشتن", "کەمترین بڕ"])
        v.addWidget(self.tbl)

    def refresh(self):
        q = f"%{self.search.text()}%"
        rows = db.q("SELECT * FROM items WHERE name LIKE ? ORDER BY name", (q,))
        fill(self.tbl, [(r["id"], r["name"], r["unit"] or "—", fmt(r["qty"]),
                         fmt(r["cost"]), fmt(r["price"]), fmt(r["minq"])) for r in rows])
        for i, r in enumerate(rows):
            if r["minq"] and r["qty"] <= r["minq"]:
                for j in range(self.tbl.columnCount()):
                    self.tbl.item(i, j).setForeground(QColor(RED))

    def form(self, r=None):
        d = dialog(self, "کاڵا"); f = QFormLayout(d); f.setSpacing(12)
        name = QLineEdit()
        unit = QLineEdit(); unit.setPlaceholderText("لیتر / کارتۆن / کیلۆ")
        cost, price, minq = num(dec=2), num(dec=2), num(dec=2)
        if r:
            name.setText(r["name"]); unit.setText(r["unit"] or "")
            cost.setValue(r["cost"]); price.setValue(r["price"]); minq.setValue(r["minq"])
        f.addRow("ناو", name); f.addRow("یەکە", unit)
        f.addRow("تێچووی یەکە", cost); f.addRow("نرخی فرۆشتن", price)
        f.addRow("کەمترین بڕ", minq)
        dlg_buttons(d, f)
        if d.exec() and name.text().strip():
            return (name.text().strip(), unit.text(),
                    cost.value(), price.value(), minq.value())
        return None

    def add(self):
        v = self.form()
        if v:
            db.x("INSERT INTO items(name,unit,cost,price,minq) VALUES(?,?,?,?,?)", v)
            self.app.refresh_all()

    def edit(self):
        i = picked_id(self.tbl)
        if not i: return msg(self, "سەرەتا کاڵایەک هەڵبژێرە")
        v = self.form(db.one("SELECT * FROM items WHERE id=?", (i,)))
        if v:
            db.x("UPDATE items SET name=?,unit=?,cost=?,price=?,minq=? WHERE id=?", (*v, i))
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


# ---------------------------------------------------------------- فرۆشتن
class Sales(QWidget):
    def __init__(self, app):
        super().__init__(); self.app = app
        self.lines = []
        main = QHBoxLayout(self); main.setSpacing(16); main.setContentsMargins(0, 0, 0, 0)

        box = QGroupBox("پسووڵەی نوێ"); fl = QVBoxLayout(box); fl.setSpacing(12)
        f = QFormLayout(); f.setSpacing(11)
        self.cust = combo(); self.dt = date_edit()
        f.addRow("کڕیار", self.cust); f.addRow("بەروار", self.dt)
        fl.addLayout(f)

        fl.addWidget(heading("زیادکردنی کاڵا"))
        add = QGridLayout(); add.setSpacing(9)
        self.item = combo()
        self.item.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.item.currentIndexChanged.connect(self.autoprice)
        self.qty = num(dec=2); self.qty.setValue(1)
        self.pr = num(dec=2)
        add.addWidget(QLabel("کاڵا"), 0, 0)
        add.addWidget(self.item, 0, 1, 1, 3)
        add.addWidget(QLabel("بڕ"), 1, 0); add.addWidget(self.qty, 1, 1)
        add.addWidget(QLabel("نرخ"), 1, 2); add.addWidget(self.pr, 1, 3)
        add.addWidget(btn("زیادکردن", self.add_line), 2, 1, 1, 3)
        fl.addLayout(add)

        self.lt = table(["کاڵا", "بڕ", "نرخ", "کۆ"]); fit(self.lt, 0)
        fl.addWidget(self.lt)
        fl.addWidget(btn("لابردنی ڕیزی هەڵبژێردراو", self.rm_line, "danger"))

        f2 = QFormLayout(); f2.setSpacing(11)
        self.disc, self.paid, self.note = num(dec=2), num(dec=2), QLineEdit()
        self.disc.valueChanged.connect(self.calc)
        self.total_lbl = QLabel("0")
        self.restyle()
        f2.addRow("داشکاندن", self.disc); f2.addRow("پارەی دراو", self.paid)
        f2.addRow("تێبینی", self.note); f2.addRow("کۆی گشتی", self.total_lbl)
        fl.addLayout(f2)
        fl.addWidget(btn("تۆمارکردنی پسووڵە", self.save, "primary"))
        main.addWidget(box, 5)

        box2 = QGroupBox("پسووڵە تۆمارکراوەکان"); v2 = QVBoxLayout(box2); v2.setSpacing(12)
        self.tbl = table(["#", "بەروار", "کڕیار", "کۆ", "ماوە"]); fit(self.tbl, 2)
        self.tbl.setColumnWidth(2, 120)
        self.tbl.setWordWrap(False)
        self.tbl.setTextElideMode(Qt.TextElideMode.ElideRight)
        v2.addWidget(self.tbl)
        h = QHBoxLayout(); h.setSpacing(9)
        h.addWidget(btn("هەناردەکردن بۆ PDF", self.pdf, "primary"))
        h.addWidget(btn("سڕینەوەی پسووڵە", self.rm_inv, "danger"))
        v2.addLayout(h)
        main.addWidget(box2, 4)

    def restyle(self):
        self.total_lbl.setStyleSheet(
            f"color:{GOLD_HI};font-size:26px;font-weight:700;")

    def refresh(self):
        self.cust.clear()
        for c in db.q("SELECT id,name FROM customers ORDER BY name"):
            self.cust.addItem(c["name"], c["id"])
        self.item.clear()
        for i in db.q("SELECT id,name,qty,price FROM items ORDER BY name"):
            self.item.addItem(f"{i['name']}   ·   بڕ {fmt(i['qty'])}", i["id"])
        rows = db.q("SELECT i.*, IFNULL(c.name,'—') cn FROM invoices i "
                    "LEFT JOIN customers c ON c.id=i.customer_id ORDER BY i.id DESC LIMIT 300")
        fill(self.tbl, [(r["id"], r["date"], r["cn"], fmt(r["total"]),
                         fmt(r["total"] - r["paid"])) for r in rows])

    def autoprice(self):
        i = self.item.currentData()
        if i:
            r = db.one("SELECT price FROM items WHERE id=?", (i,))
            if r: self.pr.setValue(r["price"])

    def add_line(self):
        i = self.item.currentData()
        if not i or self.qty.value() <= 0: return
        it = db.one("SELECT * FROM items WHERE id=?", (i,))
        # what is already on this invoice counts against the stock too
        already = sum(l["qty"] for l in self.lines if l["id"] == i)
        if already + self.qty.value() > it["qty"]:
            if not ask(self, f"بڕی مەخزەن تەنها {fmt(it['qty'])}ە. بەردەوام بم؟"): return
        for l in self.lines:
            if l["id"] == i and l["price"] == self.pr.value():
                l["qty"] += self.qty.value()
                break
        else:
            self.lines.append({"id": i, "name": it["name"], "qty": self.qty.value(),
                               "price": self.pr.value(), "cost": it["cost"]})
        self.calc()

    def rm_line(self):
        r = self.lt.currentRow()
        if r >= 0: self.lines.pop(r); self.calc()

    def calc(self):
        fill(self.lt, [(l["name"], fmt(l["qty"]), fmt(l["price"]), fmt(l["qty"] * l["price"]))
                       for l in self.lines])
        sub = sum(l["qty"] * l["price"] for l in self.lines)
        self.total_lbl.setText(f"{fmt(sub - self.disc.value())} {db.get('currency')}")

    def save(self):
        if not self.lines: return msg(self, "هیچ کاڵایەک زیاد نەکراوە")
        if self.cust.currentData() is None: return msg(self, "سەرەتا کڕیارێک زیاد بکە")
        sub = sum(l["qty"] * l["price"] for l in self.lines)
        tot = sub - self.disc.value()
        iid = db.x("INSERT INTO invoices(date,customer_id,subtotal,discount,total,paid,note) "
                   "VALUES(?,?,?,?,?,?,?)",
                   (self.dt.date().toString("yyyy-MM-dd"), self.cust.currentData(),
                    sub, self.disc.value(), tot, self.paid.value(), self.note.text()))
        for l in self.lines:
            db.x("INSERT INTO invoice_items(invoice_id,item_id,qty,price,cost) VALUES(?,?,?,?,?)",
                 (iid, l["id"], l["qty"], l["price"], l["cost"]))
            db.x("UPDATE items SET qty=qty-? WHERE id=?", (l["qty"], l["id"]))
        self.lines = []; self.disc.setValue(0); self.paid.setValue(0); self.note.clear()
        self.calc(); self.app.refresh_all()
        msg(self, f"پسووڵە #{iid} بە سەرکەوتوویی تۆمارکرا")

    def rm_inv(self):
        iid = picked_id(self.tbl)
        if not iid: return msg(self, "سەرەتا پسووڵەیەک هەڵبژێرە")
        if not ask(self, "پسووڵەکە بسڕدرێتەوە؟ بڕەکان دەگەڕێنەوە مەخزەن."): return
        for r in db.q("SELECT * FROM invoice_items WHERE invoice_id=?", (iid,)):
            db.x("UPDATE items SET qty=qty+? WHERE id=?", (r["qty"], r["item_id"]))
        db.x("DELETE FROM invoice_items WHERE invoice_id=?", (iid,))
        db.x("DELETE FROM invoices WHERE id=?", (iid,))
        self.app.refresh_all()

    def pdf(self):
        iid = picked_id(self.tbl)
        if not iid: return msg(self, "سەرەتا پسووڵەیەک هەڵبژێرە")
        inv = db.one("SELECT * FROM invoices WHERE id=?", (iid,))
        cus = db.one("SELECT * FROM customers WHERE id=?", (inv["customer_id"],))
        rows = db.q("SELECT ii.*, it.name FROM invoice_items ii JOIN items it ON it.id=ii.item_id "
                    "WHERE ii.invoice_id=?", (iid,))
        cur = db.get("currency")
        due = inv["total"] - inv["paid"]

        body = ""
        for n, r in enumerate(rows, 1):
            body += (
                f"<tr>"
                f"<td align='center'>{n}</td>"
                f"<td>{r['name']}</td>"
                f"<td align='center'>{fmt(r['qty'])}</td>"
                f"<td align='center'>{fmt(r['price'])}</td>"
                f"<td align='center'>{fmt(r['qty'] * r['price'])}</td>"
                f"</tr>")

        def total_row(label, value, bg="", bold=False, color="#2B2F36"):
            b = "background-color:%s;" % bg if bg else ""
            w = "font-weight:bold;" if bold else ""
            return (f"<tr>"
                    f"<td width='60%' align='left' "
                    f"style='{b}{w}padding:8px 14px;color:{color};'>{label}</td>"
                    f"<td width='40%' align='left' "
                    f"style='{b}{w}padding:8px 14px;color:{color};'>"
                    f"{fmt(value)} {cur}</td></tr>")

        totals = (total_row("کۆی گشتی", inv["subtotal"])
                  + total_row("داشکاندن", inv["discount"])
                  + total_row("دوای داشکاندن", inv["total"], "#FAF5E8", True)
                  + total_row("پارەی دراو", inv["paid"])
                  + total_row("ماوە", due, "", True, "#C0392B"))

        note = (f"<p style='font-size:10pt;color:#7A828C;'>تێبینی: {inv['note']}</p>"
                if inv["note"] else "")

        parts = [p for p in (db.get("address"), lrm(db.get("phone")) if db.get("phone") else "") if p]
        contact = (f"""<p align="center" style="font-size:10pt;color:#8A9099;
                                 margin-top:7pt;margin-bottom:0pt;">
          {' &nbsp;·&nbsp; '.join(parts)}</p>""" if parts else "")

        html = f"""<div dir="rtl">
        <p align="center" style="font-size:24pt;font-weight:bold;color:#B8860B;
                                 margin-top:0pt;margin-bottom:0pt;">
          {db.get('company')}</p>
        {contact}

        <table width="100%" cellspacing="0" cellpadding="0"
               style="margin-top:11pt;margin-bottom:3pt;">
          <tr><td style="background-color:#B8860B;font-size:3pt;">&nbsp;</td></tr>
        </table>
        <table width="100%" cellspacing="0" cellpadding="0"
               style="margin-bottom:18pt;">
          <tr><td style="background-color:#E2CF95;font-size:1pt;">&nbsp;</td></tr>
        </table>

        <p style="font-size:13pt;font-weight:bold;color:#2B2F36;margin-bottom:4pt;">
          پسووڵەی فرۆشتن</p>
        <p style="font-size:11pt;color:#5A626C;margin-top:4pt;margin-bottom:2pt;">
          ژمارە: {lrm(iid)} &nbsp;·&nbsp;
          بەروار: {lrm(inv['date'])} &nbsp;·&nbsp;
          کڕیار: <b>{cus['name'] if cus else '—'}</b></p>
        <p style="font-size:11pt;color:#5A626C;margin-top:2pt;">
          مۆبایل: {lrm(cus['phone']) if cus and cus['phone'] else '—'}</p>

        <table width="100%" border="1" cellspacing="0" cellpadding="9"
               style="font-size:11pt;border-color:#E4E0D8;">
          <tr style="background-color:#FAF5E8;">
            <th width="7%">ژ</th><th width="45%">کاڵا</th>
            <th width="14%">بڕ</th><th width="17%">نرخ</th><th width="17%">کۆ</th>
          </tr>
          {body}
        </table>

        <table width="100%" cellspacing="0" cellpadding="0"
               style="margin-top:18pt;font-size:11pt;">
          {totals}
        </table>

        {note}

        <p style="font-size:9pt;color:#9AA1AA;margin-top:30pt;">
          سوپاس بۆ متمانەتان — {db.get('company')}</p>
        </div>"""

        path, _ = QFileDialog.getSaveFileName(self, "پاشەکەوتکردنی PDF",
                                              os.path.join(APP_DIR, f"invoice_{iid}.pdf"), "PDF (*.pdf)")
        if not path: return

        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(path)
        printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        printer.setPageMargins(QMarginsF(14, 14, 14, 14), QPageLayout.Unit.Millimeter)

        doc = QTextDocument()
        doc.setDefaultFont(QFont("Segoe UI", 10))
        doc.setHtml(html)
        # Without an explicit page size in the printer's own units the document
        # is laid out at its default width and prints microscopically small.
        doc.setPageSize(QSizeF(printer.pageRect(QPrinter.Unit.Point).size()))
        doc.print(printer)
        msg(self, f"PDF درووستکرا:\n{path}")


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
        sales = db.one("SELECT IFNULL(SUM(total),0) t, COUNT(*) c FROM invoices "
                       "WHERE date BETWEEN ? AND ?", (a, b))
        cogs = db.one("SELECT IFNULL(SUM(ii.qty*ii.cost),0) t FROM invoice_items ii "
                      "JOIN invoices i ON i.id=ii.invoice_id WHERE i.date BETWEEN ? AND ?", (a, b))["t"]
        exp = db.one("SELECT IFNULL(SUM(amount),0) t FROM expenses WHERE date BETWEEN ? AND ?", (a, b))["t"]
        sal = db.one("SELECT IFNULL(SUM(amount),0) t FROM salaries WHERE date BETWEEN ? AND ?", (a, b))["t"]
        pur = db.one("SELECT IFNULL(SUM(qty*price),0) t FROM purchases WHERE date BETWEEN ? AND ?", (a, b))["t"]
        gross = sales["t"] - cogs
        net = gross - exp - sal

        top = db.q("SELECT it.name n, SUM(ii.qty) q, SUM(ii.qty*ii.price) v FROM invoice_items ii "
                   "JOIN invoices i ON i.id=ii.invoice_id JOIN items it ON it.id=ii.item_id "
                   "WHERE i.date BETWEEN ? AND ? GROUP BY it.id ORDER BY v DESC LIMIT 10", (a, b))
        low = db.q("SELECT * FROM items WHERE minq>0 AND qty<=minq")
        debts = [(c["name"], db.balance(c["id"])) for c in db.q("SELECT id,name FROM customers")]
        debts = sorted([d for d in debts if d[1] > 0], key=lambda x: -x[1])

        th = (f"background:{HEADER_BG};color:{MUTED};padding:10px;"
              f"text-align:right;font-weight:600;")
        td = f"padding:10px;border-bottom:1px solid {ROW_LINE};text-align:right;"
        rows = "".join(f"<tr><td style='{td}'>{r['n']}</td><td style='{td}'>{fmt(r['q'])}</td>"
                       f"<td style='{td}'>{fmt(r['v'])}</td></tr>" for r in top) or \
               f"<tr><td style='{td}' colspan='3'>هیچ فرۆشتنێک نییە</td></tr>"
        lows = "".join(f"<tr><td style='{td}'>{r['name']}</td>"
                       f"<td style='{td}color:{RED};'>{fmt(r['qty'])}</td>"
                       f"<td style='{td}'>{fmt(r['minq'])}</td></tr>" for r in low) or \
               f"<tr><td style='{td}' colspan='3'>هیچ کاڵایەک کەم نەبووە</td></tr>"
        dbt = "".join(f"<tr><td style='{td}'>{n}</td><td style='{td}'>{fmt(v)}</td></tr>"
                      for n, v in debts[:20]) or \
              f"<tr><td style='{td}' colspan='2'>هیچ قەرزێک نییە</td></tr>"

        def line(label, value, strong=False, accent=None):
            c = accent or (TEXT if strong else MUTED)
            w = "700" if strong else "400"
            return (f"<tr><td style='{td}color:{MUTED};'>{label}</td>"
                    f"<td style='{td}text-align:left;color:{c};font-weight:{w};'>{value}</td></tr>")

        self.out.setHtml(f"""
        <div dir="rtl" style="font-family:'Segoe UI',Tahoma;font-size:14px;color:{TEXT};">
        <div style="color:{GOLD};font-size:19px;font-weight:700;margin-bottom:4px;">ڕاپۆرتی گشتی</div>
        <div style="color:{MUTED};font-size:12px;margin-bottom:18px;">
             {lrm(a)} &nbsp;تا&nbsp; {lrm(b)}</div>

        <table width="100%" cellspacing="0" cellpadding="0">
        {line(f"کۆی فرۆشتن — {sales['c']} پسووڵە", f"{fmt(sales['t'])} {cur}", True)}
        {line("تێچووی کاڵای فرۆشراو", f"{fmt(cogs)} {cur}")}
        {line("قازانجی خاو", f"{fmt(gross)} {cur}", True)}
        {line("مەسروفات", f"{fmt(exp)} {cur}")}
        {line("مووچەکان", f"{fmt(sal)} {cur}")}
        {line("قازانجی سافی", f"{fmt(net)} {cur}", True, GOLD_HI)}
        {line("کڕینی کاڵا", f"{fmt(pur)} {cur}")}
        </table>

        <div style="color:{GOLD};font-size:15px;font-weight:600;margin:26px 0 8px 0;">
            باشترین کاڵا فرۆشراوەکان</div>
        <table width="100%" cellspacing="0" cellpadding="0">
        <tr><th style="{th}">کاڵا</th><th style="{th}">بڕ</th><th style="{th}">بەها</th></tr>
        {rows}</table>

        <div style="color:{GOLD};font-size:15px;font-weight:600;margin:26px 0 8px 0;">
            قەرزی کڕیاران</div>
        <table width="100%" cellspacing="0" cellpadding="0">
        <tr><th style="{th}">کڕیار</th><th style="{th}">قەرز</th></tr>
        {dbt}</table>

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
            w = _csv.writer(f); w.writerow(["ناو", "جۆر", "یەکە", "بڕ", "تێچوو", "نرخ"])
            for r in db.q("SELECT * FROM items"):
                w.writerow([r["name"], r["kind"], r["unit"], r["qty"], r["cost"], r["price"]])
        with open(os.path.join(p, "debts.csv"), "w", newline="", encoding="utf-8-sig") as f:
            w = _csv.writer(f); w.writerow(["کڕیار", "مۆبایل", "قەرز"])
            for c in db.q("SELECT * FROM customers"):
                w.writerow([c["name"], c["phone"], db.balance(c["id"])])
        msg(self, "هەناردەکرا بۆ:\n" + p)


# ---------------------------------------------------------------- ڕێکخستن
class Settings(QWidget):
    def __init__(self, app):
        super().__init__(); self.app = app
        outer = QVBoxLayout(self); outer.setContentsMargins(0, 0, 0, 0)
        row = QHBoxLayout(); row.setSpacing(16)

        g = QGroupBox("زانیاری کۆمپانیا"); f = QFormLayout(g); f.setSpacing(12)
        self.co, self.ph, self.ad = QLineEdit(), QLineEdit(), QLineEdit()
        self.cu, self.usd = QLineEdit(), num(1e6, 2)
        f.addRow("ناوی کۆمپانیا", self.co); f.addRow("مۆبایل", self.ph)
        f.addRow("ناونیشان", self.ad); f.addRow("دراو", self.cu)
        f.addRow("نرخی دۆلار", self.usd)
        f.addRow(btn("پاشەکەوتکردن", self.save, "primary"))
        row.addWidget(g, 1)

        g3 = QGroupBox("شوێنی داتابەیس"); f3 = QVBoxLayout(g3); f3.setSpacing(10)
        self.dbl = QLabel(); self.dbl.setWordWrap(True); self.dbl.setObjectName("hint")
        f3.addWidget(self.dbl)
        dh = QLabel("ئەگەر دەتەوێت چەند کۆمپیوتەرێکی دووکان هەمان داتا بەکاربهێنن، "
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
        target = os.path.join(folder, "oil_shop.db")
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
        ("dash", "داشبۆرد",          "پوختەی دووکانەکە لە یەک ڕوانیندا"),
        ("sale", "فرۆشتن",           "دەرکردنی پسووڵە و بەڕێوەبردنی فرۆشتن"),
        ("cust", "کڕیاران",          "قەرز، وەرگرتنی پارە و کەشف حساب"),
        ("inv",  "مەخزەن",           "کاڵاکان، کڕین و ئاگاداری کەمبوون"),
        ("exp",  "مەسروفات و مووچە", "خەرجییەکان و کارمەندان"),
        ("rep",  "ڕاپۆرت",           "قازانج، فرۆشتن و هەناردەکردن"),
        ("st",   "ڕێکخستن",          "زانیاری دووکان و باکئەپ"),
    ]

    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.resize(1360, 850); self.setMinimumSize(1120, 700)

        self.dash = Dashboard(); self.sale = Sales(self); self.cust = Customers(self)
        self.inv = Inventory(self); self.exp = Expenses(self)
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
        sub_l = QLabel("دووکانی جوملە"); sub_l.setObjectName("brandSub")
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
        self.sale.restyle()
        self.theme_btn.setText("دۆخی ڕووناک" if theme == "dark" else "دۆخی تاریک")
        self.refresh_all()

    def go(self, i):
        k, name, desc = self.PAGES[i]
        self.stack.setCurrentIndex(i)
        self.title.setText(name); self.sub.setText(desc)
        try: getattr(self, k).refresh()
        except Exception as e: print("refresh error:", e)

    def refresh_brand(self):
        """Show the shop's own name wherever the app identifies itself."""
        name = db.get("company") or "دووکان"
        self.brand.setText(name)
        self.setWindowTitle(f"{name} — {APP_TITLE}")

    def refresh_all(self):
        for k, _, _ in self.PAGES:
            try: getattr(self, k).refresh()
            except Exception as e: print("refresh error:", e)
        self.refresh_brand()
        self.foot.setText(f"{db.get('company')}\nدووکان · وەشانی ١٫٠")
        self.datelbl.setText(lrm(QDate.currentDate().toString("yyyy-MM-dd")))

    def closeEvent(self, e):
        p = db.get("backup")
        if p and os.path.isdir(p):
            try:
                shutil.copy2(DB_PATH, os.path.join(
                    p, f"oil_shop_{datetime.datetime.now():%Y-%m-%d}.db"))
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
    """Ask for the shop's own details the first time the app is opened."""
    d = QDialog(); d.setObjectName("dlg")
    d.setWindowTitle("بەخێربێیت")
    d.setMinimumWidth(460)
    v = QVBoxLayout(d); v.setSpacing(14); v.setContentsMargins(26, 24, 26, 22)

    t = QLabel("ناوی دووکانەکەت بنووسە")
    t.setStyleSheet(f"color:{TITLE};font-size:20px;font-weight:700;")
    v.addWidget(t)
    h = QLabel("ئەم ناوە لە سەرەوەی بەرنامەکە و لەسەر پسووڵەکان دەردەکەوێت. "
               "دواتر دەتوانیت لە بەشی ڕێکخستن بیگۆڕیت.")
    h.setWordWrap(True); h.setObjectName("hint"); v.addWidget(h)

    f = QFormLayout(); f.setSpacing(11)
    co, ph, ad = QLineEdit(), QLineEdit(), QLineEdit()
    co.setPlaceholderText("پێویستە")
    f.addRow("ناوی دووکان", co)
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
