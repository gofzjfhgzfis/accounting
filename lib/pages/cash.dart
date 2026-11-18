// سندوق و داخستنی ڕۆژ.
//
// هەموو پارەیەک کە دێت یان دەڕوات (فرۆشتن، وەرگرتنی قەرز، گەڕاندنەوە، کڕین،
// مەسروف، مووچە، و پارەی دەستی) لە سندوقەوە حیساب دەکرێت. لە کۆتایی ڕۆژدا
// پارەکە دەژمێردرێت و بەراورد دەکرێت بەوەی دەبێت هەبێت؛ دوای داخستن، ئەو
// ڕۆژە قفڵ دەبێت.
import 'package:material_ui/material_ui.dart';

import '../core/db.dart';
import '../core/fmt.dart';
import '../print/docs.dart';
import '../ui/theme.dart';
import '../ui/widgets.dart';
import 'dashboard.dart' show eps;
import 'guard.dart';

class CashPage extends StatefulWidget {
  const CashPage({super.key});
  @override
  State<CashPage> createState() => _CashPageState();
}

class _CashPageState extends State<CashPage> {
  final day = DateCtrl();
  int? pickedMove, pickedClosing;

  @override
  void initState() {
    super.initState();
    day.addListener(() => setState(() => pickedMove = null));
  }

  // ---- پارەی دەستی ----
  Future<void> handMove(bool inward) async {
    final date = DateCtrl(), amount = NumCtrl(), note = TextEditingController();
    final ok = await formDialog<bool>(
      context,
      inward ? 'خستنە ناو سندوق' : 'دەرهێنانی پارە لە سندوق',
      body: (c, _) => [
        formRow(c, 'بەروار', DateBox(date)),
        formRow(c, 'بڕ', NumBox(amount)),
        formRow(c, 'تێبینی', textBox(c, note, hintText: inward ? 'بۆ نموونە: پارەی ورد بۆ سەرەتای ڕۆژ' : 'بۆ نموونە: بردنی بۆ بانک')),
      ],
      onSave: (c) => amount.n > 0 && dayOpen(c, date.iso) ? true : null,
    );
    if (ok != true) return;
    final v = inward ? amount.n : -amount.n;
    final id = db.x('INSERT INTO cash_moves(date,amount,note) VALUES(?,?,?)', [date.iso, v, note.text.trim()]);
    db.log('cash', 'add', '${inward ? 'خستنە ناو سندوق' : 'دەرهێنان لە سندوق'} — ${money(amount.n)}'
        '${note.text.trim().isEmpty ? '' : ' — ${note.text.trim()}'}', ref: id, amount: v);
    appState.changed();
    toast(inward ? '${money(amount.n)} خرایە ناو سندوق' : '${money(amount.n)} دەرهێنرا');
  }

  Future<void> deleteMove(List<Move> moves) async {
    final m = pickedMove == null ? null : moves[pickedMove!];
    if (m == null || m.ref == null) {
      return info(context, 'ڕیزێکی «خستنە ناو سندوق» یان «دەرهێنان» هەڵبژێرە.\n'
          'فرۆشتن، پارەدان و مەسروف لە بەشی خۆیان دەسڕدرێنەوە.');
    }
    if (!dayOpen(context, m.date)) return;
    if (!await confirm(context, 'ئەم جوڵەیەی سندوق بسڕدرێتەوە؟\n${m.text} — ${money(m.amount.abs())}')) return;
    db.x('DELETE FROM cash_moves WHERE id=?', [m.ref]);
    db.log('cash', 'delete', 'جوڵەی سندوق سڕایەوە — ${m.text} — ${lrm(m.date)} — ${money(m.amount.abs())}',
        ref: m.ref, amount: m.amount);
    pickedMove = null;
    appState.changed();
  }

  // ---- داخستن ----
  Future<void> closeDay() async {
    final last = db.lastClosing;
    final t = today();
    if (last != null && (last['date'] as String).compareTo(t) >= 0) {
      return info(context, 'ئەمڕۆ پێشتر داخراوە.');
    }
    // the very first closing starts from this morning, with whatever the
    // user says was in the drawer then
    final first = last == null;
    final from = first ? dayBefore(t) : last['date'] as String;
    final openCtl = NumCtrl(first ? 0 : toD(last['counted']));
    final moves = db.cashMoves(from, t);
    final cin = moves.where((m) => m.amount > 0).fold<double>(0, (s, m) => s + m.amount);
    final cout = moves.where((m) => m.amount < 0).fold<double>(0, (s, m) => s - m.amount);
    double expectedNow() => openCtl.n + cin - cout;
    final counted = NumCtrl(expectedNow()), note = TextEditingController();
    var countedTouched = false;

    final ok = await formDialog<bool>(
      context,
      'داخستنی ڕۆژ — ${lrm(t)}',
      width: 480,
      saveText: 'داخستن',
      body: (c, set) {
        final expected = expectedNow();
        final diff = counted.n - expected;
        return [
          hint(c, first
              ? 'یەکەم داخستن: بنووسە بەیانی چەند پارە لە سندوقدا بوو.'
              : 'لە دوای داخستنی ${lrm(from)} ـەوە تا ئەمڕۆ (${moves.length} مامەڵە).'),
          formRow(c, 'پارەی سەرەتا', first
              ? NumBox(openCtl, onChanged: (_) => set(() {
                    if (!countedTouched) counted.n = expectedNow();
                  }))
              : label(c, money(openCtl.n), w: FontWeight.w700)),
          formRow(c, 'هاتن', label(c, money(cin), w: FontWeight.w700, color: c.pal.green)),
          formRow(c, 'دەرچوون', label(c, money(cout), w: FontWeight.w700, color: c.pal.red)),
          formRow(c, 'دەبێت هەبێت', label(c, money(expected), size: 18, w: FontWeight.w800, color: c.pal.goldHi)),
          formRow(c, 'پارەی ژمێردراو', NumBox(counted, onChanged: (_) => set(() => countedTouched = true))),
          formRow(
            c,
            'جیاوازی',
            label(c, diff.abs() <= eps ? 'هیچ — ڕێکە' : '${diff > 0 ? 'زیادە' : 'کەمە'}  ${money(diff.abs())}',
                w: FontWeight.w700, color: diff.abs() <= eps ? c.pal.green : c.pal.red),
          ),
          formRow(c, 'تێبینی', textBox(c, note, hintText: 'ئەگەر جیاوازی هەیە، هۆکارەکەی بنووسە')),
          hint(c, 'دوای داخستن، هیچ مامەڵەیەکی ئەمڕۆ و ڕۆژانی پێشوو ناگۆڕدرێت.'),
        ];
      },
      onSave: (_) => true,
    );
    if (ok != true) return;
    final opening = openCtl.n, expected = expectedNow();
    final n = DateTime.now();
    String two(int v) => v.toString().padLeft(2, '0');
    db.tx(() {
      db.x('INSERT INTO closings(date,at,opening,cash_in,cash_out,expected,counted,note) VALUES(?,?,?,?,?,?,?,?)', [
        t, '${isoDate(n)} ${two(n.hour)}:${two(n.minute)}', opening, cin, cout, expected, counted.n, note.text.trim(),
      ]);
      db.log('cash', 'close',
          'داخستنی ڕۆژ ${lrm(t)} — دەبێت هەبێت ${money(expected)}، ژمێردرا ${money(counted.n)}، جیاوازی ${money(counted.n - expected)}',
          amount: counted.n);
    });
    appState.changed();
    if (!mounted) return;
    final act = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('ڕۆژەکە داخرا'),
        content: Text('ڕاپۆرتی داخستنی ${lrm(t)} چاپ بکرێت؟'),
        actions: [
          Btn('چاپکردن', () => Navigator.pop(ctx, 'print'), icon: Icons.print_outlined),
          Btn('PDF', () => Navigator.pop(ctx, 'pdf'), icon: Icons.picture_as_pdf_outlined),
          Btn.primary('باشە', () => Navigator.pop(ctx)),
        ],
      ),
    );
    if (act == 'print') await printPdf(await docPdf(closingDoc(t)), 'closing_$t');
    if (act == 'pdf') await savePdf(await docPdf(closingDoc(t)), 'closing_$t.pdf');
  }

  Future<void> reopen() async {
    final last = db.lastClosing;
    if (last == null) return info(context, 'هیچ ڕۆژێک دانەخراوە.');
    if (!await confirm(context, 'داخستنی ڕۆژی ${lrm(last['date'])} هەڵبوەشێنرێتەوە؟\n'
        'ئەو ڕۆژە دووبارە دەکرێتەوە بۆ گۆڕانکاری، و ئەمە لە تۆماری چالاکیدا دەنووسرێت.')) {
      return;
    }
    db.x('DELETE FROM closings WHERE id=?', [last['id']]);
    db.log('cash', 'reopen', 'داخستنی ڕۆژی ${lrm(last['date'])} هەڵوەشێنرایەوە — ژمێردرابوو ${money(last['counted'])}');
    pickedClosing = null;
    appState.changed();
  }

  // ---------------------------------------------------------------- ڕووکار
  @override
  Widget build(BuildContext context) {
    final c = context.pal;
    final t = today();
    final todayMoves = db.cashMoves(isoDate(DateTime.now().subtract(const Duration(days: 1))), t);
    final tin = todayMoves.where((m) => m.amount > 0).fold<double>(0, (s, m) => s + m.amount);
    final tout = todayMoves.where((m) => m.amount < 0).fold<double>(0, (s, m) => s - m.amount);
    final last = db.lastClosing;
    final lastDiff = last == null ? 0.0 : toD(last['counted']) - toD(last['expected']);

    final d = day.iso;
    final prevDay = isoDate(day.value.subtract(const Duration(days: 1)));
    final moves = db.cashMoves(prevDay, d);
    final dIn = moves.where((m) => m.amount > 0).fold<double>(0, (s, m) => s + m.amount);
    final dOut = moves.where((m) => m.amount < 0).fold<double>(0, (s, m) => s - m.amount);
    final closings = db.q('SELECT * FROM closings ORDER BY date DESC LIMIT 200');
    if (pickedClosing != null && pickedClosing! >= closings.length) pickedClosing = null;
    final closedToday = last != null && (last['date'] as String).compareTo(t) >= 0;

    final cards = [
      StatCard('پارەی سندوق ئێستا', money(db.cashAt(t)),
          last == null ? 'ئەمڕۆ — هێشتا نەژمێردراوە' : 'دوایین ژماردن + مامەڵەکانی دواتر',
          Icons.point_of_sale_outlined, c.gold),
      StatCard('هاتنی ئەمڕۆ', money(tin), '${todayMoves.where((m) => m.amount > 0).length} مامەڵە',
          Icons.south_west, c.green),
      StatCard('دەرچوونی ئەمڕۆ', money(tout), '${todayMoves.where((m) => m.amount < 0).length} مامەڵە',
          Icons.north_east, c.red),
      StatCard('دوایین داخستن', last == null ? '—' : lrm(last['date']),
          last == null ? 'هێشتا هیچ ڕۆژێک دانەخراوە'
              : lastDiff.abs() <= eps ? 'ڕێک بوو' : 'جیاوازی ${fmt(lastDiff)}',
          Icons.lock_clock_outlined, closedToday ? c.green : c.blue),
    ];

    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      Row(children: [
        for (var i = 0; i < cards.length; i++) ...[
          if (i > 0) const SizedBox(width: 12),
          Expanded(child: SizedBox(height: 104, child: cards[i])),
        ],
      ]),
      const SizedBox(height: 12),
      Row(children: [
        Btn.primary(closedToday ? 'ئەمڕۆ داخراوە' : 'داخستنی ڕۆژ', closedToday ? null : closeDay, icon: Icons.lock_outline),
        const SizedBox(width: 8),
        Btn('خستنە ناو سندوق', () => handMove(true), icon: Icons.add),
        const SizedBox(width: 8),
        Btn('دەرهێنانی پارە', () => handMove(false), icon: Icons.remove),
        const Spacer(),
        Btn.danger('هەڵوەشاندنەوەی دوایین داخستن', last == null ? null : reopen),
      ]),
      const SizedBox(height: 12),
      Expanded(
        child: Row(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Expanded(
            flex: 3,
            child: Panel(
              title: 'مامەڵەکانی سندوق',
              trailing: Row(mainAxisSize: MainAxisSize.min, children: [
                Btn.ghost('سڕینەوەی جوڵەی دەستی', () => deleteMove(moves)),
                const SizedBox(width: 8),
                SizedBox(width: 170, child: DateBox(day)),
              ]),
              child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                Expanded(
                  child: Grid(
                    const [Col('ڕوونکردنەوە', flex: 6), Col('هاتن', flex: 2), Col('دەرچوون', flex: 2)],
                    [for (final m in moves) [m.text, m.amount > 0 ? fmt(m.amount) : '', m.amount < 0 ? fmt(-m.amount) : '']],
                    selected: pickedMove,
                    onSelect: (i) => setState(() => pickedMove = i),
                    colors: (r, col) => col == 1 ? c.green : (col == 2 ? c.red : null),
                    flat: true,
                    empty: 'هیچ پارەیەک لەم ڕۆژەدا نەهاتووە و نەڕۆیشتووە',
                  ),
                ),
                const SizedBox(height: 10),
                Row(children: [
                  hint(context, db.isClosed(d) ? 'ئەم ڕۆژە داخراوە' : 'ئەم ڕۆژە هێشتا کراوەیە'),
                  const Spacer(),
                  label(context, 'هاتن ${fmt(dIn)}', w: FontWeight.w700, color: c.green),
                  const SizedBox(width: 18),
                  label(context, 'دەرچوون ${fmt(dOut)}', w: FontWeight.w700, color: c.red),
                  const SizedBox(width: 18),
                  label(context, 'سافی ${fmt(dIn - dOut)}', w: FontWeight.w800, color: c.title),
                ]),
              ]),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            flex: 2,
            child: Panel(
              title: 'داخستنەکان',
              trailing: Row(mainAxisSize: MainAxisSize.min, children: [
                Btn('PDF', () async {
                  if (pickedClosing == null) return info(context, 'سەرەتا داخستنێک هەڵبژێرە');
                  final dt = closings[pickedClosing!]['date'] as String;
                  await savePdf(await docPdf(closingDoc(dt)), 'closing_$dt.pdf');
                }, icon: Icons.picture_as_pdf_outlined),
                const SizedBox(width: 6),
                Btn('چاپ', () async {
                  if (pickedClosing == null) return info(context, 'سەرەتا داخستنێک هەڵبژێرە');
                  final dt = closings[pickedClosing!]['date'] as String;
                  await printPdf(await docPdf(closingDoc(dt)), 'closing_$dt');
                }, icon: Icons.print_outlined),
              ]),
              child: Grid(
                const [Col('بەروار', flex: 3), Col('دەبێت هەبێت', flex: 3), Col('ژمێردرا', flex: 3), Col('جیاوازی', flex: 2)],
                [
                  for (final r in closings)
                    [lrm(r['date']), fmt(r['expected']), fmt(r['counted']), fmt(toD(r['counted']) - toD(r['expected']))]
                ],
                selected: pickedClosing,
                onSelect: (i) => setState(() => pickedClosing = i),
                colors: (r, col) => col == 3
                    ? ((toD(closings[r]['counted']) - toD(closings[r]['expected'])).abs() <= eps ? c.green : c.red)
                    : null,
                flat: true,
                empty: 'هێشتا هیچ ڕۆژێک دانەخراوە',
              ),
            ),
          ),
        ]),
      ),
    ]);
  }
}
