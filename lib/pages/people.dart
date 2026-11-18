// کڕیاران و دابینکەران: فۆرم، پارەدان، کەشف حساب و کارت.
import 'package:material_ui/material_ui.dart';

import '../core/db.dart';
import '../core/fmt.dart';
import '../print/docs.dart';
import '../ui/theme.dart';
import '../ui/widgets.dart';
import 'dashboard.dart' show eps;

/// Name / phone / address / note — the same for customers and suppliers.
Future<List<String>?> personForm(BuildContext context, String title, [Rec? r]) {
  final name = TextEditingController(text: r?['name'] ?? ''),
      phone = TextEditingController(text: r?['phone'] ?? ''),
      addr = TextEditingController(text: r?['address'] ?? ''),
      note = TextEditingController(text: r?['note'] ?? '');
  return formDialog<List<String>>(
    context,
    title,
    canSave: () => name.text.trim().isNotEmpty,
    body: (c, set) => [
      formRow(c, 'ناو', textBox(c, name, autofocus: true, onChanged: (_) => set(() {}))),
      formRow(c, 'مۆبایل', textBox(c, phone, ltr: true)),
      formRow(c, 'ناونیشان', textBox(c, addr)),
      formRow(c, 'تێبینی', textBox(c, note)),
    ],
    onSave: (_) => [name.text.trim(), phone.text.trim(), addr.text.trim(), note.text.trim()],
  );
}

/// Ask for a payment. Returns (date, amount, note) or null.
Future<(String, double, String)?> payDialog(BuildContext context, String title, double balance,
    {String caption = 'قەرزی ئێستا'}) {
  final date = DateCtrl(), amount = NumCtrl(balance > 0 ? balance : 0), note = TextEditingController();
  return formDialog<(String, double, String)>(
    context,
    title,
    body: (c, _) => [
      formRow(c, caption,
          label(c, money(balance), size: 16, w: FontWeight.w700, color: balance > eps ? c.pal.red : c.pal.green)),
      formRow(c, 'بەروار', DateBox(date)),
      formRow(c, 'بڕی پارە', NumBox(amount)),
      formRow(c, 'تێبینی', textBox(c, note)),
    ],
    onSave: (c) {
      if (amount.n <= 0) return null;
      return (date.iso, amount.n, note.text.trim());
    },
  );
}

/// One line of a ledger: a debt (invoice / purchase) or a payment.
class Entry {
  final String date, text;
  final double debit, credit;
  final int? payId;   // the payment row, so a mistaken one can be deleted
  Entry(this.date, this.text, this.debit, this.credit, [this.payId]);
}

/// Running-balance ledger shared by customers and suppliers.
Future<void> statementDialog(BuildContext context, String title, String name,
    List<Entry> Function() fetch, void Function(int) deletePay) {
  int? sel;
  return showDialog<void>(
    context: context,
    builder: (ctx) => StatefulBuilder(builder: (ctx, set) {
      final c = ctx.pal;
      final rows = fetch()..sort((a, b) {
          final d = a.date.compareTo(b.date);
          return d != 0 ? d : (a.payId == null ? 0 : 1) - (b.payId == null ? 0 : 1);
        });
      var bal = 0.0;
      final out = <List<String>>[];
      for (final r in rows) {
        bal += r.debit - r.credit;
        out.add([r.date, r.text, r.debit > 0 ? fmt(r.debit) : '—', r.credit > 0 ? fmt(r.credit) : '—', fmt(bal)]);
      }
      final doc = statementDoc(title, name, [for (final o in out) [lrm(o[0]), ...o.skip(1)]], bal);
      return AlertDialog(
        title: Text('$title — $name'),
        content: SizedBox(
          width: 760,
          height: 470,
          child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            Expanded(
              child: Grid(
                const [Col('بەروار', flex: 3), Col('ڕوونکردنەوە', flex: 6), Col('بڕ', flex: 3), Col('پارەی دراو', flex: 3), Col('ماوە', flex: 3)],
                [for (final o in out) [lrm(o[0]), ...o.skip(1)]],
                selected: sel,
                onSelect: (i) => set(() => sel = i),
                colors: (r, col) => col == 3 && out[r][3] != '—' ? c.green : null,
                empty: 'هیچ مامەڵەیەک نییە',
              ),
            ),
            const SizedBox(height: 12),
            Row(children: [
              label(ctx, 'کۆی ماوە', color: c.muted),
              const Spacer(),
              label(ctx, money(bal), size: 24, w: FontWeight.w800, color: c.goldHi),
            ]),
          ]),
        ),
        actions: [
          Btn('PDF', () async => savePdf(await docPdf(doc), 'statement.pdf'), icon: Icons.picture_as_pdf_outlined),
          Btn('چاپکردن', () async => printPdf(await docPdf(doc), 'statement'), icon: Icons.print_outlined),
          Btn.danger('سڕینەوەی پارەدان', () async {
            if (sel == null || rows[sel!].payId == null) {
              return info(ctx, 'ڕیزێکی «پارەدان» هەڵبژێرە.\nپسووڵە و کڕین لە بەشی خۆیان دەسڕدرێنەوە.');
            }
            if (await confirm(ctx, 'ئەم پارەدانە بسڕدرێتەوە؟')) {
              deletePay(rows[sel!].payId!);
              appState.changed();
              set(() => sel = null);
            }
          }),
          Btn.primary('داخستن', () => Navigator.pop(ctx)),
        ],
      );
    }),
  );
}

/// Customer or supplier tile with the amount still owed.
Widget personCard(BuildContext context, Rec r, String owedLabel,
    {required bool selected, required VoidCallback onTap, VoidCallback? onOpen}) {
  final c = context.pal;
  final bal = toD(r['bal']);
  final (b, tone) = bal > eps
      ? ('قەرزدار', c.red)
      : bal < -eps
          ? ('پێشەکی', c.blue)
          : ('پاک', c.green);
  final phone = (r['phone'] as String?) ?? '';
  return PickCard(selected: selected, onTap: onTap, onOpen: onOpen, children: [
    cardHead(context, r['name'] as String,
        sub: phone.isEmpty ? 'بێ ژمارە' : lrm(phone), badge: b, tone: tone, avatar: true),
    if ((r['address'] as String?)?.isNotEmpty == true) ...[
      const SizedBox(height: 4),
      hint(context, r['address'] as String),
    ],
    cardSep(context),
    cardRow(context, owedLabel, money(bal), color: bal > eps ? c.red : c.green),
  ]);
}

// ---------------------------------------------------------------- کڕیاران
class CustomersPage extends StatefulWidget {
  const CustomersPage({super.key});
  @override
  State<CustomersPage> createState() => _CustomersPageState();
}

class _CustomersPageState extends State<CustomersPage> {
  final search = TextEditingController();
  int filter = 0;
  int? picked;

  @override
  void initState() {
    super.initState();
    search.addListener(() => setState(() {}));
  }

  bool _need() {
    if (picked == null) info(context, 'سەرەتا کڕیارێک هەڵبژێرە');
    return picked != null;
  }

  Rec get _row => db.one('SELECT * FROM customers WHERE id=?', [picked])!;

  Future<void> add() async {
    final v = await personForm(context, 'کڕیاری نوێ');
    if (v == null) return;
    picked = db.x('INSERT INTO customers(name,phone,address,note) VALUES(?,?,?,?)', v);
    appState.changed();
    toast('کڕیار زیادکرا');
  }

  Future<void> edit() async {
    if (!_need()) return;
    final v = await personForm(context, 'دەستکاری کڕیار', _row);
    if (v == null) return;
    db.x('UPDATE customers SET name=?,phone=?,address=?,note=? WHERE id=?', [...v, picked]);
    appState.changed();
  }

  Future<void> remove() async {
    if (!_need()) return;
    if (db.val('SELECT COUNT(*) FROM invoices WHERE customer_id=?', [picked]) > 0 ||
        db.val('SELECT COUNT(*) FROM payments WHERE customer_id=?', [picked]) > 0) {
      return info(context, 'ناتوانرێت بسڕدرێتەوە — پسووڵە یان پارەدانی تۆمارکراوی هەیە');
    }
    if (await confirm(context, 'دڵنیایت لە سڕینەوە؟')) {
      db.x('DELETE FROM customers WHERE id=?', [picked]);
      picked = null;
      appState.changed();
    }
  }

  Future<void> pay() async {
    if (!_need()) return;
    final cid = picked!;
    final r = await payDialog(context, 'وەرگرتنی پارە — ${_row['name']}', db.balance(cid));
    if (r == null) return;
    db.x('INSERT INTO payments(date,customer_id,amount,note) VALUES(?,?,?,?)', [r.$1, cid, r.$2, r.$3]);
    appState.changed();
    toast('${money(r.$2)} وەرگیرا');
  }

  Future<void> statement() async {
    if (!_need()) return;
    final cid = picked!;
    await statementDialog(context, 'کەشف حساب', _row['name'] as String, () => [
          for (final i in db.q('SELECT * FROM invoices WHERE customer_id=?', [cid]))
            Entry(i['date'] as String, 'پسووڵە ${no(i['id'])}', toD(i['total']), toD(i['paid'])),
          for (final p in db.q('SELECT * FROM payments WHERE customer_id=?', [cid]))
            Entry(p['date'] as String,
                'وەرگرتنی پارە${(p['note'] as String?)?.isNotEmpty == true ? ' — ${p['note']}' : ''}',
                0, toD(p['amount']), p['id'] as int),
        ], (id) => db.x('DELETE FROM payments WHERE id=?', [id]));
  }

  @override
  Widget build(BuildContext context) {
    var rows = db.customers(search.text.trim());
    final owing = rows.where((r) => toD(r['bal']) > eps).toList();
    final total = owing.fold<double>(0, (s, r) => s + toD(r['bal']));
    if (filter == 1) rows = owing..sort((a, b) => toD(b['bal']).compareTo(toD(a['bal'])));
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      Row(children: [
        Btn.primary('کڕیاری نوێ', add, icon: Icons.add),
        const SizedBox(width: 8),
        Btn('دەستکاری', edit),
        const SizedBox(width: 8),
        Btn('وەرگرتنی پارە', pay, icon: Icons.payments_outlined),
        const SizedBox(width: 8),
        Btn('کەشف حساب', statement),
        const SizedBox(width: 8),
        Btn.danger('سڕینەوە', remove),
        const Spacer(),
        Chips(const ['هەموو', 'قەرزدار'], filter, (i) => setState(() => filter = i)),
        const SizedBox(width: 10),
        SearchBox('گەڕان بە ناو یان مۆبایل…', search, width: 220),
      ]),
      const SizedBox(height: 10),
      hint(context, '${db.customers().length} کڕیار   ·   ${owing.length} قەرزدار   ·   کۆی قەرز: ${money(total)}'),
      const SizedBox(height: 10),
      Expanded(
        child: CardGrid(empty: 'هیچ کڕیارێک نەدۆزرایەوە', children: [
          for (final r in rows)
            personCard(context, r, 'قەرز',
                selected: picked == r['id'],
                onTap: () => setState(() => picked = r['id'] as int),
                onOpen: statement),
        ]),
      ),
    ]);
  }
}
