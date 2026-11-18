// دابینکەران: قەرزی دووکان، دانی پارە، کەشف حساب و مێژووی کڕین.
import 'package:material_ui/material_ui.dart';

import '../core/db.dart';
import '../core/fmt.dart';
import '../ui/theme.dart';
import '../ui/widgets.dart';
import 'dashboard.dart' show eps;
import 'people.dart';

class SuppliersPage extends StatefulWidget {
  const SuppliersPage({super.key});
  @override
  State<SuppliersPage> createState() => _SuppliersPageState();
}

class _SuppliersPageState extends State<SuppliersPage> {
  final search = TextEditingController();
  int tab = 0;
  int? picked, pickedPurchase;

  @override
  void initState() {
    super.initState();
    search.addListener(() => setState(() {}));
  }

  bool _need() {
    if (picked == null) info(context, 'سەرەتا دابینکەرێک هەڵبژێرە');
    return picked != null;
  }

  Rec get _row => db.one('SELECT * FROM suppliers WHERE id=?', [picked])!;

  Future<void> add() async {
    final v = await personForm(context, 'دابینکەری نوێ');
    if (v == null) return;
    picked = db.x('INSERT INTO suppliers(name,phone,address,note) VALUES(?,?,?,?)', v);
    appState.changed();
    toast('دابینکەر زیادکرا');
  }

  Future<void> edit() async {
    if (!_need()) return;
    final v = await personForm(context, 'دەستکاری دابینکەر', _row);
    if (v == null) return;
    db.x('UPDATE suppliers SET name=?,phone=?,address=?,note=? WHERE id=?', [...v, picked]);
    appState.changed();
  }

  Future<void> remove() async {
    if (!_need()) return;
    if (db.val('SELECT COUNT(*) FROM purchases WHERE supplier_id=?', [picked]) > 0 ||
        db.val('SELECT COUNT(*) FROM supplier_payments WHERE supplier_id=?', [picked]) > 0) {
      return info(context, 'ناتوانرێت بسڕدرێتەوە — کڕین یان پارەدانی تۆمارکراوی هەیە');
    }
    if (await confirm(context, 'دڵنیایت لە سڕینەوە؟')) {
      db.x('DELETE FROM suppliers WHERE id=?', [picked]);
      picked = null;
      appState.changed();
    }
  }

  Future<void> pay() async {
    if (!_need()) return;
    final sid = picked!;
    final r = await payDialog(context, 'دانی پارە — ${_row['name']}', db.supplierBalance(sid), caption: 'قەرزمان لایە');
    if (r == null) return;
    db.x('INSERT INTO supplier_payments(date,supplier_id,amount,note) VALUES(?,?,?,?)', [r.$1, sid, r.$2, r.$3]);
    appState.changed();
    toast('${money(r.$2)} درا');
  }

  Future<void> statement() async {
    if (!_need()) return;
    final sid = picked!;
    await statementDialog(context, 'کەشف حسابی دابینکەر', _row['name'] as String, () => [
          for (final p in db.q("SELECT p.*, IFNULL(i.name,'—') iname FROM purchases p "
              'LEFT JOIN items i ON i.id=p.item_id WHERE p.supplier_id=?', [sid]))
            Entry(p['date'] as String, 'کڕین — ${p['iname']} × ${fmt(p['qty'])}',
                toD(p['qty']) * toD(p['price']), toD(p['paid'])),
          for (final p in db.q('SELECT * FROM supplier_payments WHERE supplier_id=?', [sid]))
            Entry(p['date'] as String,
                'دانی پارە${(p['note'] as String?)?.isNotEmpty == true ? ' — ${p['note']}' : ''}',
                0, toD(p['amount']), p['id'] as int),
        ], (id) => db.x('DELETE FROM supplier_payments WHERE id=?', [id]));
  }

  Future<void> removePurchase(List<Rec> rows) async {
    if (pickedPurchase == null) return info(context, 'سەرەتا کڕینێک هەڵبژێرە');
    final pu = rows[pickedPurchase!];
    final it = db.one('SELECT * FROM items WHERE id=?', [pu['item_id']]);
    var text = 'ئەم کڕینە بسڕدرێتەوە؟ بڕەکەی لە مەخزەن کەم دەکرێتەوە.';
    if (it != null && toD(it['qty']) - toD(pu['qty']) < -eps) {
      text += '\n\nئاگاداری: بەشێکی فرۆشراوە — بڕی مەخزەن دەبێتە ${fmt(toD(it['qty']) - toD(pu['qty']))}.';
    }
    if (!await confirm(context, text)) return;
    db.tx(() {
      if (it != null) {
        final nq = toD(it['qty']) - toD(pu['qty']);
        var cost = toD(it['cost']);
        if (nq > eps) {
          // undo this delivery's share of the average cost
          cost = (toD(it['qty']) * cost - toD(pu['qty']) * toD(pu['price'])) / nq;
          if (cost < 0) cost = 0;
        }
        db.x('UPDATE items SET qty=?, cost=? WHERE id=?', [nq, cost, it['id']]);
      }
      db.x('DELETE FROM purchases WHERE id=?', [pu['id']]);
    });
    pickedPurchase = null;
    appState.changed();
    toast('کڕینەکە سڕایەوە');
  }

  @override
  Widget build(BuildContext context) {
    final c = context.pal;
    Widget tabBtn(String t, int i) => Padding(
          padding: const EdgeInsetsDirectional.only(end: 6),
          child: InkWell(
            borderRadius: BorderRadius.circular(10),
            onTap: () => setState(() => tab = i),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
              decoration: BoxDecoration(
                color: tab == i ? c.card : Colors.transparent,
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: tab == i ? c.border : Colors.transparent),
              ),
              child: label(context, t, w: tab == i ? FontWeight.w700 : FontWeight.w600, color: tab == i ? c.goldHi : c.muted),
            ),
          ),
        );
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      Row(children: [tabBtn('دابینکەران', 0), tabBtn('مێژووی کڕین', 1)]),
      const SizedBox(height: 14),
      Expanded(child: tab == 0 ? _list(context) : _history(context)),
    ]);
  }

  Widget _list(BuildContext context) {
    final rows = db.suppliers(search.text.trim());
    final owed = rows.fold<double>(0, (s, r) => s + (toD(r['bal']) > eps ? toD(r['bal']) : 0));
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      Row(children: [
        Btn.primary('دابینکەری نوێ', add, icon: Icons.add),
        const SizedBox(width: 8),
        Btn('دەستکاری', edit),
        const SizedBox(width: 8),
        Btn('دانی پارە', pay, icon: Icons.payments_outlined),
        const SizedBox(width: 8),
        Btn('کەشف حساب', statement),
        const SizedBox(width: 8),
        Btn.danger('سڕینەوە', remove),
        const Spacer(),
        SearchBox('گەڕان بە ناو یان مۆبایل…', search, width: 220),
      ]),
      const SizedBox(height: 10),
      hint(context, '${rows.length} دابینکەر   ·   کۆی قەرزی سەر دووکان: ${money(owed)}'),
      const SizedBox(height: 10),
      Expanded(
        child: CardGrid(
          empty: 'هێشتا هیچ دابینکەرێک تۆمار نەکراوە.\nلە مەخزەن، لە کاتی «کڕین»دا ناوی دابینکەر بنووسە.',
          children: [
            for (final r in rows)
              personCard(context, r, 'قەرزمان لایە',
                  selected: picked == r['id'], onTap: () => setState(() => picked = r['id'] as int), onOpen: statement),
          ],
        ),
      ),
    ]);
  }

  Widget _history(BuildContext context) {
    final c = context.pal;
    final rows = db.q("SELECT p.*, IFNULL(s.name, IFNULL(p.supplier,'')) sn, IFNULL(i.name,'—') iname "
        'FROM purchases p LEFT JOIN suppliers s ON s.id=p.supplier_id '
        'LEFT JOIN items i ON i.id=p.item_id ORDER BY p.id DESC LIMIT 400');
    final month = db.val('SELECT SUM(qty*price) FROM purchases WHERE date>=?', [isoDate(monthStart())]);
    final cells = [
      for (final r in rows)
        [
          '#${r['id']}', lrm(r['date']), (r['sn'] as String).isEmpty ? '—' : r['sn'] as String, r['iname'] as String,
          fmt(r['qty']), fmt(r['price']), fmt(toD(r['qty']) * toD(r['price'])), fmt(r['paid']),
          fmt(toD(r['qty']) * toD(r['price']) - toD(r['paid'])),
        ]
    ];
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      Row(children: [
        hint(context, 'کڕینی ئەم مانگە:  ${money(month)}'),
        const Spacer(),
        Btn.danger('سڕینەوەی کڕین', () => removePurchase(rows)),
      ]),
      const SizedBox(height: 10),
      Expanded(
        child: Grid(
          const [Col('#'), Col('بەروار', flex: 2), Col('دابینکەر', flex: 3), Col('کاڵا', flex: 3), Col('بڕ'),
              Col('نرخ', flex: 2), Col('کۆ', flex: 2), Col('دراو', flex: 2), Col('ماوە', flex: 2)],
          cells,
          selected: pickedPurchase,
          onSelect: (i) => setState(() => pickedPurchase = i),
          colors: (r, col) => col == 8 ? (cells[r][8] == '0' ? c.faint : c.red) : null,
          empty: 'هێشتا هیچ کڕینێک تۆمار نەکراوە',
        ),
      ),
    ]);
  }
}
