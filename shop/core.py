# -*- coding: utf-8 -*-
"""داتابەیس، ڕێکخستنی ناوخۆیی و یارمەتیدەرە گشتییەکان."""
import os, re, sqlite3, shutil, datetime, configparser, hashlib

APP_TITLE = "سیستەمی دووکانی جوملە"
VERSION   = "٢٫٠"
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

CFG_PATH = os.path.join(APP_DIR, "config.ini")

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
CREATE TABLE IF NOT EXISTS suppliers(
    id INTEGER PRIMARY KEY, name TEXT, phone TEXT, address TEXT, note TEXT);
CREATE TABLE IF NOT EXISTS purchases(
    id INTEGER PRIMARY KEY, date TEXT, supplier TEXT, item_id INTEGER,
    qty REAL, price REAL, note TEXT, supplier_id INTEGER, paid REAL DEFAULT 0);
CREATE TABLE IF NOT EXISTS supplier_payments(
    id INTEGER PRIMARY KEY, date TEXT, supplier_id INTEGER, amount REAL, note TEXT);
CREATE TABLE IF NOT EXISTS expenses(
    id INTEGER PRIMARY KEY, date TEXT, category TEXT, amount REAL, note TEXT);
CREATE TABLE IF NOT EXISTS employees(
    id INTEGER PRIMARY KEY, name TEXT, position TEXT, salary REAL, phone TEXT);
CREATE TABLE IF NOT EXISTS salaries(
    id INTEGER PRIMARY KEY, date TEXT, employee_id INTEGER, amount REAL, note TEXT);
"""

CUST_BAL = ("(IFNULL((SELECT SUM(total-paid) FROM invoices WHERE customer_id=c.id),0)"
            " - IFNULL((SELECT SUM(amount) FROM payments WHERE customer_id=c.id),0))")
SUP_BAL = ("(IFNULL((SELECT SUM(qty*price-paid) FROM purchases WHERE supplier_id=s.id),0)"
           " - IFNULL((SELECT SUM(amount) FROM supplier_payments WHERE supplier_id=s.id),0))")


class DB:
    def __init__(self):
        self.con = sqlite3.connect(DB_PATH)
        self.con.row_factory = sqlite3.Row
        self.con.executescript(SCHEMA)
        self._migrate()
        self.con.commit()
        for k, v in [("company", ""), ("phone", ""), ("address", ""), ("currency", "د.ع"),
                     ("usd", "1320"), ("backup", ""), ("theme", "dark"), ("pin", "")]:
            if not self.one("SELECT v FROM settings WHERE k=?", (k,)):
                self.x("INSERT INTO settings(k,v) VALUES(?,?)", (k, v))

    def _migrate(self):
        """Bring a database made by an older version up to today's shape."""
        cols = {r["name"] for r in self.q("PRAGMA table_info(purchases)")}
        if "supplier_id" not in cols:
            self.con.execute("ALTER TABLE purchases ADD COLUMN supplier_id INTEGER")
            self.con.execute("ALTER TABLE purchases ADD COLUMN paid REAL DEFAULT 0")
            # the old version had no supplier debts: every purchase was cash
            self.con.execute("UPDATE purchases SET paid=qty*price")
        # purchases that only carry a typed supplier name get a real supplier
        for r in self.q("SELECT DISTINCT TRIM(supplier) n FROM purchases "
                        "WHERE supplier_id IS NULL AND TRIM(IFNULL(supplier,''))<>''"):
            sid = self.supplier_id(r["n"])
            self.con.execute("UPDATE purchases SET supplier_id=? "
                             "WHERE supplier_id IS NULL AND TRIM(supplier)=?", (sid, r["n"]))

    # ---- بنەڕەت ----
    def q(self, sql, p=()):   return self.con.execute(sql, p).fetchall()
    def one(self, sql, p=()): return self.con.execute(sql, p).fetchone()

    def run(self, sql, p=()):
        """Execute without committing — use inside `with db.con:` blocks."""
        return self.con.execute(sql, p).lastrowid

    def x(self, sql, p=()):
        c = self.con.execute(sql, p); self.con.commit(); return c.lastrowid

    def val(self, sql, p=()):
        r = self.one(sql, p)
        return (r[0] or 0) if r else 0

    def get(self, k, d=""):
        r = self.one("SELECT v FROM settings WHERE k=?", (k,))
        return r["v"] if r else d

    def set(self, k, v):
        self.x("INSERT INTO settings(k,v) VALUES(?,?) ON CONFLICT(k) DO UPDATE SET v=?",
               (k, str(v), str(v)))

    # ---- حیساب ----
    def balance(self, cid):
        return self.val(f"SELECT {CUST_BAL} FROM customers c WHERE c.id=?", (cid,))

    def customers(self, search=""):
        s = f"%{search}%"
        return self.q(f"SELECT c.*, {CUST_BAL} bal FROM customers c "
                      "WHERE c.name LIKE ? OR IFNULL(c.phone,'') LIKE ? ORDER BY c.name", (s, s))

    def supplier_balance(self, sid):
        return self.val(f"SELECT {SUP_BAL} FROM suppliers s WHERE s.id=?", (sid,))

    def suppliers(self, search=""):
        s = f"%{search}%"
        return self.q(f"SELECT s.*, {SUP_BAL} bal FROM suppliers s "
                      "WHERE s.name LIKE ? OR IFNULL(s.phone,'') LIKE ? ORDER BY s.name", (s, s))

    def supplier_id(self, name):
        """Id of the supplier with this name, creating it when it is new."""
        name = (name or "").strip()
        if not name: return None
        r = self.one("SELECT id FROM suppliers WHERE name=?", (name,))
        if r: return r["id"]
        return self.con.execute("INSERT INTO suppliers(name) VALUES(?)", (name,)).lastrowid

    def period(self, a, b):
        """Sales, cost and profit figures between two dates (inclusive)."""
        s = self.one("SELECT IFNULL(SUM(total),0) t, COUNT(*) c FROM invoices "
                     "WHERE date BETWEEN ? AND ?", (a, b))
        cogs = self.val("SELECT SUM(ii.qty*ii.cost) FROM invoice_items ii JOIN invoices i "
                        "ON i.id=ii.invoice_id WHERE i.date BETWEEN ? AND ?", (a, b))
        exp = self.val("SELECT SUM(amount) FROM expenses WHERE date BETWEEN ? AND ?", (a, b))
        sal = self.val("SELECT SUM(amount) FROM salaries WHERE date BETWEEN ? AND ?", (a, b))
        pur = self.val("SELECT SUM(qty*price) FROM purchases WHERE date BETWEEN ? AND ?", (a, b))
        gross = s["t"] - cogs
        return dict(sales=s["t"], count=s["c"], cogs=cogs, exp=exp, sal=sal, pur=pur,
                    gross=gross, net=gross - exp - sal)

    # ---- باکئەپ ----
    def backup_to(self, folder, stamp="%Y-%m-%d_%H-%M", keep=20):
        """Write a consistent copy into `folder` and drop all but the newest `keep`."""
        name = f"oil_shop_{datetime.datetime.now().strftime(stamp)}.db"
        self.con.commit()
        dst = sqlite3.connect(os.path.join(folder, name))
        try: self.con.backup(dst)
        finally: dst.close()
        old = sorted(f for f in os.listdir(folder)
                     if f.startswith("oil_shop_") and f.endswith(".db"))
        for f in old[:-keep]:
            try: os.remove(os.path.join(folder, f))
            except Exception: pass
        return name


db = DB()


# ---------------------------------------------------------------- یارمەتیدەر
def fmt(n):
    try: n = float(n)
    except Exception: return "0"
    return f"{n:,.0f}" if abs(n - round(n)) < 0.01 else f"{n:,.2f}"


def money(n):
    return f"{fmt(n)} {db.get('currency')}"


def usd(n):
    """Dollar equivalent at the rate from Settings, or '' when no rate is set."""
    try: rate = float(db.get("usd") or 0)
    except Exception: rate = 0
    if rate <= 0: return ""
    return f"≈ {LRM}${float(n) / rate:,.0f}"


def today():
    return datetime.date.today().isoformat()


def pin_hash(pin):
    return hashlib.sha256(("oilshop:" + pin).encode("utf-8")).hexdigest()


LRM = "‎"
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def lrm(v):
    """Pin a digit-only string so RTL bidi can't reorder it (0750 123 4567)."""
    v = str(v).strip()
    return LRM + v if v else v


def ltr(v):
    v = str(v)
    return LRM + v if DATE_RE.match(v) else v


def esc(v):
    """Make user-typed text safe to drop into the HTML used for PDFs."""
    return (str(v or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
