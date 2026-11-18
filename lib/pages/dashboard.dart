// داشبۆرد: کارتی ئامار، چارتی فرۆشتن، قەرزداران و کاڵای کەمبوو.
import 'package:material_ui/material_ui.dart';

import '../core/db.dart';
import '../core/fmt.dart';
import '../ui/theme.dart';
import '../ui/widgets.dart';

const eps = 0.004;

class DashboardPage extends StatefulWidget {
  const DashboardPage({super.key});
  @override
  State<DashboardPage> createState() => _DashboardPageState();
}

class _DashboardPageState extends State<DashboardPage> {
  int range = 1;   // ٧ ڕۆژ / ٣٠ ڕۆژ / ١٢ مانگ

  @override
  Widget build(BuildContext context) {
    final c = context.pal;
    final t = DateTime.now();
    final m0 = monthStart(t);
    final p1 = m0.subtract(const Duration(days: 1));
    final day = db.period(isoDate(t), isoDate(t));
    final cur = db.period(isoDate(m0), isoDate(t));
    final prev = db.period(isoDate(monthStart(p1)), isoDate(p1));
    final debts = db.customers().where((r) => toD(r['bal']) > eps).toList()
      ..sort((a, b) => toD(b['bal']).compareTo(toD(a['bal'])));
    final sups = db.suppliers().where((r) => toD(r['bal']) > eps).toList();
    final stock = db.one('SELECT IFNULL(SUM(qty*cost),0) v, COUNT(*) n FROM items')!;
    final low = db.q('SELECT * FROM items WHERE minq>0 AND qty<=minq ORDER BY qty*1.0/minq');
    final totalDebt = debts.fold<double>(0, (s, r) => s + toD(r['bal']));
    final supDebt = sups.fold<double>(0, (s, r) => s + toD(r['bal']));

    final cards = [
      StatCard('فرۆشتنی ئەمڕۆ', money(day.sales), '${day.count} پسووڵە', Icons.payments_outlined, c.green),
      StatCard('فرۆشتنی ئەم مانگە', money(cur.sales), 'مانگی پێشوو: ${fmt(prev.sales)}', Icons.receipt_long_outlined, c.blue),
      StatCard('قازانجی ئەم مانگە', money(cur.net), 'دوای تێچوو، مەسروفات و مووچە', Icons.trending_up, c.gold),
      StatCard('قەرزی کڕیاران', money(totalDebt), '${debts.length} کڕیار قەرزدارن', Icons.people_alt_outlined, c.red),
      StatCard('قەرزی دابینکەران', money(supDebt), 'بۆ ${sups.length} دابینکەر', Icons.local_shipping_outlined, c.orange),
      StatCard('بەهای مەخزەن', money(stock['v']), '${stock['n']} کاڵا   ${usd(stock['v'])}'.trim(),
          Icons.inventory_2_outlined, c.violet),
    ];

    final data = _chartData();
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      for (var r = 0; r < 2; r++) ...[
        Row(children: [
          for (var i = 0; i < 3; i++) ...[
            if (i > 0) const SizedBox(width: 12),
            Expanded(child: SizedBox(height: 104, child: cards[r * 3 + i])),
          ],
        ]),
        const SizedBox(height: 12),
      ],
      Expanded(
        child: Row(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Expanded(
            flex: 5,
            child: Panel(
              title: 'فرۆشتن',
              trailing: Chips(const ['٧ ڕۆژ', '٣٠ ڕۆژ', '١٢ مانگ'], range, (i) => setState(() => range = i)),
              child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                hint(context, 'کۆی ئەم ماوەیە:  ${money(data.fold<double>(0, (s, d) => s + d.$2))}'),
                const SizedBox(height: 6),
                Expanded(child: BarChart(data)),
              ]),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            flex: 3,
            child: ListCard('گەورەترین قەرزداران', 'هیچ کڕیارێک قەرزدار نییە',
                [for (final r in debts.take(8)) (r['name'] as String, fmt(r['bal']), c.red)]),
          ),
          const SizedBox(width: 12),
          Expanded(
            flex: 3,
            child: ListCard('کاڵای کەمبوو', 'هیچ کاڵایەک کەم نەبووە',
                [for (final r in low.take(8)) (r['name'] as String, ltrRun('${fmt(r['qty'])} / ${fmt(r['minq'])}'), c.red)]),
          ),
        ]),
      ),
    ]);
  }

  List<(String, double, String)> _chartData() {
    final t = DateTime.now();
    final cur = db.get('currency');
    if (range == 2) {
      final keys = <String>[];
      var y = t.year, m = t.month;
      for (var i = 0; i < 12; i++) {
        keys.add('${y.toString().padLeft(4, '0')}-${m.toString().padLeft(2, '0')}');
        if (--m == 0) {
          y--;
          m = 12;
        }
      }
      final ks = keys.reversed.toList();
      final got = {
        for (final r in db.q('SELECT substr(date,1,7) k, SUM(total) t FROM invoices WHERE date>=? GROUP BY k', ['${ks.first}-01']))
          r['k'] as String: toD(r['t'])
      };
      return [
        for (final k in ks)
          ('${int.parse(k.substring(5))}/${k.substring(2, 4)}', got[k] ?? 0, '${lrm(k)}\n${fmt(got[k] ?? 0)} $cur')
      ];
    }
    final n = range == 0 ? 7 : 30;
    final days = [for (var i = n - 1; i >= 0; i--) DateTime(t.year, t.month, t.day - i)];
    final got = {
      for (final r in db.q('SELECT date, SUM(total) t FROM invoices WHERE date>=? GROUP BY date', [isoDate(days.first)]))
        r['date'] as String: toD(r['t'])
    };
    return [
      for (final d in days)
        ('${d.day}/${d.month}', got[isoDate(d)] ?? 0, '${lrm(isoDate(d))}\n${fmt(got[isoDate(d)] ?? 0)} $cur')
    ];
  }
}
