# -*- coding: utf-8 -*-
"""مەخزەن، دابینکەران، مەسروفات و مووچە، ڕاپۆرت، ڕێکخستن."""
import os, csv, shutil, datetime

from PyQt6.QtCore import Qt, QDate
from PyQt6.QtWidgets import *

from . import core
from .core import db, fmt, money, usd, today, lrm, esc, pin_hash, save_cfg, APP_DIR
from .theme import T
from .ui import *
from .pages_a import (EPS, PersonCard, person_form, pay_dialog, statement, refill,
                      combo_data, month_start)


# ---------------------------------------------------------------- مەخزەن
class ItemCard(PickCard):
    def __init__(self, row):
        super().__init__(row["id"])
        out = row["qty"] <= EPS
        low = bool(row["minq"]) and row["qty"] <= row["minq"]
        badge = ("نەماوە", "bad") if out else ("کەمە", "warn") if low else (None, "")
        self.head(row["name"], row["kind"] or "", *badge)
        self.sep()
        self.row("بڕی بەردەست", f"{fmt(row['qty'])} {row['unit'] or ''}".strip(),
                 "txtBad" if (out or low) else "txtGood")
        self.row("تێچوو", fmt(row["cost"]), "txtMuted")
        self.row("نرخی فرۆشتن", money(row["price"]), "txtGold")


class Inventory(QWidget):
    def __init__(self, app):
        super().__init__(); self.app = app
        v = QVBoxLayout(self); v.setSpacing(12); v.setContentsMargins(0, 0, 0, 0)
        top = QHBoxLayout(); top.setSpacing(8)
        top.addWidget(btn("کاڵای نوێ", self.add, "primary", "plus"))
        top.addWidget(btn("دەستکاری", self.edit))
        top.addWidget(btn("کڕین / زیادکردنی بڕ", self.purchase, ico="sup"))
        top.addWidget(btn("سڕینەوە", self.rm, "danger"))
        top.addStretch()
        ch, self.flt = chips(["هەموو", "کەمبوو"], self.refresh)
        top.addLayout(ch)
        self.search = search_box("گەڕان بە ناو یان جۆر…", self.refresh, 220)
        top.addWidget(self.search); v.addLayout(top)
        self.sum_lbl = label("", "hint"); v.addWidget(self.sum_lbl)
        self.grid = CardGrid("هیچ کاڵایەک نەدۆزرایەوە", on_open=self.edit)
        v.addWidget(self.grid, 1)

    def refresh(self):
        q = f"%{self.search.text().strip()}%"
        rows = db.q("SELECT * FROM items WHERE name LIKE ? OR IFNULL(kind,'') LIKE ? "
                    "ORDER BY name", (q, q))
        low = [r for r in rows if r["minq"] and r["qty"] <= r["minq"]]
        value = sum(r["qty"] * r["cost"] for r in rows)
        self.sum_lbl.setText(f"{len(rows)} کاڵا   ·   {len(low)} کەمبوو   ·   "
                             f"بەهای مەخزەن: {money(value)}   {usd(value)}")
        self.grid.set_cards([ItemCard(r) for r in (low if self.flt.checkedId() == 1 else rows)])

    def _picked(self):
        i = self.grid.selected
        if not i: msg(self, "سەرەتا کاڵایەک هەڵبژێرە")
        return i

    def form(self, r=None):
        d = dialog(self, "دەستکاری کاڵا" if r else "کاڵای نوێ"); f = form(d)
        name = QLineEdit()
        kind = combo(editable=True)
        kind.addItems([""] + [k["kind"] for k in db.q(
            "SELECT DISTINCT kind FROM items WHERE IFNULL(kind,'')<>'' ORDER BY kind")])
        unit = QLineEdit(); unit.setPlaceholderText("لیتر / کارتۆن / کیلۆ / دانە")
        qty, cost, price, minq = num(dec=2), num(dec=2), num(dec=2), num(dec=2)
        if r:
            name.setText(r["name"]); kind.setCurrentText(r["kind"] or "")
            unit.setText(r["unit"] or ""); qty.setValue(r["qty"])
            cost.setValue(r["cost"]); price.setValue(r["price"]); minq.setValue(r["minq"])
        f.addRow("ناو", name); f.addRow("جۆر", kind); f.addRow("یەکە", unit)
        f.addRow("بڕی ئێستا" if r else "بڕی سەرەتا", qty)
        f.addRow("تێچووی یەکە", cost); f.addRow("نرخی فرۆشتن", price)
        f.addRow("کەمترین بڕ (ئاگاداری)", minq)
        ok = dlg_buttons(d, f)
        ok.setEnabled(bool(name.text().strip()))
        name.textChanged.connect(lambda s: ok.setEnabled(bool(s.strip())))
        if d.exec() and name.text().strip():
            return (name.text().strip(), kind.currentText().strip(), unit.text().strip(),
                    qty.value(), cost.value(), price.value(), minq.value())
        return None

    def add(self):
        v = self.form()
        if v:
            db.x("INSERT INTO items(name,kind,unit,qty,cost,price,minq) VALUES(?,?,?,?,?,?,?)", v)
            self.app.refresh_all(); self.app.toast("کاڵا زیادکرا")

    def edit(self):
        i = self._picked()
        if not i: return
        v = self.form(db.one("SELECT * FROM items WHERE id=?", (i,)))
        if v:
            db.x("UPDATE items SET name=?,kind=?,unit=?,qty=?,cost=?,price=?,minq=? WHERE id=?",
                 (*v, i))
            self.app.refresh_all()

    def rm(self):
        i = self._picked()
        if not i: return
        if db.val("SELECT COUNT(*) FROM invoice_items WHERE item_id=?", (i,)) or \
           db.val("SELECT COUNT(*) FROM purchases WHERE item_id=?", (i,)):
            return msg(self, "ناتوانرێت بسڕدرێتەوە — ئەم کاڵایە لە پسووڵە یان کڕیندا بەکارهاتووە")
        if ask(self, "دڵنیایت لە سڕینەوە؟"):
            db.x("DELETE FROM items WHERE id=?", (i,)); self.app.refresh_all()

    def purchase(self):
        i = self._picked()
        if not i: return
        it = db.one("SELECT * FROM items WHERE id=?", (i,))
        d = dialog(self, f"کڕین — {it['name']}", 460); f = form(d)
        dt, sup, nt = date_edit(), combo(editable=True), QLineEdit()
        sup.addItems([""] + [s["name"] for s in db.q("SELECT name FROM suppliers ORDER BY name")])
        sup.lineEdit().setPlaceholderText("ناوی دابینکەر (نوێ بێت خۆی تۆمار دەبێت)")
        qty, pr, paid = num(dec=2), num(dec=2, val=it["cost"]), num(dec=2)
        total = label("0", "txtGold")
        auto = {"on": True}          # «پارەی دراو» follows the total until it is typed in

        def calc():
            t = qty.value() * pr.value()
            total.setText(money(t)); paid.setMaximum(t)
            if auto["on"]:
                paid.blockSignals(True); paid.setValue(t); paid.blockSignals(False)

        qty.valueChanged.connect(lambda _: calc()); pr.valueChanged.connect(lambda _: calc())
        paid.valueChanged.connect(lambda _: auto.update(on=False))
        f.addRow("بەروار", dt); f.addRow("دابینکەر", sup)
        f.addRow(f"بڕ ({it['unit'] or 'یەکە'})", qty); f.addRow("نرخی یەکە", pr)
        f.addRow("کۆی کڕین", total); f.addRow("پارەی دراو", paid)
        f.addRow("", label("ئەوەی نەدرێت دەچێتە سەر قەرزی دابینکەرەکە.", "hint"))
        f.addRow("تێبینی", nt)
        dlg_buttons(d, f); calc(); qty.setFocus(); qty.selectAll()
        if not (d.exec() and qty.value() > 0): return
        name = sup.currentText().strip()
        t = qty.value() * pr.value()
        if not name and paid.value() < t - EPS:
            return msg(self, "بۆ کڕینی قەرز پێویستە ناوی دابینکەر بنووسیت")
        oq, oc = max(it["qty"], 0), it["cost"]
        nq = it["qty"] + qty.value()
        # weighted average cost of what is on the shelf after this delivery
        nc = ((oq * oc) + t) / (oq + qty.value())
        with db.con:
            sid = db.supplier_id(name)
            db.run("UPDATE items SET qty=?, cost=? WHERE id=?", (nq, nc, i))
            db.run("INSERT INTO purchases(date,supplier,supplier_id,item_id,qty,price,paid,note) "
                   "VALUES(?,?,?,?,?,?,?,?)",
                   (dstr(dt), name, sid, i, qty.value(), pr.value(), paid.value(), nt.text()))
        self.app.refresh_all(); self.app.toast("کڕینەکە تۆمارکرا")


# ---------------------------------------------------------------- دابینکەران
class Suppliers(QWidget):
    def __init__(self, app):
        super().__init__(); self.app = app
        v = QVBoxLayout(self); v.setContentsMargins(0, 0, 0, 0)
        self.tabs = QTabWidget(); v.addWidget(self.tabs)
        self.tabs.currentChanged.connect(lambda _: self.refresh())

        w1 = QWidget(); v1 = QVBoxLayout(w1); v1.setSpacing(12); v1.setContentsMargins(0, 14, 0, 0)
        top = QHBoxLayout(); top.setSpacing(8)
        top.addWidget(btn("دابینکەری نوێ", self.add, "primary", "plus"))
        top.addWidget(btn("دەستکاری", self.edit))
        top.addWidget(btn("دانی پارە", self.pay, ico="cash"))
        top.addWidget(btn("کەشف حساب", self.statement))
        top.addWidget(btn("سڕینەوە", self.rm, "danger"))
        top.addStretch()
        self.search = search_box("گەڕان بە ناو یان مۆبایل…", self.refresh, 220)
        top.addWidget(self.search); v1.addLayout(top)
        self.sum_lbl = label("", "hint"); v1.addWidget(self.sum_lbl)
        self.grid = CardGrid("هێشتا هیچ دابینکەرێک تۆمار نەکراوە.\n"
                             "لە مەخزەن، لە کاتی «کڕین»دا ناوی دابینکەر بنووسە.",
                             on_open=self.statement)
        v1.addWidget(self.grid, 1)
        self.tabs.addTab(w1, "دابینکەران")

        w2 = QWidget(); v2 = QVBoxLayout(w2); v2.setSpacing(12); v2.setContentsMargins(0, 14, 0, 0)
        h = QHBoxLayout()
        self.pur_sum = label("", "hint"); h.addWidget(self.pur_sum); h.addStretch()
        h.addWidget(btn("سڕینەوەی کڕین", self.rm_purchase, "danger"))
        v2.addLayout(h)
        self.pt = table(["#", "بەروار", "دابینکەر", "کاڵا", "بڕ", "نرخ", "کۆ", "دراو", "ماوە"], stretch=3)
        v2.addWidget(self.pt, 1)
        self.tabs.addTab(w2, "مێژووی کڕین")

    def refresh(self):
        if self.tabs.currentIndex() == 0:
            rows = db.suppliers(self.search.text().strip())
            owed = sum(r["bal"] for r in rows if r["bal"] > EPS)
            self.sum_lbl.setText(f"{len(rows)} دابینکەر   ·   کۆی قەرزی سەر دووکان: {money(owed)}")
            self.grid.set_cards([PersonCard(r, "قەرزمان لایە", "پاک") for r in rows])
        else:
            rows = db.q("SELECT p.*, IFNULL(s.name, IFNULL(p.supplier,'')) sn, IFNULL(i.name,'—') iname "
                        "FROM purchases p LEFT JOIN suppliers s ON s.id=p.supplier_id "
                        "LEFT JOIN items i ON i.id=p.item_id ORDER BY p.id DESC LIMIT 400")
            fill(self.pt, [(f"#{r['id']}", r["date"], r["sn"] or "—", r["iname"], fmt(r["qty"]),
                            fmt(r["price"]), fmt(r["qty"] * r["price"]), fmt(r["paid"] or 0),
                            fmt(r["qty"] * r["price"] - (r["paid"] or 0))) for r in rows],
                 {8: lambda r: T.RED if r[8] != "0" else T.FAINT})
            m = month_start().isoformat()
            self.pur_sum.setText("کڕینی ئەم مانگە:  " + money(db.val(
                "SELECT SUM(qty*price) FROM purchases WHERE date>=?", (m,))))

    def _picked(self):
        sid = self.grid.selected
        if not sid: msg(self, "سەرەتا دابینکەرێک هەڵبژێرە")
        return sid

    def add(self):
        v = person_form(self, "دابینکەری نوێ")
        if v:
            db.x("INSERT INTO suppliers(name,phone,address,note) VALUES(?,?,?,?)", v)
            self.app.refresh_all(); self.app.toast("دابینکەر زیادکرا")

    def edit(self):
        sid = self._picked()
        if not sid: return
        v = person_form(self, "دەستکاری دابینکەر", db.one("SELECT * FROM suppliers WHERE id=?", (sid,)))
        if v:
            db.x("UPDATE suppliers SET name=?,phone=?,address=?,note=? WHERE id=?", (*v, sid))
            self.app.refresh_all()

    def rm(self):
        sid = self._picked()
        if not sid: return
        if db.val("SELECT COUNT(*) FROM purchases WHERE supplier_id=?", (sid,)) or \
           db.val("SELECT COUNT(*) FROM supplier_payments WHERE supplier_id=?", (sid,)):
            return msg(self, "ناتوانرێت بسڕدرێتەوە — کڕین یان پارەدانی تۆمارکراوی هەیە")
        if ask(self, "دڵنیایت لە سڕینەوە؟"):
            db.x("DELETE FROM suppliers WHERE id=?", (sid,)); self.app.refresh_all()

    def pay(self):
        sid = self._picked()
        if not sid: return
        s = db.one("SELECT * FROM suppliers WHERE id=?", (sid,))
        r = pay_dialog(self, f"دانی پارە — {s['name']}", db.supplier_balance(sid), "قەرزمان لایە")
        if r:
            db.x("INSERT INTO supplier_payments(date,supplier_id,amount,note) VALUES(?,?,?,?)",
                 (r[0], sid, r[1], r[2]))
            self.app.refresh_all(); self.app.toast(f"{money(r[1])} درا")

    def statement(self):
        sid = self._picked()
        if not sid: return
        s = db.one("SELECT * FROM suppliers WHERE id=?", (sid,))

        def fetch():
            out = [dict(date=p["date"], text=f"کڕین — {p['iname']} × {fmt(p['qty'])}",
                        debit=p["qty"] * p["price"], credit=p["paid"] or 0, pay=None)
                   for p in db.q("SELECT p.*, IFNULL(i.name,'—') iname FROM purchases p "
                                 "LEFT JOIN items i ON i.id=p.item_id WHERE p.supplier_id=?", (sid,))]
            out += [dict(date=p["date"], text="دانی پارە" + (f" — {p['note']}" if p["note"] else ""),
                         debit=0, credit=p["amount"], pay=p["id"])
                    for p in db.q("SELECT * FROM supplier_payments WHERE supplier_id=?", (sid,))]
            return out

        statement(self, self.app, "کەشف حسابی دابینکەر", s["name"], fetch,
                  lambda pid: db.x("DELETE FROM supplier_payments WHERE id=?", (pid,)))

    def rm_purchase(self):
        pid = picked_id(self.pt)
        if not pid: return msg(self, "سەرەتا کڕینێک هەڵبژێرە")
        p = db.one("SELECT * FROM purchases WHERE id=?", (pid,))
        it = db.one("SELECT * FROM items WHERE id=?", (p["item_id"],))
        text = "ئەم کڕینە بسڕدرێتەوە؟ بڕەکەی لە مەخزەن کەم دەکرێتەوە."
        if it and it["qty"] - p["qty"] < -EPS:
            text += f"\n\nئاگاداری: بەشێکی فرۆشراوە — بڕی مەخزەن دەبێتە {fmt(it['qty'] - p['qty'])}."
        if not ask(self, text): return
        with db.con:
            if it:
                nq = it["qty"] - p["qty"]
                cost = it["cost"]
                if nq > EPS:      # undo this delivery's share of the average cost
                    cost = max(0.0, (it["qty"] * it["cost"] - p["qty"] * p["price"]) / nq)
                db.run("UPDATE items SET qty=?, cost=? WHERE id=?", (nq, cost, it["id"]))
            db.run("DELETE FROM purchases WHERE id=?", (pid,))
        self.app.refresh_all(); self.app.toast("کڕینەکە سڕایەوە")


# ---------------------------------------------------------------- مەسروفات و مووچە
class ExpenseCard(PickCard):
    def __init__(self, row):
        super().__init__(row["id"])
        self.head(row["category"] or "—", lrm(row["date"]))
        if row["note"]: self.meta(row["note"])
        self.body.addStretch()
        self.sep()
        self.row("بڕ", money(row["amount"]), "txtGold")


class EmployeeCard(PickCard):
    def __init__(self, row):
        super().__init__(row["id"])
        paid = row["paid"] or 0
        badge = ("مووچەی ئەم مانگە دراوە", "good") if paid >= (row["salary"] or 0) - EPS and paid > 0 \
            else ("بەشێکی دراوە", "warn") if paid > 0 else ("مووچە نەدراوە", "bad")
        self.head(row["name"], row["position"] or "", avatar=True)
        self.body.addWidget(pill(*badge))
        if row["phone"]: self.meta(lrm(row["phone"]))
        self.body.addStretch()
        self.sep()
        self.row("مووچەی مانگانە", money(row["salary"]), "txtGold")


class Expenses(QWidget):
    CATS = ["کارەبا", "سووتەمەنی", "کرێ", "گواستنەوە", "چاککردنەوە", "بازرگانی", "هیتر"]

    def __init__(self, app):
        super().__init__(); self.app = app
        v = QVBoxLayout(self); v.setContentsMargins(0, 0, 0, 0)
        self.tabs = QTabWidget(); v.addWidget(self.tabs)
        self.tabs.currentChanged.connect(lambda _: self.refresh())

        w1 = QWidget(); v1 = QVBoxLayout(w1); v1.setSpacing(12); v1.setContentsMargins(0, 14, 0, 0)
        h = QHBoxLayout(); h.setSpacing(8)
        h.addWidget(btn("مەسروفی نوێ", self.add_exp, "primary", "plus"))
        h.addWidget(btn("دەستکاری", self.edit_exp))
        h.addWidget(btn("سڕینەوە", self.rm_exp, "danger"))
        h.addStretch()
        ch, self.flt = chips(["هەموو", "ئەم مانگە"], self.refresh, 1)
        h.addLayout(ch)
        self.search = search_box("گەڕان بە جۆر یان تێبینی…", self.refresh, 220)
        h.addWidget(self.search); v1.addLayout(h)
        self.sum_lbl = label("", "hint"); v1.addWidget(self.sum_lbl)
        self.eg = CardGrid("هیچ مەسروفێک نەدۆزرایەوە", min_w=225, on_open=self.edit_exp)
        v1.addWidget(self.eg, 1)
        self.tabs.addTab(w1, "مەسروفات")

        w2 = QWidget(); v2 = QVBoxLayout(w2); v2.setSpacing(12); v2.setContentsMargins(0, 14, 0, 0)
        h2 = QHBoxLayout(); h2.setSpacing(8)
        h2.addWidget(btn("کارمەندی نوێ", self.add_emp, "primary", "plus"))
        h2.addWidget(btn("دەستکاری", self.edit_emp))
        h2.addWidget(btn("دانی مووچە", self.pay_sal, ico="cash"))
        h2.addWidget(btn("سڕینەوە", self.rm_emp, "danger"))
        h2.addStretch(); v2.addLayout(h2)
        self.mg = CardGrid("هێشتا هیچ کارمەندێک تۆمار نەکراوە", on_open=self.edit_emp)
        v2.addWidget(self.mg, 3)
        h3 = QHBoxLayout()
        h3.addWidget(label("مووچە دراوەکان", "panelTitle")); h3.addStretch()
        h3.addWidget(btn("سڕینەوەی مووچە", self.rm_sal, "danger"))
        v2.addLayout(h3)
        self.st = table(["#", "بەروار", "کارمەند", "بڕ", "تێبینی"], stretch=4)
        v2.addWidget(self.st, 2)
        self.tabs.addTab(w2, "کارمەندان و مووچە")

    def refresh(self):
        m = month_start().isoformat()
        if self.tabs.currentIndex() == 0:
            s = f"%{self.search.text().strip()}%"
            where, p = "(IFNULL(category,'') LIKE ? OR IFNULL(note,'') LIKE ?)", [s, s]
            if self.flt.checkedId() == 1: where += " AND date>=?"; p.append(m)
            rows = db.q(f"SELECT * FROM expenses WHERE {where} ORDER BY date DESC, id DESC LIMIT 300", p)
            tot = db.val(f"SELECT SUM(amount) FROM expenses WHERE {where}", p)
            self.sum_lbl.setText(f"{len(rows)} تۆمار   ·   کۆ: {money(tot)}")
            self.eg.set_cards([ExpenseCard(r) for r in rows])
        else:
            self.mg.set_cards([EmployeeCard(r) for r in db.q(
                "SELECT e.*, (SELECT SUM(amount) FROM salaries WHERE employee_id=e.id AND date>=?) paid "
                "FROM employees e ORDER BY e.name", (m,))])
            fill(self.st, [(f"#{r['id']}", r["date"], r["n"], fmt(r["amount"]), r["note"] or "—")
                           for r in db.q("SELECT s.*, IFNULL(e.name,'—') n FROM salaries s "
                                         "LEFT JOIN employees e ON e.id=s.employee_id "
                                         "ORDER BY s.date DESC, s.id DESC LIMIT 200")])

    # ---- مەسروف ----
    def exp_form(self, r=None):
        d = dialog(self, "مەسروف"); f = form(d)
        dt, cat, am, nt = date_edit(), combo(editable=True), num(), QLineEdit()
        used = [c["category"] for c in db.q(
            "SELECT DISTINCT category FROM expenses WHERE IFNULL(category,'')<>''")]
        cat.addItems(self.CATS + [c for c in used if c not in self.CATS])
        if r:
            dt.setDate(QDate.fromString(r["date"], "yyyy-MM-dd"))
            cat.setCurrentText(r["category"] or ""); am.setValue(r["amount"]); nt.setText(r["note"] or "")
        f.addRow("بەروار", dt); f.addRow("جۆر", cat); f.addRow("بڕ", am); f.addRow("تێبینی", nt)
        dlg_buttons(d, f); am.setFocus(); am.selectAll()
        if d.exec() and am.value() > 0:
            return dstr(dt), cat.currentText().strip() or "هیتر", am.value(), nt.text()
        return None

    def add_exp(self):
        v = self.exp_form()
        if v:
            db.x("INSERT INTO expenses(date,category,amount,note) VALUES(?,?,?,?)", v)
            self.app.refresh_all(); self.app.toast("مەسروفەکە تۆمارکرا")

    def edit_exp(self):
        i = self.eg.selected
        if not i: return msg(self, "سەرەتا مەسروفێک هەڵبژێرە")
        v = self.exp_form(db.one("SELECT * FROM expenses WHERE id=?", (i,)))
        if v:
            db.x("UPDATE expenses SET date=?,category=?,amount=?,note=? WHERE id=?", (*v, i))
            self.app.refresh_all()

    def rm_exp(self):
        i = self.eg.selected
        if not i: return msg(self, "سەرەتا مەسروفێک هەڵبژێرە")
        if ask(self, "بسڕدرێتەوە؟"):
            db.x("DELETE FROM expenses WHERE id=?", (i,)); self.app.refresh_all()

    # ---- کارمەند ----
    def emp_form(self, r=None):
        d = dialog(self, "کارمەند"); f = form(d)
        n, p, s, ph = QLineEdit(), QLineEdit(), num(), QLineEdit()
        ph.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        if r:
            n.setText(r["name"]); p.setText(r["position"] or "")
            s.setValue(r["salary"] or 0); ph.setText(r["phone"] or "")
        f.addRow("ناو", n); f.addRow("پۆست", p)
        f.addRow("مووچەی مانگانە", s); f.addRow("مۆبایل", ph)
        dlg_buttons(d, f)
        if d.exec() and n.text().strip():
            return n.text().strip(), p.text().strip(), s.value(), ph.text().strip()
        return None

    def add_emp(self):
        v = self.emp_form()
        if v:
            db.x("INSERT INTO employees(name,position,salary,phone) VALUES(?,?,?,?)", v)
            self.app.refresh_all(); self.app.toast("کارمەند زیادکرا")

    def edit_emp(self):
        i = self.mg.selected
        if not i: return msg(self, "سەرەتا کارمەندێک هەڵبژێرە")
        v = self.emp_form(db.one("SELECT * FROM employees WHERE id=?", (i,)))
        if v:
            db.x("UPDATE employees SET name=?,position=?,salary=?,phone=? WHERE id=?", (*v, i))
            self.app.refresh_all()

    def rm_emp(self):
        i = self.mg.selected
        if not i: return msg(self, "سەرەتا کارمەندێک هەڵبژێرە")
        if ask(self, "کارمەندەکە بسڕدرێتەوە؟\nمووچە دراوەکانی لە ڕاپۆرتدا دەمێننەوە."):
            db.x("DELETE FROM employees WHERE id=?", (i,)); self.app.refresh_all()

    def pay_sal(self):
        i = self.mg.selected
        if not i: return msg(self, "سەرەتا کارمەندێک هەڵبژێرە")
        e = db.one("SELECT * FROM employees WHERE id=?", (i,))
        d = dialog(self, f"مووچە — {e['name']}"); f = form(d)
        dt, am, nt = date_edit(), num(val=e["salary"] or 0), QLineEdit()
        f.addRow("بەروار", dt); f.addRow("بڕ", am); f.addRow("تێبینی", nt)
        dlg_buttons(d, f)
        if d.exec() and am.value() > 0:
            db.x("INSERT INTO salaries(date,employee_id,amount,note) VALUES(?,?,?,?)",
                 (dstr(dt), i, am.value(), nt.text()))
            self.app.refresh_all(); self.app.toast("مووچەکە تۆمارکرا")

    def rm_sal(self):
        i = picked_id(self.st)
        if not i: return msg(self, "سەرەتا ڕیزێکی مووچە هەڵبژێرە")
        if ask(self, "ئەم مووچەیە بسڕدرێتەوە؟"):
            db.x("DELETE FROM salaries WHERE id=?", (i,)); self.app.refresh_all()


# ---------------------------------------------------------------- ڕاپۆرت
class Reports(QWidget):
    def __init__(self, app):
        super().__init__(); self.app = app
        v = QVBoxLayout(self); v.setSpacing(12); v.setContentsMargins(0, 0, 0, 0)
        h = QHBoxLayout(); h.setSpacing(8)
        ch, self.preset = chips(["ئەمڕۆ", "٧ ڕۆژ", "ئەم مانگە", "ئەم ساڵ"], self.apply_preset, 2)
        h.addLayout(ch); h.addSpacing(8)
        self.f, self.t = date_edit(), date_edit()
        h.addWidget(label("لە", "cardMeta")); h.addWidget(self.f)
        h.addWidget(label("بۆ", "cardMeta")); h.addWidget(self.t)
        h.addStretch()
        h.addWidget(btn("PDF", self.pdf, ico="pdf"))
        h.addWidget(btn("چاپکردن", lambda: print_html(self, self.html()), ico="print"))
        h.addWidget(btn("CSV", self.csv))
        v.addLayout(h)

        g = QHBoxLayout(); g.setSpacing(12)
        self.c = {}
        for k, cap, accent, ico in [("sales", "کۆی فرۆشتن", "BLUE", "sale"),
                                    ("gross", "قازانجی خاو", "GREEN", "trend"),
                                    ("costs", "مەسروفات و مووچە", "RED", "exp"),
                                    ("net", "قازانجی سافی", "GOLD", "cash")]:
            self.c[k] = StatCard(cap, accent, ico); g.addWidget(self.c[k])
        v.addLayout(g)

        row = QHBoxLayout(); row.setSpacing(12)
        box, bv = card("فرۆشتن بەپێی کات")
        self.chart = BarChart(); bv.addWidget(self.chart, 1)
        row.addWidget(box, 4)
        b2, v2 = card("باشترین کاڵاکان", margins=(18, 16, 18, 8), spacing=6)
        self.top_items = table(["کاڵا", "بڕ", "فرۆشتن", "قازانج"], stretch=0, flat=True)
        v2.addWidget(self.top_items, 1); row.addWidget(b2, 5)
        b3, v3 = card("باشترین کڕیاران", margins=(18, 16, 18, 8), spacing=6)
        self.top_cust = table(["کڕیار", "پسووڵە", "کۆ"], stretch=0, flat=True)
        v3.addWidget(self.top_cust, 1); row.addWidget(b3, 4)
        v.addLayout(row, 1)

        self.apply_preset()
        self.f.dateChanged.connect(lambda _: self.run())
        self.t.dateChanged.connect(lambda _: self.run())

    def apply_preset(self):
        t = QDate.currentDate()
        a = [t, t.addDays(-6), QDate(t.year(), t.month(), 1), QDate(t.year(), 1, 1)][self.preset.checkedId()]
        for w, d in ((self.f, a), (self.t, t)):
            w.blockSignals(True); w.setDate(d); w.blockSignals(False)
        self.run()

    def refresh(self): self.run()

    def _range(self):
        return dstr(self.f), dstr(self.t)

    def _data(self):
        a, b = self._range()
        items = db.q("SELECT IFNULL(it.name,'—') n, SUM(ii.qty) q, SUM(ii.qty*ii.price) v, "
                     "SUM(ii.qty*(ii.price-ii.cost)) pr FROM invoice_items ii "
                     "JOIN invoices i ON i.id=ii.invoice_id LEFT JOIN items it ON it.id=ii.item_id "
                     "WHERE i.date BETWEEN ? AND ? GROUP BY ii.item_id ORDER BY v DESC LIMIT 15", (a, b))
        custs = db.q("SELECT IFNULL(c.name,'کڕیاری نەقد') n, COUNT(*) k, SUM(i.total) v FROM invoices i "
                     "LEFT JOIN customers c ON c.id=i.customer_id WHERE i.date BETWEEN ? AND ? "
                     "GROUP BY i.customer_id ORDER BY v DESC LIMIT 15", (a, b))
        return db.period(a, b), items, custs

    def run(self):
        a, b = self._range()
        p, items, custs = self._data()
        self.c["sales"].set(money(p["sales"]), f"{p['count']} پسووڵە   {usd(p['sales'])}")
        self.c["gross"].set(money(p["gross"]), f"تێچووی کاڵا: {fmt(p['cogs'])}")
        self.c["costs"].set(money(p["exp"] + p["sal"]),
                            f"مەسروف {fmt(p['exp'])}  ·  مووچە {fmt(p['sal'])}")
        self.c["net"].set(money(p["net"]), f"کڕینی کاڵا: {fmt(p['pur'])}")
        fill(self.top_items, [(r["n"], fmt(r["q"]), fmt(r["v"]), fmt(r["pr"])) for r in items])
        fill(self.top_cust, [(r["n"], r["k"], fmt(r["v"])) for r in custs])

        cur = db.get("currency")
        d0, d1 = datetime.date.fromisoformat(a), datetime.date.fromisoformat(b)
        if (d1 - d0).days <= 45:
            got = {r["k"]: r["t"] for r in db.q(
                "SELECT date k, SUM(total) t FROM invoices WHERE date BETWEEN ? AND ? GROUP BY date", (a, b))}
            days = [d0 + datetime.timedelta(days=i) for i in range(max((d1 - d0).days, 0) + 1)]
            data = [(f"{d.day}/{d.month}", got.get(d.isoformat(), 0),
                     f"{lrm(d.isoformat())}\n{fmt(got.get(d.isoformat(), 0))} {cur}") for d in days]
        else:
            got = {r["k"]: r["t"] for r in db.q(
                "SELECT substr(date,1,7) k, SUM(total) t FROM invoices WHERE date BETWEEN ? AND ? "
                "GROUP BY k", (a, b))}
            keys, y, m = [], d0.year, d0.month
            while (y, m) <= (d1.year, d1.month):
                keys.append(f"{y:04d}-{m:02d}")
                m += 1
                if m == 13: y, m = y + 1, 1
            data = [(f"{int(k[5:])}/{k[2:4]}", got.get(k, 0),
                     f"{lrm(k)}\n{fmt(got.get(k, 0))} {cur}") for k in keys]
        self.chart.set_data(data)

    def html(self):
        a, b = self._range()
        p, items, custs = self._data()
        cur = esc(db.get("currency"))
        debts = sorted([c for c in db.customers() if c["bal"] > EPS], key=lambda c: -c["bal"])
        low = db.q("SELECT * FROM items WHERE minq>0 AND qty<=minq")

        def line(lbl, v, bold=False):
            w = "font-weight:bold;background-color:#FAF5E8;" if bold else ""
            return (f"<tr><td style='{w}padding:6px 12px;'>{lbl}</td>"
                    f"<td align='left' style='{w}padding:6px 12px;'>{fmt(v)} {cur}</td></tr>")

        def h2(t):
            return f"<p style='font-size:12pt;font-weight:bold;color:#B8860B;margin-top:16pt;'>{t}</p>"

        return f"""<div dir="rtl">{doc_head("ڕاپۆرتی گشتی", f"{lrm(a)} &nbsp;تا&nbsp; {lrm(b)}")}
        <table width="100%" cellspacing="0" cellpadding="0" style="font-size:11pt;">
        {line(f"کۆی فرۆشتن — {p['count']} پسووڵە", p["sales"], True)}
        {line("تێچووی کاڵای فرۆشراو", p["cogs"])}{line("قازانجی خاو", p["gross"], True)}
        {line("مەسروفات", p["exp"])}{line("مووچەکان", p["sal"])}
        {line("قازانجی سافی", p["net"], True)}{line("کڕینی کاڵا", p["pur"])}</table>
        {h2("باشترین کاڵا فرۆشراوەکان")}
        {doc_table(["کاڵا", "بڕ", "فرۆشتن", "قازانج"],
                   [(esc(r["n"]), fmt(r["q"]), fmt(r["v"]), fmt(r["pr"])) for r in items])}
        {h2("باشترین کڕیاران")}
        {doc_table(["کڕیار", "پسووڵە", "کۆ"], [(esc(r["n"]), r["k"], fmt(r["v"])) for r in custs])}
        {h2("قەرزی کڕیاران")}
        {doc_table(["کڕیار", "مۆبایل", "قەرز"],
                   [(esc(c["name"]), esc(lrm(c["phone"] or "")), fmt(c["bal"])) for c in debts])}
        {h2("کاڵای کەمبوو")}
        {doc_table(["کاڵا", "بڕی ماوە", "کەمترین بڕ"],
                   [(esc(r["name"]), fmt(r["qty"]), fmt(r["minq"])) for r in low])}</div>"""

    def pdf(self):
        if save_pdf(self, self.html(), f"report_{dstr(self.t)}.pdf"):
            self.app.toast("ڕاپۆرتەکە پاشەکەوتکرا")

    def csv(self):
        p = QFileDialog.getExistingDirectory(self, "فۆڵدەری پاشەکەوت", APP_DIR)
        if not p: return
        a, b = self._range()

        def write(name, head, rows):
            with open(os.path.join(p, name), "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f); w.writerow(head); w.writerows(rows)

        try:
            write("inventory.csv", ["ناو", "جۆر", "یەکە", "بڕ", "تێچوو", "نرخ"],
                  [[r["name"], r["kind"], r["unit"], r["qty"], r["cost"], r["price"]]
                   for r in db.q("SELECT * FROM items ORDER BY name")])
            write("debts.csv", ["کڕیار", "مۆبایل", "قەرز"],
                  [[c["name"], c["phone"], c["bal"]] for c in db.customers()])
            write("suppliers.csv", ["دابینکەر", "مۆبایل", "قەرز"],
                  [[s["name"], s["phone"], s["bal"]] for s in db.suppliers()])
            write("invoices.csv", ["ژمارە", "بەروار", "کڕیار", "کۆ", "داشکاندن", "دوای داشکاندن", "دراو"],
                  [[r["id"], r["date"], r["cn"], r["subtotal"], r["discount"], r["total"], r["paid"]]
                   for r in db.q("SELECT i.*, IFNULL(c.name,'کڕیاری نەقد') cn FROM invoices i "
                                 "LEFT JOIN customers c ON c.id=i.customer_id "
                                 "WHERE i.date BETWEEN ? AND ? ORDER BY i.id", (a, b))])
            write("expenses.csv", ["بەروار", "جۆر", "بڕ", "تێبینی"],
                  [[r["date"], r["category"], r["amount"], r["note"]] for r in db.q(
                      "SELECT * FROM expenses WHERE date BETWEEN ? AND ? ORDER BY date", (a, b))])
        except Exception as e:
            return msg(self, f"نەتوانرا هەناردە بکرێت:\n{e}")
        self.app.toast("٥ فایلی CSV هەناردەکران")


# ---------------------------------------------------------------- ڕێکخستن
class Settings(QWidget):
    def __init__(self, app):
        super().__init__(); self.app = app
        outer = QVBoxLayout(self); outer.setContentsMargins(0, 0, 0, 0)
        g = QGridLayout(); g.setSpacing(12)

        b1, v1 = card("زانیاری دووکان")
        f = QFormLayout(); f.setSpacing(11)
        self.co, self.ph, self.ad = QLineEdit(), QLineEdit(), QLineEdit()
        self.ph.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.cu, self.usd = QLineEdit(), num(1e6, 2)
        f.addRow("ناوی دووکان", self.co); f.addRow("مۆبایل", self.ph)
        f.addRow("ناونیشان", self.ad); f.addRow("دراو", self.cu)
        f.addRow("نرخی ١ دۆلار", self.usd)
        v1.addLayout(f)
        v1.addWidget(label("ئەم زانیارییانە لەسەر پسووڵە و ڕاپۆرتە چاپکراوەکان دەردەکەون. "
                           "نرخی دۆلار بۆ پیشاندانی بەهای نزیکەیی بە دۆلار بەکاردێت.", "hint", wrap=True))
        v1.addStretch()
        v1.addWidget(btn("پاشەکەوتکردن", self.save, "primary"))
        g.addWidget(b1, 0, 0, 2, 1)

        b4, v4 = card("پاراستن")
        self.pin_lbl = label("", "cardMeta", wrap=True); v4.addWidget(self.pin_lbl)
        hp = QHBoxLayout(); hp.setSpacing(8)
        self.pin_set = btn("دانانی ژمارەی نهێنی", self.set_pin, ico="lock")
        self.pin_rm = btn("لابردنی قفڵ", self.rm_pin, "danger")
        hp.addWidget(self.pin_set); hp.addWidget(self.pin_rm); hp.addStretch()
        v4.addLayout(hp); v4.addStretch()
        g.addWidget(b4, 0, 1)

        b2, v2 = card("باکئەپ")
        self.bl = label("", "cardMeta", wrap=True); v2.addWidget(self.bl)
        v2.addWidget(label("فۆڵدەرێکی هاوبەش یان فۆڵدەری کلاودی سەر کۆمپیوتەرەکەت هەڵبژێرە. هەر جارێک "
                           "بەرنامەکە دادەخرێت کۆپییەک دەنێردرێت و ٢٠ دانەی دوایی هەڵدەگیرێن.",
                           "hint", wrap=True))
        hb = QHBoxLayout(); hb.setSpacing(8)
        hb.addWidget(btn("هەڵبژاردنی فۆڵدەر", self.pick))
        hb.addWidget(btn("باکئەپی ئێستا", self.backup, "primary"))
        hb.addWidget(btn("گەڕاندنەوە", self.restore, "danger")); hb.addStretch()
        v2.addLayout(hb); v2.addStretch()
        g.addWidget(b2, 0, 2)

        b3, v3 = card("شوێنی داتابەیس")
        self.dbl = label("", "cardMeta", wrap=True)
        self.dbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        v3.addWidget(self.dbl)
        v3.addWidget(label("ئەگەر دەتەوێت چەند کۆمپیوتەرێکی دووکان هەمان داتا بەکاربهێنن، "
                           "لە هەموویان هەمان فۆڵدەری هاوبەش دیاری بکە.", "hint", wrap=True))
        hd = QHBoxLayout(); hd.addWidget(btn("گۆڕینی شوێن", self.move_db)); hd.addStretch()
        v3.addLayout(hd); v3.addStretch()
        g.addWidget(b3, 1, 1, 1, 2)

        for c in range(3): g.setColumnStretch(c, 1)
        outer.addLayout(g); outer.addStretch()

    def refresh(self):
        self.co.setText(db.get("company")); self.ph.setText(db.get("phone"))
        self.ad.setText(db.get("address")); self.cu.setText(db.get("currency"))
        self.usd.setValue(float(db.get("usd") or 0))
        p = db.get("backup")
        self.bl.setText(f"فۆڵدەری ئێستا:  {p}" if p else "هێشتا فۆڵدەری باکئەپ دیاری نەکراوە.")
        self.dbl.setText(core.DB_PATH)
        on = bool(db.get("pin"))
        self.pin_lbl.setText("قفڵ چالاکە — لە کاتی کردنەوەی بەرنامەکە ژمارەی نهێنی دەپرسرێت." if on else
                             "قفڵ ناچالاکە — هەر کەسێک دەتوانێت بەرنامەکە بکاتەوە.")
        self.pin_set.setText("گۆڕینی ژمارەی نهێنی" if on else "دانانی ژمارەی نهێنی")
        self.pin_rm.setVisible(on)

    def save(self):
        if not self.co.text().strip(): return msg(self, "ناوی دووکان پێویستە")
        for k, w in [("company", self.co), ("phone", self.ph),
                     ("address", self.ad), ("currency", self.cu)]:
            db.set(k, w.text().strip())
        db.set("usd", self.usd.value()); self.app.refresh_all(); self.app.toast("پاشەکەوتکرا")

    # ---- قفڵ ----
    def _ask_pin(self, title, twice=False):
        d = dialog(self, title, 360); f = form(d)
        a, b = QLineEdit(), QLineEdit()
        for w in (a, b):
            w.setEchoMode(QLineEdit.EchoMode.Password)
            w.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        f.addRow("ژمارەی نهێنی", a)
        if twice: f.addRow("دووبارە", b)
        dlg_buttons(d, f, "باشە")
        if not d.exec(): return None
        if twice and a.text() != b.text():
            msg(self, "دوو ژمارەکە وەک یەک نین"); return None
        return a.text()

    def set_pin(self):
        if db.get("pin"):
            old = self._ask_pin("ژمارەی نهێنی ئێستا")
            if old is None: return
            if pin_hash(old) != db.get("pin"): return msg(self, "ژمارەی نهێنی هەڵەیە")
        new = self._ask_pin("ژمارەی نهێنی نوێ", twice=True)
        if new is None: return
        if len(new) < 4: return msg(self, "لانیکەم ٤ پیت یان ژمارە بنووسە")
        db.set("pin", pin_hash(new)); self.refresh(); self.app.toast("قفڵ چالاککرا")

    def rm_pin(self):
        old = self._ask_pin("ژمارەی نهێنی ئێستا")
        if old is None: return
        if pin_hash(old) != db.get("pin"): return msg(self, "ژمارەی نهێنی هەڵەیە")
        db.set("pin", ""); self.refresh(); self.app.toast("قفڵ لابرا")

    # ---- داتابەیس و باکئەپ ----
    def move_db(self):
        folder = QFileDialog.getExistingDirectory(self, "فۆڵدەری داتابەیس")
        if not folder: return
        target = os.path.join(folder, "oil_shop.db")
        if os.path.abspath(target) == os.path.abspath(core.DB_PATH):
            return msg(self, "هەمان شوێنە")
        if os.path.exists(target):
            if not ask(self, "لەم فۆڵدەرەدا داتابەیسێک هەیە.\n"
                             "بەکاری بهێنم؟ (داتای ئێستات دەمێنێتەوە لە شوێنی کۆنی خۆی)"):
                return
        else:
            try:
                db.con.commit(); shutil.copy2(core.DB_PATH, target)
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
        try: name = db.backup_to(p)
        except Exception as e: return msg(self, f"باکئەپ سەرکەوتوو نەبوو:\n{e}")
        self.app.toast(f"باکئەپ درووستکرا: {name}")

    def restore(self):
        p, _ = QFileDialog.getOpenFileName(self, "فایلی باکئەپ", db.get("backup") or APP_DIR, "DB (*.db)")
        if not p: return
        if ask(self, "هەموو داتای ئێستا دەگۆڕدرێت بە باکئەپەکە. دڵنیایت؟"):
            self.app.skip_backup = True      # don't overwrite a backup with what is being replaced
            db.con.close(); shutil.copy2(p, core.DB_PATH)
            msg(self, "گەڕێندرایەوە. تکایە بەرنامەکە دووبارە بکەرەوە")
            QApplication.quit()
