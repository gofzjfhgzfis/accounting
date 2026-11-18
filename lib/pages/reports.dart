// ڕاپۆرت: قازانج بۆ هەر ماوەیەک، چارت، باشترین کاڵا و کڕیاران، PDF و CSV.
import 'dart:io';

import 'package:file_selector/file_selector.dart';
import 'package:material_ui/material_ui.dart';
import 'package:path/path.dart' as p;

import '../core/config.dart';
import '../core/db.dart';
import '../core/fmt.dart';
import '../print/docs.dart';
import '../ui/theme.dart';
import '../ui/widgets.dart';
import 'dashboard.dart' show eps;

class ReportsPage extends StatefulWidget {
  const ReportsPage({super.key});
  @override
  State<ReportsPage> createState() => ReportsPageState();
}

class ReportsPageState extends State<ReportsPage> {
  int preset = 2;
  final from = DateCtrl(monthStart()), to = DateCtrl();

  @override
  void initState() {
    super.initState();
    from.addListener(() => setState(() {}));
    to.addListener(() => setState(() {}));
  }

  void applyPreset(int i) {
    final t = DateTime.now();
    preset = i;
    from.value = [DateTime(t.year, t.month, t.day), DateTime(t.year, t.month, t.day - 6), monthStart(t), DateTime(t.year)][i];
    to.value = t;
  }

  String get a => from.iso;
  String get b => to.iso;

  /// Best sellers, after taking off goods that came back.
  List<Rec> topItems() => db.q(
      "SELECT IFNULL(it.name,'—') n, SUM(t.q) q, SUM(t.v) v, SUM(t.pr) pr FROM ("
      'SELECT ii.item_id id, ii.qty q, ii.qty*ii.price v, ii.qty*(ii.price-ii.cost) pr FROM invoice_items ii '
      'JOIN invoices i ON i.id=ii.invoice_id WHERE i.date BETWEEN ? AND ? '
      'UNION ALL SELECT ri.item_id, -ri.qty, -ri.qty*ri.price, -ri.qty*(ri.price-ri.cost) FROM return_items ri '
      'JOIN returns r ON r.id=ri.return_id WHERE r.date BETWEEN ? AND ?'
      ') t LEFT JOIN items it ON it.id=t.id GROUP BY t.id HAVING SUM(t.q)>0 ORDER BY v DESC LIMIT 15', [a, b, a, b]);

  List<Rec> topCustomers() => db.q(
      "SELECT IFNULL(c.name,'$walkIn') n, COUNT(*) k, SUM(i.total) v FROM invoices i "
      'LEFT JOIN customers c ON c.id=i.customer_id WHERE i.date BETWEEN ? AND ? '
      'GROUP BY i.customer_id ORDER BY v DESC LIMIT 15', [a, b]);

  List<(String, double, String)> chart() {
    final cur = db.get('currency');
    final d0 = from.value, d1 = to.value;
    final days = d1.difference(DateTime(d0.year, d0.month, d0.day)).inDays;
    if (days <= 45) {
      final got = {
        for (final r in db.q('SELECT date k, SUM(total) t FROM invoices WHERE date BETWEEN ? AND ? GROUP BY date', [a, b]))
          r['k'] as String: toD(r['t'])
      };
      return [
        for (var i = 0; i <= (days < 0 ? 0 : days); i++)
          () {
            final d = DateTime(d0.year, d0.month, d0.day + i), k = isoDate(d);
            return ('${d.day}/${d.month}', got[k] ?? 0, '${lrm(k)}\n${fmt(got[k] ?? 0)} $cur');
          }()
      ];
    }
    final got = {
      for (final r in db.q('SELECT substr(date,1,7) k, SUM(total) t FROM invoices WHERE date BETWEEN ? AND ? GROUP BY k', [a, b]))
        r['k'] as String: toD(r['t'])
    };
    final out = <(String, double, String)>[];
    var y = d0.year, m = d0.month;
    while (y < d1.year || (y == d1.year && m <= d1.month)) {
      final k = '${y.toString().padLeft(4, '0')}-${m.toString().padLeft(2, '0')}';
      out.add(('$m/${k.substring(2, 4)}', got[k] ?? 0, '${lrm(k)}\n${fmt(got[k] ?? 0)} $cur'));
      if (++m == 13) {
        y++;
        m = 1;
      }
    }
    return out;
  }

  Doc reportDoc() {
    final pr = db.period(a, b);
    final debts = db.customers().where((r) => toD(r['bal']) > eps).toList()
      ..sort((x, y) => toD(y['bal']).compareTo(toD(x['bal'])));
    final low = db.q('SELECT * FROM items WHERE minq>0 AND qty<=minq');
    const ink = Color(0xFF2B2F36);
    String m(double v) => money(v);
    return Doc('ڕاپۆرتی گشتی', '${lrm(a)}   تا   ${lrm(b)}', [
      Totals([
        ('کۆی فرۆشتن — ${pr.count} پسووڵە', m(pr.sales + pr.returns), true, ink, true),
        ('گەڕاندنەوە', m(pr.returns), false, ink, false),
        ('فرۆشتنی سافی', m(pr.sales), true, ink, true),
        ('تێچووی کاڵای فرۆشراو', m(pr.cogs), false, ink, false),
        ('قازانجی خاو', m(pr.gross), true, ink, true),
        ('مەسروفات', m(pr.exp), false, ink, false),
        ('مووچەکان', m(pr.sal), false, ink, false),
        ('قازانجی سافی', m(pr.net), true, ink, true),
        ('کڕینی کاڵا', m(pr.pur), false, ink, false),
      ]),
      Heading('باشترین کاڵا فرۆشراوەکان'),
      DocTable(['کاڵا', 'بڕ', 'فرۆشتن', 'قازانج'], [8, 3, 4, 4],
          [for (final r in topItems()) [r['n'] as String, fmt(r['q']), fmt(r['v']), fmt(r['pr'])]]),
      Heading('باشترین کڕیاران'),
      DocTable(['کڕیار', 'پسووڵە', 'کۆ'], [8, 3, 4], [for (final r in topCustomers()) [r['n'] as String, '${r['k']}', fmt(r['v'])]]),
      Heading('قەرزی کڕیاران'),
      DocTable(['کڕیار', 'مۆبایل', 'قەرز'], [8, 5, 4],
          [for (final r in debts) [r['name'] as String, lrm(r['phone'] ?? ''), fmt(r['bal'])]]),
      Heading('کاڵای کەمبوو'),
      DocTable(['کاڵا', 'بڕی ماوە', 'کەمترین بڕ'], [8, 4, 4],
          [for (final r in low) [r['name'] as String, fmt(r['qty']), fmt(r['minq'])]]),
    ]);
  }

  Future<void> csv() async {
    final dir = await getDirectoryPath(initialDirectory: appDir, confirmButtonText: 'هەڵبژاردن');
    if (dir == null) return;
    void write(String name, List<String> head, List<List<Object?>> rows) {
      String cell(Object? v) {
        final s = '${v ?? ''}';
        return s.contains(RegExp('[",\n]')) ? '"${s.replaceAll('"', '""')}"' : s;
      }

      final b = StringBuffer(String.fromCharCode(0xFEFF))..writeln(head.map(cell).join(','));
      for (final r in rows) {
        b.writeln(r.map(cell).join(','));
      }
      File(p.join(dir, name)).writeAsStringSync(b.toString());
    }

    try {
      write('inventory.csv', ['ناو', 'جۆر', 'یەکە', 'بارکۆد', 'بڕ', 'تێچوو', 'نرخ'], [
        for (final r in db.q('SELECT * FROM items ORDER BY name'))
          [r['name'], r['kind'], r['unit'], r['barcode'], r['qty'], r['cost'], r['price']]
      ]);
      write('debts.csv', ['کڕیار', 'مۆبایل', 'قەرز'], [for (final c in db.customers()) [c['name'], c['phone'], c['bal']]]);
      write('suppliers.csv', ['دابینکەر', 'مۆبایل', 'قەرز'], [for (final s in db.suppliers()) [s['name'], s['phone'], s['bal']]]);
      write('invoices.csv', ['ژمارە', 'بەروار', 'کڕیار', 'کۆ', 'داشکاندن', 'دوای داشکاندن', 'دراو'], [
        for (final r in db.q("SELECT i.*, IFNULL(c.name,'$walkIn') cn FROM invoices i LEFT JOIN customers c ON c.id=i.customer_id "
            'WHERE i.date BETWEEN ? AND ? ORDER BY i.id', [a, b]))
          [r['id'], r['date'], r['cn'], r['subtotal'], r['discount'], r['total'], r['paid']]
      ]);
      write('returns.csv', ['ژمارە', 'بەروار', 'پسووڵە', 'کڕیار', 'بەها', 'پارەی گەڕێنراوە', 'تێبینی'], [
        for (final r in db.q("SELECT r.*, IFNULL(c.name,'$walkIn') cn FROM returns r LEFT JOIN customers c ON c.id=r.customer_id "
            'WHERE r.date BETWEEN ? AND ? ORDER BY r.id', [a, b]))
          [r['id'], r['date'], r['invoice_id'], r['cn'], r['total'], r['refund'], r['note']]
      ]);
      write('expenses.csv', ['بەروار', 'جۆر', 'بڕ', 'تێبینی'], [
        for (final r in db.q('SELECT * FROM expenses WHERE date BETWEEN ? AND ? ORDER BY date', [a, b]))
          [r['date'], r['category'], r['amount'], r['note']]
      ]);
    } catch (e) {
      if (mounted) info(context, 'نەتوانرا هەناردە بکرێت:\n$e');
      return;
    }
    toast('٦ فایلی CSV هەناردەکران');
    openPath(dir);
  }

  @override
  Widget build(BuildContext context) {
    final c = context.pal;
    final pr = db.period(a, b);
    final items = topItems(), custs = topCustomers();
    final cards = [
      StatCard('کۆی فرۆشتن', money(pr.sales),
          pr.returns > eps ? '${pr.count} پسووڵە  ·  گەڕاندنەوە ${fmt(pr.returns)}' : '${pr.count} پسووڵە   ${usd(pr.sales)}',
          Icons.receipt_long_outlined, c.blue),
      StatCard('قازانجی خاو', money(pr.gross), 'تێچووی کاڵا: ${fmt(pr.cogs)}', Icons.trending_up, c.green),
      StatCard('مەسروفات و مووچە', money(pr.exp + pr.sal), 'مەسروف ${fmt(pr.exp)}  ·  مووچە ${fmt(pr.sal)}',
          Icons.account_balance_wallet_outlined, c.red),
      StatCard('قازانجی سافی', money(pr.net), 'کڕینی کاڵا: ${fmt(pr.pur)}', Icons.payments_outlined, c.gold),
    ];
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      Row(children: [
        Chips(const ['ئەمڕۆ', '٧ ڕۆژ', 'ئەم مانگە', 'ئەم ساڵ'], preset, (i) => setState(() => applyPreset(i))),
        const SizedBox(width: 14),
        label(context, 'لە', color: c.muted),
        const SizedBox(width: 6),
        SizedBox(width: 160, child: DateBox(from)),
        const SizedBox(width: 10),
        label(context, 'بۆ', color: c.muted),
        const SizedBox(width: 6),
        SizedBox(width: 160, child: DateBox(to)),
        const Spacer(),
        Btn('PDF', () async {
          if (await savePdf(await docPdf(reportDoc()), 'report_$b.pdf') != null) toast('ڕاپۆرتەکە پاشەکەوتکرا');
        }, icon: Icons.picture_as_pdf_outlined),
        const SizedBox(width: 8),
        Btn('چاپکردن', () async => printPdf(await docPdf(reportDoc()), 'report_$b'), icon: Icons.print_outlined),
        const SizedBox(width: 8),
        Btn('CSV', csv),
      ]),
      const SizedBox(height: 12),
      Row(children: [
        for (var i = 0; i < cards.length; i++) ...[
          if (i > 0) const SizedBox(width: 12),
          Expanded(child: SizedBox(height: 104, child: cards[i])),
        ],
      ]),
      const SizedBox(height: 12),
      Expanded(
        child: Row(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Expanded(flex: 4, child: Panel(title: 'فرۆشتن بەپێی کات', child: BarChart(chart()))),
          const SizedBox(width: 12),
          Expanded(
            flex: 5,
            child: Panel(
              title: 'باشترین کاڵاکان',
              child: Grid(const [Col('کاڵا', flex: 4), Col('بڕ', flex: 2), Col('فرۆشتن', flex: 3), Col('قازانج', flex: 3)],
                  [for (final r in items) [r['n'] as String, fmt(r['q']), fmt(r['v']), fmt(r['pr'])]],
                  flat: true, empty: 'هیچ فرۆشتنێک لەم ماوەیەدا نییە'),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            flex: 4,
            child: Panel(
              title: 'باشترین کڕیاران',
              child: Grid(const [Col('کڕیار', flex: 4), Col('پسووڵە', flex: 2), Col('کۆ', flex: 3)],
                  [for (final r in custs) [r['n'] as String, '${r['k']}', fmt(r['v'])]],
                  flat: true, empty: 'هیچ فرۆشتنێک لەم ماوەیەدا نییە'),
            ),
          ),
        ]),
      ),
    ]);
  }
}
