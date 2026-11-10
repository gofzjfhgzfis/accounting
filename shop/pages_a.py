# -*- coding: utf-8 -*-
"""داشبۆرد، فرۆشتن و کڕیاران."""
import datetime

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import *

from .core import db, fmt, money, usd, today, lrm, esc
from .theme import T
from .ui import *

WALK_IN = "کڕیاری نەقد"
EPS = 0.004


def combo_data(c):
    """Data of the entry whose text is shown — None when the typed text matches nothing."""
    i = c.findText(c.currentText().strip())
    return c.itemData(i) if i >= 0 else None


def refill(c, rows, keep=True):
    """Replace a combo's entries [(text, data)] without losing the selection."""
    cur = c.currentData() if keep else None
    c.blockSignals(True)
    c.clear()
    for text, data in rows: c.addItem(text, data)
    i = c.findData(cur) if cur is not None else -1
    c.setCurrentIndex(i if i >= 0 else (0 if rows else -1))
    c.blockSignals(False)


def month_start(d=None):
    d = d or datetime.date.today()
    return d.replace(day=1)


# ---------------------------------------------------------------- داشبۆرد
class Dashboard(QWidget):
    SPECS = [("today",  "فرۆشتنی ئەمڕۆ",     "GREEN",  "cash"),
             ("month",  "فرۆشتنی ئەم مانگە", "BLUE",   "sale"),
             ("profit", "قازانجی ئەم مانگە", "GOLD",   "trend"),
             ("debt",   "قەرزی کڕیاران",     "RED",    "cust"),
             ("sup",    "قەرزی دابینکەران",  "ORANGE", "sup"),
             ("stock",  "بەهای مەخزەن",      "VIOLET", "inv")]

    def __init__(self, app):
        super().__init__(); self.app = app
        v = QVBoxLayout(self); v.setSpacing(14); v.setContentsMargins(0, 0, 0, 0)
        g = QGridLayout(); g.setSpacing(12)
        self.c = {}
        for i, (k, cap, accent, ico) in enumerate(self.SPECS):
            self.c[k] = StatCard(cap, accent, ico)
            g.addWidget(self.c[k], i // 3, i % 3)
        v.addLayout(g)

        row = QHBoxLayout(); row.setSpacing(12)
        box, bv = card()
        top = QHBoxLayout()
        top.addWidget(label("فرۆشتن", "panelTitle")); top.addStretch()
        ch, self.range = chips(["٧ ڕۆژ", "٣٠ ڕۆژ", "١٢ مانگ"], self.draw_chart, 1)
        top.addLayout(ch); bv.addLayout(top)
        self.chart_sum = label("", "hint"); bv.addWidget(self.chart_sum)
        self.chart = BarChart(); bv.addWidget(self.chart, 1)
        row.addWidget(box, 5)
        self.debtors = ListCard("گەورەترین قەرزداران", "هیچ کڕیارێک قەرزدار نییە")
        self.low = ListCard("کاڵای کەمبوو", "هیچ کاڵایەک کەم نەبووە")
        row.addWidget(self.debtors, 3); row.addWidget(self.low, 3)
        v.addLayout(row, 1)

    def refresh(self):
        t = datetime.date.today()
        m0 = month_start(t)
        p1 = m0 - datetime.timedelta(days=1); p0 = month_start(p1)
        day = db.period(t.isoformat(), t.isoformat())
        cur = db.period(m0.isoformat(), t.isoformat())
        prev = db.period(p0.isoformat(), p1.isoformat())
        custs = db.customers()
        debts = [c for c in custs if c["bal"] > EPS]
        sups = [s for s in db.suppliers() if s["bal"] > EPS]
        stock = db.one("SELECT IFNULL(SUM(qty*cost),0) v, COUNT(*) n FROM items")
        low = db.q("SELECT * FROM items WHERE minq>0 AND qty<=minq ORDER BY qty*1.0/minq")

        self.c["today"].set(money(day["sales"]), f"{day['count']} پسووڵە")
        self.c["month"].set(money(cur["sales"]), f"مانگی پێشوو: {fmt(prev['sales'])}")
        self.c["profit"].set(money(cur["net"]), "دوای تێچوو، مەسروفات و مووچە")
        total_debt = sum(c["bal"] for c in debts)
        self.c["debt"].set(money(total_debt), f"{len(debts)} کڕیار قەرزدارن")
        self.c["sup"].set(money(sum(s["bal"] for s in sups)), f"بۆ {len(sups)} دابینکەر")
        self.c["stock"].set(money(stock["v"]),
                            f"{stock['n']} کاڵا   {usd(stock['v'])}".strip())

        debts.sort(key=lambda c: -c["bal"])
        self.debtors.set_rows([(c["name"], fmt(c["bal"]), "txtBad") for c in debts[:6]])
        self.low.set_rows([(i["name"], f"{fmt(i['qty'])} / {fmt(i['minq'])}", "txtBad")
                           for i in low[:6]])
        self.draw_chart()

    def draw_chart(self):
        t = datetime.date.today()
        mode = self.range.checkedId()
        cur = db.get("currency")
        if mode == 2:
            y, m = t.year, t.month
            keys = []
            for _ in range(12):
                keys.append(f"{y:04d}-{m:02d}")
                m -= 1
                if m == 0: y, m = y - 1, 12
            keys.reverse()
            got = {r["k"]: r["t"] for r in db.q(
                "SELECT substr(date,1,7) k, SUM(total) t FROM invoices "
                "WHERE date>=? GROUP BY k", (keys[0] + "-01",))}
            data = [(f"{int(k[5:])}/{k[2:4]}", got.get(k, 0),
                     f"{lrm(k)}\n{fmt(got.get(k, 0))} {cur}") for k in keys]
        else:
            n = 7 if mode == 0 else 30
            days = [t - datetime.timedelta(days=i) for i in range(n - 1, -1, -1)]
            got = {r["date"]: r["t"] for r in db.q(
                "SELECT date, SUM(total) t FROM invoices WHERE date>=? GROUP BY date",
                (days[0].isoformat(),))}
            data = [(f"{d.day}/{d.month}", got.get(d.isoformat(), 0),
                     f"{lrm(d.isoformat())}\n{fmt(got.get(d.isoformat(), 0))} {cur}") for d in days]
        self.chart.set_data(data)
        self.chart_sum.setText(f"کۆی ئەم ماوەیە:  {fmt(sum(d[1] for d in data))} {cur}")


# ---------------------------------------------------------------- پسووڵە
def invoice_html(iid):
    inv = db.one("SELECT * FROM invoices WHERE id=?", (iid,))
    cus = db.one("SELECT * FROM customers WHERE id=?", (inv["customer_id"],))
    rows = db.q("SELECT ii.*, IFNULL(it.name,'—') name, IFNULL(it.unit,'') unit "
                "FROM invoice_items ii LEFT JOIN items it ON it.id=ii.item_id "
                "WHERE ii.invoice_id=?", (iid,))
    cur = esc(db.get("currency"))
    due = inv["total"] - inv["paid"]
    body = doc_table(
        ["ژ", "کاڵا", "بڕ", "نرخ", "کۆ"],
        [(n, esc(r["name"]), f"{fmt(r['qty'])} {esc(r['unit'])}", fmt(r["price"]),
          fmt(r["qty"] * r["price"])) for n, r in enumerate(rows, 1)],
        ["7%", "45%", "16%", "15%", "17%"])

    def total_row(lbl, value, bg="", bold=False, color="#2B2F36"):
        b = f"background-color:{bg};" if bg else ""
        w = "font-weight:bold;" if bold else ""
        return (f"<tr><td width='60%' align='left' style='{b}{w}padding:7px 14px;color:{color};'>"
                f"{lbl}</td><td width='40%' align='left' style='{b}{w}padding:7px 14px;"
                f"color:{color};'>{fmt(value)} {cur}</td></tr>")

    totals = (total_row("کۆی گشتی", inv["subtotal"]) + total_row("داشکاندن", inv["discount"])
              + total_row("دوای داشکاندن", inv["total"], "#FAF5E8", True)
              + total_row("پارەی دراو", inv["paid"])
              + total_row("ماوە", due, "", True, "#C0392B" if due > EPS else "#2B2F36"))
    note = (f"<p style='font-size:10pt;color:#7A828C;'>تێبینی: {esc(inv['note'])}</p>"
            if inv["note"] else "")
    name = esc(cus["name"]) if cus else WALK_IN
    phone = lrm(cus["phone"]) if cus and cus["phone"] else "—"
    sub = (f"ژمارە: {lrm(iid)} &nbsp;·&nbsp; بەروار: {lrm(inv['date'])} &nbsp;·&nbsp; "
           f"کڕیار: <b>{name}</b> &nbsp;·&nbsp; مۆبایل: {esc(phone)}")
    return f"""<div dir="rtl">{doc_head("پسووڵەی فرۆشتن", sub)}{body}
        <table width="100%" cellspacing="0" cellpadding="0" style="margin-top:16pt;font-size:11pt;">
        {totals}</table>{note}
        <p style="font-size:9pt;color:#9AA1AA;margin-top:28pt;">
          سوپاس بۆ متمانەتان — {esc(db.get('company'))}</p></div>"""


class InvoiceCard(PickCard):
    def __init__(self, row):
        super().__init__(row["id"])
        due = row["total"] - row["paid"]
        if due <= EPS: badge = ("دراوە", "good")
        elif row["paid"] > EPS: badge = ("بەشێکی دراوە", "warn")
        else: badge = ("قەرز", "bad")
        self.head(f"پسووڵە #{lrm(row['id'])}", row["cn"], *badge)
        self.sep()
        self.row("بەروار", lrm(row["date"]), "txtMuted")
        self.row("کۆ", money(row["total"]))
        if due > EPS: self.row("ماوە", money(due), "txtBad")


class Sales(QWidget):
    def __init__(self, app):
        super().__init__(); self.app = app
        self.lines = []
        v = QVBoxLayout(self); v.setContentsMargins(0, 0, 0, 0)
        self.tabs = QTabWidget(); v.addWidget(self.tabs)
        self.tabs.addTab(self._new_tab(), "پسووڵەی نوێ")
        self.tabs.addTab(self._list_tab(), "پسووڵەکان")
        self.tabs.currentChanged.connect(lambda _: self.refresh())

    # ---- پسووڵەی نوێ ----
    def _new_tab(self):
        w = QWidget(); main = QHBoxLayout(w)
        main.setSpacing(12); main.setContentsMargins(0, 14, 0, 0)

        side, sv = card(spacing=9); side.setFixedWidth(350)
        sv.addWidget(heading("کڕیار"))
        self.cust = combo(editable=True)
        self.cust.currentTextChanged.connect(lambda _: self.calc())
        sv.addWidget(self.cust)
        self.cust_hint = label("", "hint"); sv.addWidget(self.cust_hint)
        self.dt = date_edit(); sv.addLayout(field("بەروار", self.dt))
        sv.addSpacing(8)
        sv.addWidget(heading("زیادکردنی کاڵا"))
        self.item = combo(editable=True)
        self.item.currentTextChanged.connect(lambda _: self.autoprice())
        sv.addWidget(self.item)
        self.item_hint = label("", "hint"); sv.addWidget(self.item_hint)
        self.qty = num(dec=2, val=1); self.pr = num(dec=2)
        qp = QHBoxLayout(); qp.setSpacing(9)
        qp.addLayout(field("بڕ", self.qty)); qp.addLayout(field("نرخی یەکە", self.pr))
        sv.addLayout(qp)
        for s in (self.qty, self.pr):
            s.lineEdit().returnPressed.connect(self.add_line)
        sv.addSpacing(4)
        sv.addWidget(btn("زیادکردن بۆ پسووڵە", self.add_line, ico="plus"))
        sv.addWidget(label("دوای نووسینی بڕ، Enter لێبدە بۆ زیادکردن.", "hint", wrap=True))
        sv.addStretch()
        main.addWidget(side)

        box, bv = card(spacing=10)
        top = QHBoxLayout()
        top.addWidget(label("کاڵاکانی پسووڵە", "panelTitle"))
        self.count = pill("0"); top.addWidget(self.count); top.addStretch()
        top.addWidget(btn("لابردنی ڕیز", self.rm_line, "danger"))
        bv.addLayout(top)
        self.lt = table(["کاڵا", "بڕ", "نرخ", "کۆ"], stretch=0, flat=True)
        bv.addWidget(self.lt, 1)

        foot = QHBoxLayout(); foot.setSpacing(22)
        left = QVBoxLayout(); left.setSpacing(9)
        self.disc, self.paid, self.note = num(dec=2), num(dec=2), QLineEdit()
        self.note.setPlaceholderText("ئارەزوومەندانە")
        self.disc.valueChanged.connect(lambda _: self.totals())
        self.paid.valueChanged.connect(lambda _: self.totals())
        dp = QHBoxLayout(); dp.setSpacing(9)
        dp.addLayout(field("داشکاندن", self.disc))
        pv = field("پارەی دراو", self.paid); dp.addLayout(pv)
        left.addLayout(dp)
        self.all_btn = btn("هەمووی دراوە", self.pay_all)
        nb = QHBoxLayout(); nb.setSpacing(9)
        nb.addLayout(field("تێبینی", self.note), 1)
        nb.addWidget(self.all_btn, 0, Qt.AlignmentFlag.AlignBottom)
        left.addLayout(nb)
        foot.addLayout(left, 3)

        right = QVBoxLayout(); right.setSpacing(4)
        self.sub_lbl, self.due_lbl = label("0", "txtStrong"), label("0", "txtBad")
        self.total_lbl, self.usd_lbl = label("0", "big"), label("", "hint")
        for cap, w2 in [("کۆی کاڵاکان", self.sub_lbl), ("ماوە (قەرز)", self.due_lbl)]:
            h = QHBoxLayout(); h.addWidget(label(cap, "cardKey")); h.addStretch(); h.addWidget(w2)
            right.addLayout(h)
        h = QHBoxLayout(); h.addWidget(label("کۆی گشتی", "cardKey")); h.addStretch()
        h.addWidget(self.usd_lbl); h.addSpacing(8); h.addWidget(self.total_lbl)
        right.addLayout(h)
        save = btn("تۆمارکردنی پسووڵە", self.save, "primary"); save.setMinimumHeight(26)
        right.addWidget(save)
        foot.addLayout(right, 2)
        bv.addLayout(foot)
        main.addWidget(box, 1)
        return w

    # ---- لیستی پسووڵەکان ----
    def _list_tab(self):
        w = QWidget(); v = QVBoxLayout(w); v.setSpacing(12); v.setContentsMargins(0, 14, 0, 0)
        h = QHBoxLayout(); h.setSpacing(8)
        h.addWidget(btn("بینین", self.view))
        h.addWidget(btn("PDF", self.pdf, ico="pdf"))
        h.addWidget(btn("چاپکردن", self.print_, ico="print"))
        h.addWidget(btn("سڕینەوە", self.rm_inv, "danger"))
        h.addStretch()
        ch, self.flt = chips(["هەموو", "قەرز ماوە", "ئەمڕۆ"], self.load_list)
        h.addLayout(ch)
        self.search = search_box("ژمارەی پسووڵە یان ناوی کڕیار…", self.load_list, 230)
        h.addWidget(self.search)
        v.addLayout(h)
        self.sum_lbl = label("", "hint"); v.addWidget(self.sum_lbl)
        self.grid = CardGrid("هیچ پسووڵەیەک نەدۆزرایەوە", min_w=230, on_open=self.view)
        v.addWidget(self.grid, 1)
        return w

    def refresh(self):
        if self.tabs.currentIndex() == 0:
            refill(self.cust, [(WALK_IN, 0)] + [(c["name"], c["id"]) for c in
                                                db.q("SELECT id,name FROM customers ORDER BY name")])
            refill(self.item, [(i["name"], i["id"]) for i in
                               db.q("SELECT id,name FROM items ORDER BY name")])
            self.autoprice(); self.calc()
        else:
            self.load_list()

    def new_invoice(self):
        self.tabs.setCurrentIndex(0)
        self.item.setFocus()

    def load_list(self):
        where, p = ["1=1"], []
        s = self.search.text().strip()
        if s:
            where.append("(IFNULL(c.name,?) LIKE ? OR CAST(i.id AS TEXT)=?)")
            p += [WALK_IN, f"%{s}%", s.lstrip("#")]
        if self.flt.checkedId() == 1: where.append(f"i.total-i.paid>{EPS}")
        if self.flt.checkedId() == 2: where.append("i.date=?"); p.append(today())
        w = " AND ".join(where)
        rows = db.q(f"SELECT i.*, IFNULL(c.name,'{WALK_IN}') cn FROM invoices i "
                    f"LEFT JOIN customers c ON c.id=i.customer_id WHERE {w} "
                    "ORDER BY i.id DESC LIMIT 150", p)
        s = db.one(f"SELECT COUNT(*) n, IFNULL(SUM(i.total),0) t, IFNULL(SUM(i.total-i.paid),0) d "
                   f"FROM invoices i LEFT JOIN customers c ON c.id=i.customer_id WHERE {w}", p)
        more = "   ·   تەنها دوایین ١٥٠ پیشان دەدرێن" if s["n"] > 150 else ""
        self.sum_lbl.setText(f"{s['n']} پسووڵە   ·   کۆ: {money(s['t'])}   ·   "
                             f"ماوە: {money(s['d'])}{more}")
        self.grid.set_cards([InvoiceCard(r) for r in rows])

    # ---- دروستکردن ----
    def autoprice(self):
        i = combo_data(self.item)
        r = db.one("SELECT * FROM items WHERE id=?", (i,)) if i else None
        if r:
            self.pr.setValue(r["price"])
            low = r["minq"] and r["qty"] <= r["minq"]
            self.item_hint.setText(f"بەردەست لە مەخزەن:  {fmt(r['qty'])} {r['unit'] or ''}"
                                   + ("   ·   کەمە" if low else ""))
        else:
            self.item_hint.setText("کاڵایەک هەڵبژێرە یان ناوەکەی بنووسە")

    def add_line(self):
        i = combo_data(self.item)
        if not i: return msg(self, "ئەم کاڵایە لە مەخزەندا نییە")
        if self.qty.value() <= 0: return
        it = db.one("SELECT * FROM items WHERE id=?", (i,))
        # what is already on this invoice counts against the stock too
        already = sum(l["qty"] for l in self.lines if l["id"] == i)
        if already + self.qty.value() > it["qty"] + EPS:
            if not ask(self, f"بڕی مەخزەن تەنها {fmt(it['qty'])}ە. بەردەوام بم؟"): return
        for l in self.lines:
            if l["id"] == i and l["price"] == self.pr.value():
                l["qty"] += self.qty.value()
                break
        else:
            self.lines.append({"id": i, "name": it["name"], "qty": self.qty.value(),
                               "price": self.pr.value(), "cost": it["cost"]})
        self.qty.setValue(1)
        self.calc()
        self.item.setFocus(); self.item.lineEdit().selectAll()

    def rm_line(self):
        r = sel_row(self.lt)
        if r < 0 and self.lines: r = len(self.lines) - 1
        if r >= 0: self.lines.pop(r); self.calc()

    def calc(self):
        fill(self.lt, [(l["name"], fmt(l["qty"]), fmt(l["price"]), fmt(l["qty"] * l["price"]))
                       for l in self.lines])
        self.count.setText(str(len(self.lines)))
        self.totals()

    def totals(self):
        sub = sum(l["qty"] * l["price"] for l in self.lines)
        self.disc.setMaximum(sub)
        tot = sub - self.disc.value()
        cid = combo_data(self.cust)
        walk = cid == 0
        # a sale with no named customer cannot leave a debt behind
        self.paid.setMaximum(tot)
        if walk: self.paid.setValue(tot)
        self.paid.setEnabled(not walk); self.all_btn.setEnabled(not walk)
        if walk: self.cust_hint.setText("فرۆشتنی نەقد — هەموو پارەکە وەردەگیرێت")
        elif cid:
            bal = db.balance(cid)
            self.cust_hint.setText(f"قەرزی ئێستای ئەم کڕیارە:  {money(bal)}")
        else: self.cust_hint.setText("ئەم ناوە لە لیستی کڕیاراندا نییە")
        self.sub_lbl.setText(money(sub))
        self.total_lbl.setText(money(tot)); self.usd_lbl.setText(usd(tot) if tot else "")
        due = tot - self.paid.value()
        self.due_lbl.setText(money(due))
        self.due_lbl.setObjectName("txtBad" if due > EPS else "txtGood")
        self.due_lbl.style().unpolish(self.due_lbl); self.due_lbl.style().polish(self.due_lbl)

    def pay_all(self):
        self.paid.setValue(self.paid.maximum())

    def save(self):
        if not self.lines: return msg(self, "هیچ کاڵایەک زیاد نەکراوە")
        cid = combo_data(self.cust)
        if cid is None:
            return msg(self, "ئەم کڕیارە تۆمار نەکراوە.\nلە بەشی کڕیاران زیادی بکە یان «کڕیاری نەقد» هەڵبژێرە.")
        sub = sum(l["qty"] * l["price"] for l in self.lines)
        tot = sub - self.disc.value()
        with db.con:
            iid = db.run("INSERT INTO invoices(date,customer_id,subtotal,discount,total,paid,note) "
                         "VALUES(?,?,?,?,?,?,?)",
                         (dstr(self.dt), cid or None, sub, self.disc.value(), tot,
                          self.paid.value(), self.note.text()))
            for l in self.lines:
                db.run("INSERT INTO invoice_items(invoice_id,item_id,qty,price,cost) VALUES(?,?,?,?,?)",
                       (iid, l["id"], l["qty"], l["price"], l["cost"]))
                db.run("UPDATE items SET qty=qty-? WHERE id=?", (l["qty"], l["id"]))
        self.lines = []; self.disc.setValue(0); self.paid.setValue(0); self.note.clear()
        self.cust.setCurrentIndex(0)
        self.app.refresh_all()
        d = QMessageBox(self); d.setWindowTitle("تۆمارکرا")
        d.setText(f"پسووڵە #{iid} بە سەرکەوتوویی تۆمارکرا.")
        b_print = d.addButton("چاپکردن", QMessageBox.ButtonRole.ActionRole)
        b_pdf = d.addButton("PDF", QMessageBox.ButtonRole.ActionRole)
        d.addButton("باشە", QMessageBox.ButtonRole.AcceptRole).setObjectName("primary")
        d.exec()
        if d.clickedButton() is b_print: print_html(self, invoice_html(iid))
        elif d.clickedButton() is b_pdf: save_pdf(self, invoice_html(iid), f"invoice_{iid}.pdf")

    # ---- کردارەکانی لیست ----
    def _picked(self):
        iid = self.grid.selected
        if not iid: msg(self, "سەرەتا پسووڵەیەک هەڵبژێرە")
        return iid

    def pdf(self):
        iid = self._picked()
        if iid and save_pdf(self, invoice_html(iid), f"invoice_{iid}.pdf"):
            self.app.toast("PDF درووستکرا")

    def print_(self):
        iid = self._picked()
        if iid: print_html(self, invoice_html(iid))

    def view(self):
        iid = self._picked()
        if not iid: return
        inv = db.one(f"SELECT i.*, IFNULL(c.name,'{WALK_IN}') cn FROM invoices i "
                     "LEFT JOIN customers c ON c.id=i.customer_id WHERE i.id=?", (iid,))
        rows = db.q("SELECT ii.*, IFNULL(it.name,'—') name FROM invoice_items ii "
                    "LEFT JOIN items it ON it.id=ii.item_id WHERE ii.invoice_id=?", (iid,))
        d = dialog(self, f"پسووڵە #{iid}", 640); d.resize(660, 540)
        v = QVBoxLayout(d); v.setSpacing(12); v.setContentsMargins(22, 20, 22, 18)
        top = QHBoxLayout()
        col = QVBoxLayout(); col.setSpacing(2)
        col.addWidget(label(inv["cn"], "panelTitle"))
        col.addWidget(label(f"بەروار:  {lrm(inv['date'])}" +
                            (f"   ·   {inv['note']}" if inv["note"] else ""), "cardMeta"))
        top.addLayout(col); top.addStretch()
        due = inv["total"] - inv["paid"]
        top.addWidget(pill("دراوە", "good") if due <= EPS else pill(f"ماوە: {money(due)}", "bad"))
        v.addLayout(top)
        t = table(["کاڵا", "بڕ", "نرخ", "کۆ"], stretch=0)
        fill(t, [(r["name"], fmt(r["qty"]), fmt(r["price"]), fmt(r["qty"] * r["price"])) for r in rows])
        v.addWidget(t, 1)
        for cap, val, tone in [("کۆی کاڵاکان", inv["subtotal"], "txtStrong"),
                               ("داشکاندن", inv["discount"], "txtStrong"),
                               ("کۆی گشتی", inv["total"], "txtGold"),
                               ("پارەی دراو", inv["paid"], "txtGood")]:
            h = QHBoxLayout(); h.addWidget(label(cap, "cardKey")); h.addStretch()
            h.addWidget(label(money(val), tone)); v.addLayout(h)
        h = QHBoxLayout(); h.setSpacing(8)
        h.addWidget(btn("PDF", lambda: save_pdf(d, invoice_html(iid), f"invoice_{iid}.pdf"), ico="pdf"))
        h.addWidget(btn("چاپکردن", lambda: print_html(d, invoice_html(iid)), ico="print"))
        h.addStretch(); h.addWidget(btn("داخستن", d.accept, "primary"))
        v.addLayout(h)
        d.exec()

    def rm_inv(self):
        iid = self._picked()
        if not iid: return
        if not ask(self, f"پسووڵە #{iid} بسڕدرێتەوە؟\nبڕەکان دەگەڕێنەوە بۆ مەخزەن."): return
        with db.con:
            for r in db.q("SELECT * FROM invoice_items WHERE invoice_id=?", (iid,)):
                db.run("UPDATE items SET qty=qty+? WHERE id=?", (r["qty"], r["item_id"]))
            db.run("DELETE FROM invoice_items WHERE invoice_id=?", (iid,))
            db.run("DELETE FROM invoices WHERE id=?", (iid,))
        self.app.refresh_all(); self.app.toast("پسووڵەکە سڕایەوە")


# ---------------------------------------------------------------- کەشف حساب
def statement(parent, app, title, name, fetch, del_pay):
    """Running-balance ledger shared by customers and suppliers.

    fetch() -> [dict(date, text, debit, credit, pay)] where `pay` is the id of a
    payment row (deletable) or None; del_pay(id) removes one.
    """
    d = dialog(parent, f"{title} — {name}", 760); d.resize(780, 560)
    v = QVBoxLayout(d); v.setSpacing(12); v.setContentsMargins(22, 20, 22, 18)
    t = table(["بەروار", "ڕوونکردنەوە", "بڕ", "پارەی دراو", "ماوە"], stretch=1)
    v.addWidget(t, 1)
    foot = QHBoxLayout()
    total = label("", "big"); foot.addWidget(label("کۆی ماوە", "cardKey")); foot.addStretch()
    foot.addWidget(total); v.addLayout(foot)
    state = {"rows": [], "bal": 0}

    def load():
        rows = sorted(fetch(), key=lambda r: (r["date"], r["pay"] is not None))
        bal = 0
        out = []
        for r in rows:
            bal += r["debit"] - r["credit"]
            out.append((r["date"], r["text"], fmt(r["debit"]) if r["debit"] else "—",
                        fmt(r["credit"]) if r["credit"] else "—", fmt(bal)))
        state["rows"], state["bal"], state["out"] = rows, bal, out
        fill(t, out, {3: lambda r: T.GREEN if r[3] != "—" else None})
        total.setText(money(bal))
        t.scrollToBottom()

    def html():
        sub = f"ناو: <b>{esc(name)}</b> &nbsp;·&nbsp; بەروار: {lrm(today())}"
        body = doc_table(["بەروار", "ڕوونکردنەوە", "بڕ", "پارەی دراو", "ماوە"],
                         [(lrm(r[0]), esc(r[1]), r[2], r[3], r[4]) for r in state["out"]],
                         ["16%", "36%", "16%", "16%", "16%"])
        return (f'<div dir="rtl">{doc_head(title, sub)}{body}'
                f'<p align="left" style="font-size:13pt;font-weight:bold;color:#C0392B;'
                f'margin-top:14pt;">کۆی ماوە: {money(state["bal"])}</p></div>')

    def remove():
        r = sel_row(t)
        if r < 0 or state["rows"][r]["pay"] is None:
            return msg(d, "ڕیزێکی «پارەدان» هەڵبژێرە.\nپسووڵە و کڕین لە بەشی خۆیان دەسڕدرێنەوە.")
        if ask(d, "ئەم پارەدانە بسڕدرێتەوە؟"):
            del_pay(state["rows"][r]["pay"]); load(); app.refresh_all()

    h = QHBoxLayout(); h.setSpacing(8)
    h.addWidget(btn("PDF", lambda: save_pdf(d, html(), "statement.pdf"), ico="pdf"))
    h.addWidget(btn("چاپکردن", lambda: print_html(d, html()), ico="print"))
    h.addWidget(btn("سڕینەوەی پارەدان", remove, "danger"))
    h.addStretch(); h.addWidget(btn("داخستن", d.accept, "primary"))
    v.addLayout(h)
    load()
    d.exec()


def pay_dialog(parent, title, balance, caption="قەرزی ئێستا"):
    """Ask for a payment. Returns (date, amount, note) or None."""
    d = dialog(parent, title); f = form(d)
    dt, am, nt = date_edit(), num(val=max(balance, 0)), QLineEdit()
    f.addRow(caption, label(money(balance), "txtBad" if balance > EPS else "txtGood"))
    f.addRow("بەروار", dt); f.addRow("بڕی پارە", am); f.addRow("تێبینی", nt)
    dlg_buttons(d, f)
    am.setFocus(); am.selectAll()
    if d.exec() and am.value() > 0:
        return dstr(dt), am.value(), nt.text()
    return None


def person_form(parent, title, r=None):
    """Name / phone / address / note — the same for customers and suppliers."""
    d = dialog(parent, title); f = form(d)
    name, ph, ad, nt = QLineEdit(), QLineEdit(), QLineEdit(), QLineEdit()
    ph.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
    if r:
        name.setText(r["name"]); ph.setText(r["phone"] or "")
        ad.setText(r["address"] or ""); nt.setText(r["note"] or "")
    f.addRow("ناو", name); f.addRow("مۆبایل", ph)
    f.addRow("ناونیشان", ad); f.addRow("تێبینی", nt)
    ok = dlg_buttons(d, f)
    ok.setEnabled(bool(name.text().strip()))
    name.textChanged.connect(lambda s: ok.setEnabled(bool(s.strip())))
    if d.exec() and name.text().strip():
        return name.text().strip(), ph.text().strip(), ad.text().strip(), nt.text().strip()
    return None


class PersonCard(PickCard):
    """Customer or supplier tile with the amount still owed."""

    def __init__(self, row, owed_label, clear_text):
        super().__init__(row["id"])
        bal = row["bal"]
        if bal > EPS: badge = ("قەرزدار", "bad")
        elif bal < -EPS: badge = ("پێشەکی", "blue")
        else: badge = (clear_text, "good")
        self.head(row["name"], lrm(row["phone"]) if row["phone"] else "بێ ژمارە",
                  *badge, avatar=True)
        if row["address"]: self.meta(row["address"])
        self.body.addStretch()
        self.sep()
        self.row(owed_label, money(bal), "txtBad" if bal > EPS else "txtGood")


# ---------------------------------------------------------------- کڕیاران
class Customers(QWidget):
    def __init__(self, app):
        super().__init__(); self.app = app
        v = QVBoxLayout(self); v.setSpacing(12); v.setContentsMargins(0, 0, 0, 0)
        top = QHBoxLayout(); top.setSpacing(8)
        top.addWidget(btn("کڕیاری نوێ", self.add, "primary", "plus"))
        top.addWidget(btn("دەستکاری", self.edit))
        top.addWidget(btn("وەرگرتنی پارە", self.pay, ico="cash"))
        top.addWidget(btn("کەشف حساب", self.statement))
        top.addWidget(btn("سڕینەوە", self.rm, "danger"))
        top.addStretch()
        ch, self.flt = chips(["هەموو", "قەرزدار"], self.refresh)
        top.addLayout(ch)
        self.search = search_box("گەڕان بە ناو یان مۆبایل…", self.refresh, 220)
        top.addWidget(self.search)
        v.addLayout(top)
        self.sum_lbl = label("", "hint"); v.addWidget(self.sum_lbl)
        self.grid = CardGrid("هیچ کڕیارێک نەدۆزرایەوە", on_open=self.statement)
        v.addWidget(self.grid, 1)

    def refresh(self):
        rows = db.customers(self.search.text().strip())
        owing = [r for r in rows if r["bal"] > EPS]
        self.sum_lbl.setText(f"{len(rows)} کڕیار   ·   {len(owing)} قەرزدار   ·   "
                             f"کۆی قەرز: {money(sum(r['bal'] for r in owing))}")
        if self.flt.checkedId() == 1: rows = sorted(owing, key=lambda r: -r["bal"])
        self.grid.set_cards([PersonCard(r, "قەرز", "پاک") for r in rows])

    def _picked(self):
        cid = self.grid.selected
        if not cid: msg(self, "سەرەتا کڕیارێک هەڵبژێرە")
        return cid

    def add(self):
        v = person_form(self, "کڕیاری نوێ")
        if v:
            db.x("INSERT INTO customers(name,phone,address,note) VALUES(?,?,?,?)", v)
            self.app.refresh_all(); self.app.toast("کڕیار زیادکرا")

    def edit(self):
        cid = self._picked()
        if not cid: return
        v = person_form(self, "دەستکاری کڕیار", db.one("SELECT * FROM customers WHERE id=?", (cid,)))
        if v:
            db.x("UPDATE customers SET name=?,phone=?,address=?,note=? WHERE id=?", (*v, cid))
            self.app.refresh_all()

    def rm(self):
        cid = self._picked()
        if not cid: return
        if db.val("SELECT COUNT(*) FROM invoices WHERE customer_id=?", (cid,)) or \
           db.val("SELECT COUNT(*) FROM payments WHERE customer_id=?", (cid,)):
            return msg(self, "ناتوانرێت بسڕدرێتەوە — پسووڵە یان پارەدانی تۆمارکراوی هەیە")
        if ask(self, "دڵنیایت لە سڕینەوە؟"):
            db.x("DELETE FROM customers WHERE id=?", (cid,)); self.app.refresh_all()

    def pay(self):
        cid = self._picked()
        if not cid: return
        c = db.one("SELECT * FROM customers WHERE id=?", (cid,))
        r = pay_dialog(self, f"وەرگرتنی پارە — {c['name']}", db.balance(cid))
        if r:
            db.x("INSERT INTO payments(date,customer_id,amount,note) VALUES(?,?,?,?)",
                 (r[0], cid, r[1], r[2]))
            self.app.refresh_all(); self.app.toast(f"{money(r[1])} وەرگیرا")

    def statement(self):
        cid = self._picked()
        if not cid: return
        c = db.one("SELECT * FROM customers WHERE id=?", (cid,))

        def fetch():
            out = [dict(date=i["date"], text=f"پسووڵە #{i['id']}", debit=i["total"],
                        credit=i["paid"], pay=None)
                   for i in db.q("SELECT * FROM invoices WHERE customer_id=?", (cid,))]
            out += [dict(date=p["date"], text="وەرگرتنی پارە" + (f" — {p['note']}" if p["note"] else ""),
                         debit=0, credit=p["amount"], pay=p["id"])
                    for p in db.q("SELECT * FROM payments WHERE customer_id=?", (cid,))]
            return out

        statement(self, self.app, "کەشف حساب", c["name"], fetch,
                  lambda pid: db.x("DELETE FROM payments WHERE id=?", (pid,)))
