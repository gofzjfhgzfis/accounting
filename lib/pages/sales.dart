// فرۆشتن: پسووڵەی نوێ (بە سکانی بارکۆد) و لیستی پسووڵەکان.
import 'package:flutter/services.dart';
import 'package:material_ui/material_ui.dart';

import '../core/barcode.dart';
import '../core/db.dart';
import '../core/fmt.dart';
import '../print/docs.dart';
import '../ui/theme.dart';
import '../ui/widgets.dart';
import 'dashboard.dart' show eps;
import 'guard.dart';

class Line {
  final int id;
  final String name;
  double qty, price;
  final double cost;
  Line(this.id, this.name, this.qty, this.price, this.cost);
}

/// The invoice being written. Kept outside the page so it survives a visit
/// to another section.
class SaleDraft {
  final lines = <Line>[];
  final cust = TextEditingController(text: walkIn);
  final item = TextEditingController();
  final scan = TextEditingController();
  final qty = NumCtrl(1), price = NumCtrl(), disc = NumCtrl(), paid = NumCtrl();
  final note = TextEditingController();
  final date = DateCtrl();
  final scanFocus = FocusNode(), itemFocus = FocusNode();
  String scanMsg = '';
  bool scanBad = false;
  int? selected;
  int tab = 0;
}

final draft = SaleDraft();

class SalesPage extends StatefulWidget {
  const SalesPage({super.key});
  @override
  State<SalesPage> createState() => SalesPageState();
}

class SalesPageState extends State<SalesPage> {
  SaleDraft get d => draft;

  // ---- لیست ----
  final search = TextEditingController();
  int filter = 0;
  int? picked;

  @override
  void initState() {
    super.initState();
    search.addListener(() => setState(() {}));
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted && d.tab == 0) d.scanFocus.requestFocus();
    });
  }

  void focusScan() {
    setState(() => d.tab = 0);
    WidgetsBinding.instance.addPostFrameCallback((_) => d.scanFocus.requestFocus());
  }

  // ---- ژمێریاری ----
  double get sub => d.lines.fold(0, (s, l) => s + l.qty * l.price);
  double get total => sub - d.disc.n.clamp(0, sub);

  List<(String, int)> get custOptions => [
        (walkIn, 0),
        for (final r in db.q('SELECT id,name FROM customers ORDER BY name')) (r['name'] as String, r['id'] as int),
      ];

  List<(String, int)> get itemOptions =>
      [for (final r in db.q('SELECT id,name FROM items ORDER BY name')) (r['name'] as String, r['id'] as int)];

  int? get custId => PickBox.valueOf(custOptions, d.cust);

  Future<bool> _add(Rec it, double qty, double price) async {
    final already = d.lines.where((l) => l.id == it['id']).fold<double>(0, (s, l) => s + l.qty);
    if (already + qty > toD(it['qty']) + eps) {
      if (!await confirm(context, 'بڕی «${it['name']}» لە مەخزەن تەنها ${fmt(it['qty'])}ە. بەردەوام بم؟')) {
        return false;
      }
    }
    final same = d.lines.where((l) => l.id == it['id'] && l.price == price);
    if (same.isNotEmpty) {
      same.first.qty += qty;
    } else {
      d.lines.add(Line(it['id'] as int, it['name'] as String, qty, price, toD(it['cost'])));
    }
    setState(() {});
    return true;
  }

  Future<void> addLine() async {
    var id = PickBox.valueOf(itemOptions, d.item);
    if (id == null) {
      // a barcode typed or scanned into the item box works too
      final hit = db.itemByCode(normCode(d.item.text));
      if (hit != null) {
        id = hit['id'] as int;
        d.item.text = hit['name'] as String;
      }
    }
    if (id == null) return info(context, 'ئەم کاڵایە لە مەخزەندا نییە');
    if (d.qty.n <= 0) return;
    final it = db.one('SELECT * FROM items WHERE id=?', [id])!;
    if (await _add(it, d.qty.n, d.price.n)) d.qty.n = 1;
    d.itemFocus.requestFocus();
    d.item.selection = TextSelection(baseOffset: 0, extentOffset: d.item.text.length);
  }

  /// One scan = one more of that item at its selling price.
  Future<void> scanCode(String text) async {
    final code = normCode(text);
    d.scan.clear();
    if (code.isEmpty) return;
    final it = db.itemByCode(code);
    if (it == null) {
      SystemSound.play(SystemSoundType.alert);
      setState(() {
        d.scanMsg = 'بارکۆدی ${lrm(code)} لە مەخزەندا نییە';
        d.scanBad = true;
      });
    } else if (await _add(it, 1, toD(it['price']))) {
      final n = d.lines.where((l) => l.id == it['id']).fold<double>(0, (s, l) => s + l.qty);
      setState(() {
        d.scanMsg = '✓  ${iso(it['name'] as String)} زیادکرا  ·  ${fmt(n)} ${it['unit'] ?? ''}'.trim();
        d.scanBad = false;
      });
    }
    d.scanFocus.requestFocus();
  }

  void pickItem(String name) {
    final id = PickBox.valueOf(itemOptions, d.item);
    if (id != null) {
      final r = db.one('SELECT price FROM items WHERE id=?', [id]);
      if (r != null) d.price.n = toD(r['price']);
    }
    setState(() {});
  }

  Future<void> save() async {
    if (d.lines.isEmpty) return info(context, 'هیچ کاڵایەک زیاد نەکراوە');
    final cid = custId;
    if (cid == null) {
      return info(context, 'ئەم کڕیارە تۆمار نەکراوە.\nلە بەشی کڕیاران زیادی بکە یان «$walkIn» هەڵبژێرە.');
    }
    final s = sub, disc = d.disc.n.clamp(0, s).toDouble(), tot = s - disc;
    final paid = cid == 0 ? tot : d.paid.n.clamp(0, tot).toDouble();
    if (!dayOpen(context, d.date.iso)) return;
    final who = cid == 0 ? walkIn : d.cust.text.trim();
    final iid = db.tx(() {
      final iid = db.x('INSERT INTO invoices(date,customer_id,subtotal,discount,total,paid,note) VALUES(?,?,?,?,?,?,?)',
          [d.date.iso, cid == 0 ? null : cid, s, disc, tot, paid, d.note.text]);
      for (final l in d.lines) {
        db.x('INSERT INTO invoice_items(invoice_id,item_id,qty,price,cost) VALUES(?,?,?,?,?)',
            [iid, l.id, l.qty, l.price, l.cost]);
        db.x('UPDATE items SET qty=qty-? WHERE id=?', [l.qty, l.id]);
      }
      db.log('sale', 'add', 'پسووڵە ${no(iid)} — $who — کۆ ${money(tot)}، دراو ${money(paid)}', ref: iid, amount: tot);
      return iid;
    });
    d.lines.clear();
    d.disc.n = 0;
    d.paid.n = 0;
    d.note.clear();
    d.cust.text = walkIn;
    d.scanMsg = '';
    d.selected = null;
    appState.changed();
    if (!mounted) return;
    final act = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('تۆمارکرا'),
        content: Text('پسووڵە ${no(iid)} بە سەرکەوتوویی تۆمارکرا.'),
        actions: [
          Btn('چاپکردن', () => Navigator.pop(ctx, 'print'), icon: Icons.print_outlined),
          Btn('PDF', () => Navigator.pop(ctx, 'pdf'), icon: Icons.picture_as_pdf_outlined),
          Btn.primary('باشە', () => Navigator.pop(ctx)),
        ],
      ),
    );
    if (act == 'print') await printPdf(await docPdf(invoiceDoc(iid)), 'invoice_$iid');
    if (act == 'pdf') await savePdf(await docPdf(invoiceDoc(iid)), 'invoice_$iid.pdf');
    d.scanFocus.requestFocus();
  }

  // ---------------------------------------------------------------- ڕووکار
  @override
  Widget build(BuildContext context) {
    final c = context.pal;
    Widget tabBtn(String t, int i) => Padding(
          padding: const EdgeInsetsDirectional.only(end: 6),
          child: InkWell(
            borderRadius: BorderRadius.circular(10),
            onTap: () => setState(() => d.tab = i),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
              decoration: BoxDecoration(
                color: d.tab == i ? c.card : Colors.transparent,
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: d.tab == i ? c.border : Colors.transparent),
              ),
              child: label(context, t,
                  w: d.tab == i ? FontWeight.w700 : FontWeight.w600, color: d.tab == i ? c.goldHi : c.muted),
            ),
          ),
        );
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      Row(children: [tabBtn('پسووڵەی نوێ', 0), tabBtn('پسووڵەکان', 1), tabBtn('گەڕاندنەوەکان', 2)]),
      const SizedBox(height: 14),
      Expanded(child: switch (d.tab) { 0 => _newTab(context), 1 => _listTab(context), _ => _returnsTab(context) }),
    ]);
  }

  Widget _newTab(BuildContext context) {
    final c = context.pal;
    final cid = custId;
    final walk = cid == 0;
    final s = sub, tot = total;
    // a sale with no named customer cannot leave a debt behind
    if (walk && d.paid.n != tot) {
      WidgetsBinding.instance.addPostFrameCallback((_) => d.paid.n = tot);
    }
    final due = walk ? 0.0 : tot - d.paid.n.clamp(0, tot);
    final itemId = PickBox.valueOf(itemOptions, d.item);
    final it = itemId == null ? null : db.one('SELECT * FROM items WHERE id=?', [itemId]);

    final side = Panel(
      child: SingleChildScrollView(
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          heading(context, 'کڕیار'),
          const SizedBox(height: 6),
          PickBox(custOptions, d.cust, onChanged: (_) => setState(() {}),
              prefix: Icon(Icons.person_outline, size: 19, color: c.muted)),
          const SizedBox(height: 5),
          hint(context, walk
              ? 'فرۆشتنی نەقد — هەموو پارەکە وەردەگیرێت'
              : cid != null
                  ? 'قەرزی ئێستای ئەم کڕیارە:  ${money(db.balance(cid))}'
                  : 'ئەم ناوە لە لیستی کڕیاراندا نییە'),
          const SizedBox(height: 10),
          field(context, 'بەروار', DateBox(d.date)),
          const SizedBox(height: 18),
          heading(context, 'زیادکردنی کاڵا'),
          const SizedBox(height: 6),
          TextField(
            controller: d.scan,
            focusNode: d.scanFocus,
            style: st(context),
            onSubmitted: scanCode,
            decoration: InputDecoration(
              hintText: 'سکانی بارکۆد بکە…  (F2)',
              prefixIcon: Icon(Icons.qr_code_scanner, size: 19, color: c.muted),
            ),
          ),
          const SizedBox(height: 5),
          label(context, d.scanMsg.isEmpty ? 'بە سکانکردن کاڵاکە یەکسەر دەچێتە سەر پسووڵە.' : d.scanMsg,
              size: 13.5,
              w: d.scanMsg.isEmpty ? FontWeight.w400 : FontWeight.w700,
              color: d.scanMsg.isEmpty ? c.muted : (d.scanBad ? c.red : c.green)),
          const SizedBox(height: 10),
          PickBox(itemOptions, d.item,
              focus: d.itemFocus,
              hintText: 'یان ناوی کاڵا بنووسە',
              onChanged: pickItem,
              onSubmitted: (_) => addLine(),
              prefix: Icon(Icons.inventory_2_outlined, size: 19, color: c.muted)),
          const SizedBox(height: 5),
          hint(context, it == null
              ? 'کاڵایەک هەڵبژێرە یان ناوەکەی بنووسە'
              : 'بەردەست لە مەخزەن:  ${fmt(it['qty'])} ${it['unit'] ?? ''}'
                  '${toD(it['minq']) > 0 && toD(it['qty']) <= toD(it['minq']) ? '   ·   کەمە' : ''}'),
          const SizedBox(height: 10),
          Row(children: [
            Expanded(child: field(context, 'بڕ', NumBox(d.qty, onSubmitted: (_) => addLine()))),
            const SizedBox(width: 9),
            Expanded(child: field(context, 'نرخی یەکە', NumBox(d.price, onSubmitted: (_) => addLine()))),
          ]),
          const SizedBox(height: 12),
          Btn('زیادکردن بۆ پسووڵە', addLine, icon: Icons.add),
          const SizedBox(height: 6),
          hint(context, 'دوای نووسینی بڕ، Enter لێبدە بۆ زیادکردن.'),
        ]),
      ),
    );

    final lines = Panel(
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        Row(children: [
          panelTitle(context, 'کاڵاکانی پسووڵە'),
          const SizedBox(width: 8),
          Pill('${d.lines.length}'),
          const Spacer(),
          Btn.danger('لابردنی ڕیز', () {
            if (d.lines.isEmpty) return;
            setState(() {
              d.lines.removeAt(d.selected != null && d.selected! < d.lines.length ? d.selected! : d.lines.length - 1);
              d.selected = null;
            });
          }),
        ]),
        const SizedBox(height: 10),
        Expanded(
          child: Grid(
            const [Col('کاڵا', flex: 5), Col('بڕ'), Col('نرخ', flex: 2), Col('کۆ', flex: 2)],
            [for (final l in d.lines) [l.name, fmt(l.qty), fmt(l.price), fmt(l.qty * l.price)]],
            selected: d.selected,
            onSelect: (i) => setState(() => d.selected = i),
            flat: true,
            empty: 'سکان بکە یان کاڵایەک هەڵبژێرە',
          ),
        ),
        const SizedBox(height: 12),
        Row(crossAxisAlignment: CrossAxisAlignment.end, children: [
          Expanded(
            flex: 3,
            child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              Row(children: [
                Expanded(child: field(context, 'داشکاندن', NumBox(d.disc, onChanged: (_) => setState(() {})))),
                const SizedBox(width: 9),
                Expanded(
                    child: field(context, 'پارەی دراو',
                        NumBox(d.paid, enabled: !walk, onChanged: (_) => setState(() {})))),
              ]),
              const SizedBox(height: 9),
              Row(crossAxisAlignment: CrossAxisAlignment.end, children: [
                Expanded(child: field(context, 'تێبینی', textBox(context, d.note, hintText: 'ئارەزوومەندانە'))),
                const SizedBox(width: 9),
                Btn('هەمووی دراوە', walk ? null : () => setState(() => d.paid.n = tot)),
              ]),
            ]),
          ),
          const SizedBox(width: 22),
          Expanded(
            flex: 2,
            child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              cardRow(context, 'کۆی کاڵاکان', money(s)),
              cardRow(context, 'ماوە (قەرز)', money(due), color: due > eps ? c.red : c.green),
              Row(children: [
                label(context, 'کۆی گشتی', color: c.muted),
                const SizedBox(width: 8),
                // a big total shrinks to fit rather than spill out of the panel
                Expanded(
                  child: FittedBox(
                    fit: BoxFit.scaleDown,
                    alignment: AlignmentDirectional.centerEnd,
                    child: Row(children: [
                      label(context, tot > 0 ? usd(tot) : '', size: 13, color: c.muted),
                      const SizedBox(width: 8),
                      label(context, money(tot), size: 27, w: FontWeight.w800, color: c.goldHi),
                    ]),
                  ),
                ),
              ]),
              const SizedBox(height: 6),
              SizedBox(height: 46, child: Btn.primary('تۆمارکردنی پسووڵە', save)),
            ]),
          ),
        ]),
      ]),
    );

    return Row(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      SizedBox(width: 360, child: side),
      const SizedBox(width: 12),
      Expanded(child: lines),
    ]);
  }

  // ---- لیستی پسووڵەکان ----
  Widget _listTab(BuildContext context) {
    final c = context.pal;
    final where = <String>['1=1'], args = <Object?>[];
    final s = search.text.trim();
    if (s.isNotEmpty) {
      where.add('(IFNULL(c.name,?) LIKE ? OR CAST(i.id AS TEXT)=?)');
      args.addAll([walkIn, '%$s%', asciiDigits(s).replaceAll('#', '')]);
    }
    if (filter == 1) where.add('i.total-i.paid>$eps');
    if (filter == 2) {
      where.add('i.date=?');
      args.add(today());
    }
    final w = where.join(' AND ');
    final rows = db.q("SELECT i.*, IFNULL(c.name,'$walkIn') cn, "
        '(SELECT SUM(total) FROM returns WHERE invoice_id=i.id) rt FROM invoices i '
        'LEFT JOIN customers c ON c.id=i.customer_id WHERE $w ORDER BY i.id DESC LIMIT 150', args);
    final sum = db.one('SELECT COUNT(*) n, IFNULL(SUM(i.total),0) t, IFNULL(SUM(i.total-i.paid),0) d '
        'FROM invoices i LEFT JOIN customers c ON c.id=i.customer_id WHERE $w', args)!;
    if (picked != null && !rows.any((r) => r['id'] == picked)) picked = null;

    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      Row(children: [
        Btn('بینین', () => view(picked)),
        const SizedBox(width: 8),
        Btn('گەڕاندنەوە', () => returnGoods(picked), icon: Icons.assignment_return_outlined),
        const SizedBox(width: 8),
        Btn('PDF', () => pdf(picked), icon: Icons.picture_as_pdf_outlined),
        const SizedBox(width: 8),
        Btn('چاپکردن', () => printInv(picked), icon: Icons.print_outlined),
        const SizedBox(width: 8),
        Btn.danger('سڕینەوە', () => remove(picked)),
        const Spacer(),
        Chips(const ['هەموو', 'قەرز ماوە', 'ئەمڕۆ'], filter, (i) => setState(() => filter = i)),
        const SizedBox(width: 10),
        SearchBox('ژمارەی پسووڵە یان ناوی کڕیار…', search),
      ]),
      const SizedBox(height: 10),
      hint(context, '${sum['n']} پسووڵە   ·   کۆ: ${money(sum['t'])}   ·   ماوە: ${money(sum['d'])}'
          '${(sum['n'] as int) > 150 ? '   ·   تەنها دوایین ١٥٠ پیشان دەدرێن' : ''}'),
      const SizedBox(height: 10),
      Expanded(
        child: CardGrid(minWidth: 230, empty: 'هیچ پسووڵەیەک نەدۆزرایەوە', children: [
          for (final r in rows)
            () {
              final due = toD(r['total']) - toD(r['paid']);
              final (b, tone) = due <= eps
                  ? ('دراوە', c.green)
                  : toD(r['paid']) > eps
                      ? ('بەشێکی دراوە', c.orange)
                      : ('قەرز', c.red);
              return PickCard(
                selected: picked == r['id'],
                onTap: () => setState(() => picked = r['id'] as int),
                onOpen: () => view(r['id'] as int),
                children: [
                  cardHead(context, 'پسووڵە ${no(r['id'])}', sub: r['cn'] as String, badge: b, tone: tone),
                  cardSep(context),
                  cardRow(context, 'بەروار', lrm(r['date']), color: c.muted, strong: false),
                  cardRow(context, 'کۆ', money(r['total'])),
                  if (due > eps) cardRow(context, 'ماوە', money(due), color: c.red),
                  if (toD(r['rt']) > eps) cardRow(context, 'گەڕێنراوە', money(r['rt']), color: c.orange),
                ],
              );
            }(),
        ]),
      ),
    ]);
  }

  bool _need(int? iid) {
    if (iid == null) info(context, 'سەرەتا پسووڵەیەک هەڵبژێرە');
    return iid != null;
  }

  Future<void> pdf(int? iid) async {
    if (!_need(iid)) return;
    if (await savePdf(await docPdf(invoiceDoc(iid!)), 'invoice_$iid.pdf') != null) toast('PDF درووستکرا');
  }

  Future<void> printInv(int? iid) async {
    if (!_need(iid)) return;
    await printPdf(await docPdf(invoiceDoc(iid!)), 'invoice_$iid');
  }

  Future<void> remove(int? iid) async {
    if (!_need(iid)) return;
    final inv = db.one("SELECT i.*, IFNULL(c.name,'$walkIn') cn FROM invoices i "
        'LEFT JOIN customers c ON c.id=i.customer_id WHERE i.id=?', [iid])!;
    if (db.val('SELECT COUNT(*) FROM returns WHERE invoice_id=?', [iid]) > 0) {
      return info(context, 'ئەم پسووڵەیە گەڕاندنەوەی لەسەرە، بۆیە ناسڕدرێتەوە.');
    }
    if (!dayOpen(context, inv['date'] as String)) return;
    if (!await confirm(context, 'پسووڵە ${no(iid)} بسڕدرێتەوە؟\nبڕەکان دەگەڕێنەوە بۆ مەخزەن.\n\n'
        'باشترە لەبری سڕینەوە «گەڕاندنەوە» بەکاربهێنیت، تا مێژووەکە بمێنێتەوە.')) {
      return;
    }
    db.tx(() {
      db.log('sale', 'delete', 'پسووڵە ${no(iid)} سڕایەوە — ${inv['cn']} — ${lrm(inv['date'])} — ${money(inv['total'])}',
          ref: iid, amount: toD(inv['total']));
      for (final r in db.q('SELECT * FROM invoice_items WHERE invoice_id=?', [iid])) {
        db.x('UPDATE items SET qty=qty+? WHERE id=?', [r['qty'], r['item_id']]);
      }
      db.x('DELETE FROM invoice_items WHERE invoice_id=?', [iid]);
      db.x('DELETE FROM invoices WHERE id=?', [iid]);
    });
    appState.changed();
    toast('پسووڵەکە سڕایەوە');
  }

  // ---------------------------------------------------------------- گەڕاندنەوە
  /// Take goods back from invoice [iid]: stock goes up, and their value is
  /// paid back in cash or taken off what the customer owes.
  Future<void> returnGoods(int? iid) async {
    if (!_need(iid)) return;
    final inv = db.one("SELECT i.*, IFNULL(c.name,'$walkIn') cn FROM invoices i "
        'LEFT JOIN customers c ON c.id=i.customer_id WHERE i.id=?', [iid])!;
    final cid = inv['customer_id'] as int?;
    // the invoice discount is shared over its lines, so a return gives back
    // what was really paid for the goods
    final f = toD(inv['subtotal']) > 0 ? toD(inv['total']) / toD(inv['subtotal']) : 1.0;
    final lines = [
      for (final r in db.q("SELECT ii.item_id, IFNULL(it.name,'—') name, IFNULL(it.unit,'') unit, SUM(ii.qty) q, "
          'SUM(ii.qty*ii.price)/SUM(ii.qty) p, SUM(ii.qty*ii.cost)/SUM(ii.qty) cost '
          'FROM invoice_items ii LEFT JOIN items it ON it.id=ii.item_id WHERE ii.invoice_id=? GROUP BY ii.item_id', [iid]))
        (
          id: r['item_id'] as int, name: r['name'] as String, unit: r['unit'] as String,
          sold: toD(r['q']), back: db.returnedQty(iid!, r['item_id'] as int),
          price: toD(r['p']) * f, cost: toD(r['cost']), ctl: NumCtrl(0),
        ),
    ];
    if (lines.every((l) => l.sold - l.back <= eps)) {
      return info(context, 'هەموو کاڵاکانی ئەم پسووڵەیە پێشتر گەڕێنراونەتەوە.');
    }
    final date = DateCtrl(), refund = NumCtrl(), note = TextEditingController();
    var auto = true;   // the refund follows the return until it is typed in
    final owed = cid == null ? 0.0 : db.balance(cid);
    double total() => lines.fold(0, (s, l) => s + l.ctl.n.clamp(0, l.sold - l.back) * l.price);
    // by default the return first clears what the customer owes, the rest is paid back
    double suggested() => cid == null ? total() : (total() - (owed > 0 ? owed : 0)).clamp(0, total()).toDouble();

    final ok = await formDialog<bool>(
      context,
      'گەڕاندنەوەی کاڵا — پسووڵە ${no(iid)}',
      width: 640,
      saveText: 'تۆمارکردنی گەڕاندنەوە',
      body: (c, set) {
        void sync() => set(() {
              if (auto) refund.n = suggested();
            });
        final t = total();
        return [
          hint(c, '${inv['cn']}   ·   ${lrm(inv['date'])}   ·   کۆی پسووڵە ${money(inv['total'])}'),
          Container(
            decoration: BoxDecoration(border: Border.all(color: c.pal.border), borderRadius: BorderRadius.circular(10)),
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
            child: Column(children: [
              Row(children: [
                Expanded(flex: 5, child: label(c, 'کاڵا', size: 13, w: FontWeight.w700, color: c.pal.faint)),
                Expanded(flex: 2, child: label(c, 'فرۆشراو', size: 13, w: FontWeight.w700, color: c.pal.faint)),
                Expanded(flex: 2, child: label(c, 'گەڕاوە', size: 13, w: FontWeight.w700, color: c.pal.faint)),
                Expanded(flex: 3, child: label(c, 'بڕی گەڕاندنەوە', size: 13, w: FontWeight.w700, color: c.pal.faint)),
                Expanded(flex: 3, child: label(c, 'بەها', size: 13, w: FontWeight.w700, color: c.pal.faint, align: TextAlign.end)),
              ]),
              const SizedBox(height: 4),
              for (final l in lines)
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: 4),
                  child: Row(children: [
                    Expanded(flex: 5, child: label(c, l.name, lines: 1)),
                    Expanded(flex: 2, child: label(c, '${fmt(l.sold)} ${l.unit}'.trim(), color: c.pal.muted)),
                    Expanded(flex: 2, child: label(c, fmt(l.back), color: l.back > 0 ? c.pal.orange : c.pal.faint)),
                    Expanded(
                      flex: 3,
                      child: Row(children: [
                        Expanded(child: NumBox(l.ctl, enabled: l.sold - l.back > eps, onChanged: (_) => sync())),
                        IconButton(
                          tooltip: 'هەمووی',
                          icon: const Icon(Icons.keyboard_double_arrow_left, size: 18),
                          onPressed: l.sold - l.back > eps ? () {
                            l.ctl.n = l.sold - l.back;
                            sync();
                          } : null,
                        ),
                      ]),
                    ),
                    Expanded(
                      flex: 3,
                      child: label(c, fmt(l.ctl.n.clamp(0, l.sold - l.back) * l.price),
                          align: TextAlign.end, w: FontWeight.w700),
                    ),
                  ]),
                ),
            ]),
          ),
          formRow(c, 'بەروار', DateBox(date)),
          formRow(c, 'کۆی گەڕاندنەوە', label(c, money(t), size: 17, w: FontWeight.w800, color: c.pal.goldHi)),
          formRow(c, 'پارەی گەڕێنراوە', NumBox(refund, enabled: cid != null, onChanged: (_) => set(() => auto = false))),
          Padding(
            padding: const EdgeInsetsDirectional.only(start: 130),
            child: hint(c, cid == null
                ? 'کڕیاری نەقد: هەموو بەهاکە بە پارە دەگەڕێنرێتەوە.'
                : 'ئەوەی بە پارە نەگەڕێنرێتەوە لە قەرزی کڕیارەکە کەم دەکرێتەوە '
                    '(قەرزی ئێستا: ${money(owed)}، دوای گەڕاندنەوە: ${money(owed - (t - refund.n.clamp(0, t)))}).'),
          ),
          formRow(c, 'تێبینی', textBox(c, note, hintText: 'هۆکاری گەڕاندنەوە')),
        ];
      },
      onSave: (c) {
        if (total() <= eps) {
          info(c, 'بڕی گەڕاندنەوەی لانیکەم یەک کاڵا بنووسە');
          return null;
        }
        for (final l in lines) {
          if (l.ctl.n > l.sold - l.back + eps) {
            info(c, 'لە «${l.name}» تەنها ${fmt(l.sold - l.back)} دەگەڕێتەوە');
            return null;
          }
        }
        if (!dayOpen(c, date.iso)) return null;
        return true;
      },
    );
    if (ok != true) return;
    final t = total();
    final paidBack = cid == null ? t : refund.n.clamp(0, t).toDouble();
    final rid = db.tx(() {
      final rid = db.x('INSERT INTO returns(date,invoice_id,customer_id,total,refund,note) VALUES(?,?,?,?,?,?)',
          [date.iso, iid, cid, t, paidBack, note.text.trim()]);
      for (final l in lines) {
        final q = l.ctl.n.clamp(0, l.sold - l.back).toDouble();
        if (q <= 0) continue;
        db.x('INSERT INTO return_items(return_id,item_id,qty,price,cost) VALUES(?,?,?,?,?)', [rid, l.id, q, l.price, l.cost]);
        db.x('UPDATE items SET qty=qty+? WHERE id=?', [q, l.id]);
      }
      db.log('return', 'add',
          'گەڕاندنەوە ${no(rid)} بۆ پسووڵە ${no(iid)} — ${inv['cn']} — ${money(t)}، پارەی گەڕێنراوە ${money(paidBack)}',
          ref: rid, amount: t);
      return rid;
    });
    appState.changed();
    if (!mounted) return;
    final act = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('تۆمارکرا'),
        content: Text('گەڕاندنەوە ${no(rid)} تۆمارکرا.\nکاڵاکان گەڕانەوە مەخزەن'
            '${paidBack > eps ? '، و ${money(paidBack)} بە پارە بدەرەوە.' : '، و بەهاکەی لە قەرزی کڕیار کەمکرایەوە.'}'),
        actions: [
          Btn('چاپکردن', () => Navigator.pop(ctx, 'print'), icon: Icons.print_outlined),
          Btn('PDF', () => Navigator.pop(ctx, 'pdf'), icon: Icons.picture_as_pdf_outlined),
          Btn.primary('باشە', () => Navigator.pop(ctx)),
        ],
      ),
    );
    if (act == 'print') await printPdf(await docPdf(returnDoc(rid)), 'return_$rid');
    if (act == 'pdf') await savePdf(await docPdf(returnDoc(rid)), 'return_$rid.pdf');
  }

  int? pickedReturn;

  Widget _returnsTab(BuildContext context) {
    final c = context.pal;
    final rows = db.q("SELECT r.*, IFNULL(c.name,'$walkIn') cn, "
        '(SELECT SUM(qty) FROM return_items WHERE return_id=r.id) q FROM returns r '
        'LEFT JOIN customers c ON c.id=r.customer_id ORDER BY r.id DESC LIMIT 300');
    if (pickedReturn != null && pickedReturn! >= rows.length) pickedReturn = null;
    final sel = pickedReturn == null ? null : rows[pickedReturn!]['id'] as int;
    final month = db.val('SELECT SUM(total) FROM returns WHERE date>=?', [isoDate(monthStart())]);
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      Row(children: [
        Btn('PDF', () async {
          if (sel == null) return info(context, 'سەرەتا گەڕاندنەوەیەک هەڵبژێرە');
          await savePdf(await docPdf(returnDoc(sel)), 'return_$sel.pdf');
        }, icon: Icons.picture_as_pdf_outlined),
        const SizedBox(width: 8),
        Btn('چاپکردن', () async {
          if (sel == null) return info(context, 'سەرەتا گەڕاندنەوەیەک هەڵبژێرە');
          await printPdf(await docPdf(returnDoc(sel)), 'return_$sel');
        }, icon: Icons.print_outlined),
        const SizedBox(width: 8),
        Btn.danger('سڕینەوە', () => removeReturn(sel)),
        const Spacer(),
        hint(context, 'بۆ گەڕاندنەوەی نوێ: لە «پسووڵەکان» پسووڵەکە هەڵبژێرە و «گەڕاندنەوە» بکە.'),
      ]),
      const SizedBox(height: 10),
      hint(context, '${rows.length} گەڕاندنەوە   ·   ئەم مانگە: ${money(month)}'),
      const SizedBox(height: 10),
      Expanded(
        child: Grid(
          const [Col('#'), Col('بەروار', flex: 2), Col('پسووڵە'), Col('کڕیار', flex: 3), Col('بڕ'),
              Col('بەها', flex: 2), Col('پارەی گەڕێنراوە', flex: 2), Col('تێبینی', flex: 3)],
          [
            for (final r in rows)
              [
                no(r['id']), lrm(r['date']), no(r['invoice_id']), r['cn'] as String, fmt(r['q']),
                fmt(r['total']), fmt(r['refund']), (r['note'] as String?)?.isNotEmpty == true ? r['note'] as String : '—',
              ]
          ],
          selected: pickedReturn,
          onSelect: (i) => setState(() => pickedReturn = i),
          colors: (r, col) => col == 5 ? c.orange : null,
          empty: 'هێشتا هیچ کاڵایەک نەگەڕێنراوەتەوە',
        ),
      ),
    ]);
  }

  Future<void> removeReturn(int? rid) async {
    if (rid == null) return info(context, 'سەرەتا گەڕاندنەوەیەک هەڵبژێرە');
    final r = db.one("SELECT r.*, IFNULL(c.name,'$walkIn') cn FROM returns r "
        'LEFT JOIN customers c ON c.id=r.customer_id WHERE r.id=?', [rid])!;
    if (!dayOpen(context, r['date'] as String)) return;
    if (!await confirm(context, 'گەڕاندنەوە ${no(rid)} بسڕدرێتەوە؟\nکاڵاکان لە مەخزەن کەم دەکرێنەوە.')) return;
    db.tx(() {
      for (final it in db.q('SELECT * FROM return_items WHERE return_id=?', [rid])) {
        db.x('UPDATE items SET qty=qty-? WHERE id=?', [it['qty'], it['item_id']]);
      }
      db.x('DELETE FROM return_items WHERE return_id=?', [rid]);
      db.x('DELETE FROM returns WHERE id=?', [rid]);
      db.log('return', 'delete',
          'گەڕاندنەوە ${no(rid)} سڕایەوە — پسووڵە ${no(r['invoice_id'])} — ${r['cn']} — ${money(r['total'])}',
          ref: rid, amount: toD(r['total']));
    });
    pickedReturn = null;
    appState.changed();
    toast('گەڕاندنەوەکە سڕایەوە');
  }

  Future<void> view(int? iid) async {
    if (!_need(iid)) return;
    final inv = db.one("SELECT i.*, IFNULL(c.name,'$walkIn') cn FROM invoices i "
        'LEFT JOIN customers c ON c.id=i.customer_id WHERE i.id=?', [iid])!;
    final rows = db.q("SELECT ii.*, IFNULL(it.name,'—') name FROM invoice_items ii "
        'LEFT JOIN items it ON it.id=ii.item_id WHERE ii.invoice_id=?', [iid]);
    final due = toD(inv['total']) - toD(inv['paid']);
    await showDialog<void>(
      context: context,
      builder: (ctx) {
        final c = ctx.pal;
        return AlertDialog(
          title: Text('پسووڵە ${no(iid)}'),
          content: SizedBox(
            width: 640,
            height: 470,
            child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              Row(children: [
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    panelTitle(ctx, inv['cn'] as String),
                    hint(ctx, 'بەروار:  ${lrm(inv['date'])}${(inv['note'] as String?)?.isNotEmpty == true ? '   ·   ${inv['note']}' : ''}'),
                  ]),
                ),
                due <= eps ? Pill('دراوە', color: c.green) : Pill('ماوە: ${money(due)}', color: c.red),
              ]),
              const SizedBox(height: 12),
              Expanded(
                child: Grid(const [Col('کاڵا', flex: 5), Col('بڕ'), Col('نرخ', flex: 2), Col('کۆ', flex: 2)], [
                  for (final r in rows)
                    [r['name'] as String, fmt(r['qty']), fmt(r['price']), fmt(toD(r['qty']) * toD(r['price']))]
                ]),
              ),
              const SizedBox(height: 10),
              cardRow(ctx, 'کۆی کاڵاکان', money(inv['subtotal'])),
              cardRow(ctx, 'داشکاندن', money(inv['discount'])),
              cardRow(ctx, 'کۆی گشتی', money(inv['total']), color: c.goldHi),
              cardRow(ctx, 'پارەی دراو', money(inv['paid']), color: c.green),
              for (final r in db.q('SELECT * FROM returns WHERE invoice_id=? ORDER BY id', [iid]))
                cardRow(ctx, 'گەڕاندنەوە ${no(r['id'])} — ${lrm(r['date'])}', money(r['total']), color: c.orange),
            ]),
          ),
          actions: [
            Btn('PDF', () => pdf(iid), icon: Icons.picture_as_pdf_outlined),
            Btn('چاپکردن', () => printInv(iid), icon: Icons.print_outlined),
            Btn.primary('داخستن', () => Navigator.pop(ctx)),
          ],
        );
      },
    );
  }
}
