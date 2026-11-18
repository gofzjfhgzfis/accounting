// مەخزەن: کاڵاکان، بارکۆد، کڕین و چاپی لەیبڵ.
import 'package:material_ui/material_ui.dart';

import '../core/barcode.dart';
import '../core/db.dart';
import '../core/fmt.dart';
import '../print/docs.dart';
import '../ui/barcode_view.dart';
import '../ui/theme.dart';
import '../ui/widgets.dart';
import 'dashboard.dart' show eps;
import 'guard.dart';

class InventoryPage extends StatefulWidget {
  const InventoryPage({super.key});
  @override
  State<InventoryPage> createState() => _InventoryPageState();
}

class _InventoryPageState extends State<InventoryPage> {
  final search = TextEditingController();
  int filter = 0;
  int? picked;

  @override
  void initState() {
    super.initState();
    search.addListener(() {
      // a scanned code picks its item straight away
      final hit = db.itemByCode(normCode(search.text));
      setState(() => picked = hit?['id'] as int? ?? picked);
    });
  }

  bool _need() {
    if (picked == null) info(context, 'سەرەتا کاڵایەک هەڵبژێرە');
    return picked != null;
  }

  Rec get _row => db.one('SELECT * FROM items WHERE id=?', [picked])!;

  Future<List<Object?>?> form([Rec? r]) {
    final name = TextEditingController(text: r?['name'] ?? ''),
        kind = TextEditingController(text: r?['kind'] ?? ''),
        unit = TextEditingController(text: r?['unit'] ?? ''),
        code = TextEditingController(text: r?['barcode'] ?? '');
    final qty = NumCtrl(toD(r?['qty'])), cost = NumCtrl(toD(r?['cost'])),
        price = NumCtrl(toD(r?['price'])), minq = NumCtrl(toD(r?['minq']));
    final kinds = [
      for (final k in db.q("SELECT DISTINCT kind FROM items WHERE IFNULL(kind,'')<>'' ORDER BY kind"))
        (k['kind'] as String, 0)
    ];
    final next = FocusNode();
    return formDialog<List<Object?>>(
      context,
      r == null ? 'کاڵای نوێ' : 'دەستکاری کاڵا',
      canSave: () => name.text.trim().isNotEmpty,
      body: (c, set) => [
        formRow(c, 'ناو', textBox(c, name, autofocus: true, onChanged: (_) => set(() {}))),
        formRow(c, 'جۆر', PickBox(kinds, kind)),
        formRow(c, 'یەکە', textBox(c, unit, hintText: 'لیتر / کارتۆن / کیلۆ / دانە')),
        formRow(
          c,
          'بارکۆد',
          Row(children: [
            Expanded(
              child: textBox(c, code,
                  ltr: true,
                  hintText: 'سکان بکە یان بینووسە',
                  // a scanner ends with Enter: tidy the code and move on
                  onSubmitted: (v) {
                    code.text = normCode(v);
                    next.requestFocus();
                  }),
            ),
            const SizedBox(width: 8),
            Btn('درووستکردن', () => code.text = generateCode((x) => db.itemByCode(x) != null),
                tip: 'ژمارەیەکی نوێ بۆ کاڵایەک کە بارکۆدی نییە'),
          ]),
        ),
        formRow(c, r == null ? 'بڕی سەرەتا' : 'بڕی ئێستا', NumBox(qty, focus: next)),
        formRow(c, 'تێچووی یەکە', NumBox(cost)),
        formRow(c, 'نرخی فرۆشتن', NumBox(price)),
        formRow(c, 'کەمترین بڕ (ئاگاداری)', NumBox(minq)),
      ],
      onSave: (c) {
        final cd = normCode(code.text);
        code.text = cd;
        if (cd.isNotEmpty && !validCode(cd)) {
          info(c, 'بارکۆد تەنها ژمارە و پیتی ئینگلیزی وەردەگرێت');
          return null;
        }
        final other = db.itemByCode(cd, r?['id'] as int?);
        if (other != null) {
          info(c, 'ئەم بارکۆدە پێشتر بۆ «${other['name']}» تۆمارکراوە');
          return null;
        }
        return [name.text.trim(), kind.text.trim(), unit.text.trim(), cd.isEmpty ? null : cd,
            qty.n, cost.n, price.n, minq.n];
      },
    );
  }

  Future<void> add() async {
    final v = await form();
    if (v == null) return;
    picked = db.x('INSERT INTO items(name,kind,unit,barcode,qty,cost,price,minq) VALUES(?,?,?,?,?,?,?,?)', v);
    db.log('item', 'add', 'کاڵای نوێ — ${v[0]} — بڕ ${fmt(v[4])}، نرخ ${money(v[6])}', ref: picked);
    appState.changed();
    toast('کاڵا زیادکرا');
  }

  Future<void> edit() async {
    if (!_need()) return;
    final old = _row;
    final v = await form(old);
    if (v == null) return;
    db.x('UPDATE items SET name=?,kind=?,unit=?,barcode=?,qty=?,cost=?,price=?,minq=? WHERE id=?', [...v, picked]);
    // spell out what changed, so a quiet stock or price edit can be traced
    final changes = [
      if (old['name'] != v[0]) 'ناو ← ${v[0]}',
      if ((toD(old['qty']) - toD(v[4])).abs() > eps) 'بڕ ${fmt(old['qty'])} ← ${fmt(v[4])}',
      if ((toD(old['cost']) - toD(v[5])).abs() > eps) 'تێچوو ${fmt(old['cost'])} ← ${fmt(v[5])}',
      if ((toD(old['price']) - toD(v[6])).abs() > eps) 'نرخ ${fmt(old['price'])} ← ${fmt(v[6])}',
      if ((old['barcode'] ?? '') != (v[3] ?? '')) 'بارکۆد ← ${v[3] ?? '—'}',
    ];
    db.log('item', 'edit', 'دەستکاری کاڵا — ${old['name']}${changes.isEmpty ? '' : ' — ${changes.join('، ')}'}', ref: picked);
    appState.changed();
  }

  Future<void> remove() async {
    if (!_need()) return;
    if (db.val('SELECT COUNT(*) FROM invoice_items WHERE item_id=?', [picked]) > 0 ||
        db.val('SELECT COUNT(*) FROM purchases WHERE item_id=?', [picked]) > 0) {
      return info(context, 'ناتوانرێت بسڕدرێتەوە — ئەم کاڵایە لە پسووڵە یان کڕیندا بەکارهاتووە');
    }
    if (await confirm(context, 'دڵنیایت لە سڕینەوە؟')) {
      db.log('item', 'delete', 'کاڵا سڕایەوە — ${_row['name']}', ref: picked);
      db.x('DELETE FROM items WHERE id=?', [picked]);
      picked = null;
      appState.changed();
    }
  }

  Future<void> purchase() async {
    if (!_need()) return;
    final it = _row, iid = picked!;
    final date = DateCtrl(), sup = TextEditingController(), note = TextEditingController();
    final qty = NumCtrl(), price = NumCtrl(toD(it['cost'])), paid = NumCtrl();
    var auto = true;   // «پارەی دراو» follows the total until it is typed in
    final sups = [for (final s in db.q('SELECT name FROM suppliers ORDER BY name')) (s['name'] as String, 0)];
    final r = await formDialog<bool>(
      context,
      'کڕین — ${it['name']}',
      width: 480,
      body: (c, set) {
        final t = qty.n * price.n;
        void sync() => set(() {
              if (auto) paid.n = qty.n * price.n;
            });
        return [
          formRow(c, 'بەروار', DateBox(date)),
          formRow(c, 'دابینکەر', PickBox(sups, sup, hintText: 'ناوی دابینکەر (نوێ بێت خۆی تۆمار دەبێت)')),
          formRow(c, 'بڕ (${(it['unit'] as String?)?.isNotEmpty == true ? it['unit'] : 'یەکە'})',
              NumBox(qty, onChanged: (_) => sync())),
          formRow(c, 'نرخی یەکە', NumBox(price, onChanged: (_) => sync())),
          formRow(c, 'کۆی کڕین', label(c, money(t), size: 16, w: FontWeight.w700, color: c.pal.goldHi)),
          formRow(c, 'پارەی دراو', NumBox(paid, onChanged: (_) => set(() => auto = false))),
          Padding(
            padding: const EdgeInsetsDirectional.only(start: 130),
            child: hint(c, 'ئەوەی نەدرێت دەچێتە سەر قەرزی دابینکەرەکە.'),
          ),
          formRow(c, 'تێبینی', textBox(c, note)),
        ];
      },
      onSave: (c) {
        if (qty.n <= 0) return null;
        if (sup.text.trim().isEmpty && paid.n < qty.n * price.n - eps) {
          info(c, 'بۆ کڕینی قەرز پێویستە ناوی دابینکەر بنووسیت');
          return null;
        }
        return true;
      },
    );
    if (r != true || !mounted || !dayOpen(context, date.iso)) return;
    final t = qty.n * price.n, onHand = toD(it['qty']) > 0 ? toD(it['qty']) : 0.0;
    // weighted average cost of what is on the shelf after this delivery
    final newCost = (onHand * toD(it['cost']) + t) / (onHand + qty.n);
    db.tx(() {
      final sid = db.supplierId(sup.text);
      db.x('UPDATE items SET qty=qty+?, cost=? WHERE id=?', [qty.n, newCost, iid]);
      final pid = db.x('INSERT INTO purchases(date,supplier,supplier_id,item_id,qty,price,paid,note) VALUES(?,?,?,?,?,?,?,?)',
          [date.iso, sup.text.trim(), sid, iid, qty.n, price.n, paid.n.clamp(0, t), note.text.trim()]);
      db.log('purchase', 'add',
          'کڕین — ${it['name']} × ${fmt(qty.n)}${sup.text.trim().isEmpty ? '' : ' — ${sup.text.trim()}'} — ${money(t)}، دراو ${money(paid.n.clamp(0, t))}',
          ref: pid, amount: t);
    });
    appState.changed();
    toast('کڕینەکە تۆمارکرا');
  }

  Future<void> labels() async {
    if (!_need()) return;
    final it = _row;
    var code = (it['barcode'] as String?) ?? '';
    if (code.isEmpty) {
      if (!await confirm(context, '«${it['name']}» بارکۆدی نییە.\nژمارەیەکی نوێی بۆ درووست بکەم؟')) return;
      code = generateCode((x) => db.itemByCode(x) != null);
      db.x('UPDATE items SET barcode=? WHERE id=?', [code, picked]);
      db.log('item', 'edit', 'بارکۆدی نوێ — ${it['name']} — $code', ref: picked);
      appState.changed();
    }
    if (mounted) await labelsDialog(context, it['name'] as String, code, money(it['price']));
  }

  @override
  Widget build(BuildContext context) {
    final c = context.pal;
    final t = search.text.trim();
    final rows = db.q(
        "SELECT * FROM items WHERE name LIKE ? OR IFNULL(kind,'') LIKE ? OR IFNULL(barcode,'') LIKE ? ORDER BY name",
        ['%$t%', '%$t%', '%${normCode(t)}%']);
    final low = rows.where((r) => toD(r['minq']) > 0 && toD(r['qty']) <= toD(r['minq'])).toList();
    final value = rows.fold<double>(0, (s, r) => s + toD(r['qty']) * toD(r['cost']));
    final shown = filter == 1 ? low : rows;
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      Row(children: [
        Btn.primary('کاڵای نوێ', add, icon: Icons.add),
        const SizedBox(width: 8),
        Btn('دەستکاری', edit),
        const SizedBox(width: 8),
        Btn('کڕین / زیادکردنی بڕ', purchase, icon: Icons.local_shipping_outlined),
        const SizedBox(width: 8),
        Btn('چاپی بارکۆد', labels, icon: Icons.qr_code_2),
        const SizedBox(width: 8),
        Btn.danger('سڕینەوە', remove),
        const Spacer(),
        Chips(const ['هەموو', 'کەمبوو'], filter, (i) => setState(() => filter = i)),
        const SizedBox(width: 10),
        SearchBox('ناو، جۆر یان بارکۆد…', search, width: 220),
      ]),
      const SizedBox(height: 10),
      hint(context, '${rows.length} کاڵا   ·   ${low.length} کەمبوو   ·   بەهای مەخزەن: ${money(value)}   ${usd(value)}'),
      const SizedBox(height: 10),
      Expanded(
        child: CardGrid(empty: 'هیچ کاڵایەک نەدۆزرایەوە', children: [
          for (final r in shown)
            () {
              final out = toD(r['qty']) <= eps;
              final isLow = toD(r['minq']) > 0 && toD(r['qty']) <= toD(r['minq']);
              return PickCard(
                selected: picked == r['id'],
                onTap: () => setState(() => picked = r['id'] as int),
                onOpen: edit,
                children: [
                  cardHead(context, r['name'] as String,
                      sub: (r['kind'] as String?) ?? '',
                      badge: out ? 'نەماوە' : (isLow ? 'کەمە' : null),
                      tone: out ? c.red : c.orange),
                  cardSep(context),
                  cardRow(context, 'بڕی بەردەست', '${fmt(r['qty'])} ${r['unit'] ?? ''}'.trim(),
                      color: out || isLow ? c.red : c.green),
                  cardRow(context, 'تێچوو', fmt(r['cost']), color: c.muted, strong: false),
                  cardRow(context, 'نرخی فرۆشتن', money(r['price']), color: c.goldHi),
                  if ((r['barcode'] as String?)?.isNotEmpty == true)
                    cardRow(context, 'بارکۆد', lrm(r['barcode']), color: c.muted, strong: false),
                ],
              );
            }(),
        ]),
      ),
    ]);
  }
}

/// Choose the sheet and how many stickers, then save a PDF or print.
Future<void> labelsDialog(BuildContext context, String name, String code, String price) {
  var layout = 0, showPrice = true;
  final count = NumCtrl(24);
  return showDialog<void>(
    context: context,
    builder: (ctx) => StatefulBuilder(builder: (ctx, set) {
      final c = ctx.pal;
      final l = labelLayouts[layout];
      final k = (320 / l.$2) < (190 / l.$3) ? 320 / l.$2 : 190 / l.$3;   // px per mm in the preview
      Future<void> run(bool toPdf) async {
        final n = count.n.round().clamp(1, 2000);
        final bytes = await labelsPdf(layout, n, name, code, showPrice ? price : '');
        if (toPdf) {
          await savePdf(bytes, 'barcode_$code.pdf');
        } else {
          await printPdf(bytes, 'barcode_$code', format: labelFormat(layout));
        }
        if (ctx.mounted) Navigator.pop(ctx);
      }

      return AlertDialog(
        title: Text('چاپی بارکۆد — $name'),
        content: SizedBox(
          width: 500,
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            Container(
              height: 230,
              alignment: Alignment.center,
              decoration: BoxDecoration(color: c.field, borderRadius: BorderRadius.circular(12), border: Border.all(color: c.border)),
              child: Container(
                width: l.$2 * k,
                height: l.$3 * k,
                decoration: BoxDecoration(border: Border.all(color: const Color(0xFFC9CED6))),
                child: LabelView(name, code, showPrice ? price : '',
                    pixelRatio: MediaQuery.devicePixelRatioOf(ctx)),
              ),
            ),
            const SizedBox(height: 14),
            formRow(
              ctx,
              'جۆری لەیبڵ',
              DropdownButtonFormField<int>(
                initialValue: layout,
                items: [for (var i = 0; i < labelLayouts.length; i++) DropdownMenuItem(value: i, child: Text(labelLayouts[i].$1))],
                onChanged: (v) => set(() {
                  layout = v ?? 0;
                  final per = labelLayouts[layout].$4 * labelLayouts[layout].$5;
                  count.n = per > 1 ? per.toDouble() : 1;
                }),
              ),
            ),
            const SizedBox(height: 10),
            formRow(ctx, 'ژمارەی لەیبڵ', NumBox(count)),
            const SizedBox(height: 4),
            CheckboxListTile(
              value: showPrice,
              onChanged: (v) => set(() => showPrice = v ?? true),
              title: label(ctx, 'نرخی فرۆشتن لەسەر لەیبڵەکە بنووسە'),
              controlAffinity: ListTileControlAffinity.leading,
              contentPadding: const EdgeInsetsDirectional.only(start: 122),
              dense: true,
            ),
            hint(ctx, 'بارکۆد:  ${lrm(code)}'),
          ]),
        ),
        actions: [
          Btn('داخستن', () => Navigator.pop(ctx)),
          Btn('PDF', () => run(true), icon: Icons.picture_as_pdf_outlined),
          Btn.primary('چاپکردن', () => run(false), icon: Icons.print_outlined),
        ],
      );
    }),
  );
}
