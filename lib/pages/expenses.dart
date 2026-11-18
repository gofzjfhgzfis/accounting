// مەسروفات، کارمەندان و مووچە.
import 'package:material_ui/material_ui.dart';

import '../core/db.dart';
import '../core/fmt.dart';
import '../ui/theme.dart';
import '../ui/widgets.dart';
import 'dashboard.dart' show eps;

const expenseCats = ['کارەبا', 'سووتەمەنی', 'کرێ', 'گواستنەوە', 'چاککردنەوە', 'بازرگانی', 'هیتر'];

class ExpensesPage extends StatefulWidget {
  const ExpensesPage({super.key});
  @override
  State<ExpensesPage> createState() => _ExpensesPageState();
}

class _ExpensesPageState extends State<ExpensesPage> {
  final search = TextEditingController();
  int tab = 0, filter = 1;
  int? pickedExp, pickedEmp, pickedSal;

  @override
  void initState() {
    super.initState();
    search.addListener(() => setState(() {}));
  }

  // ---- مەسروف ----
  Future<List<Object?>?> expForm([Rec? r]) {
    final date = DateCtrl(r == null ? null : DateTime.tryParse(r['date'] as String));
    final cat = TextEditingController(text: r?['category'] ?? expenseCats.first);
    final amount = NumCtrl(toD(r?['amount'])), note = TextEditingController(text: r?['note'] ?? '');
    final used = [
      for (final c in db.q("SELECT DISTINCT category FROM expenses WHERE IFNULL(category,'')<>''"))
        c['category'] as String
    ];
    final cats = [for (final c in {...expenseCats, ...used}) (c, 0)];
    return formDialog<List<Object?>>(
      context,
      'مەسروف',
      body: (c, _) => [
        formRow(c, 'بەروار', DateBox(date)),
        formRow(c, 'جۆر', PickBox(cats, cat)),
        formRow(c, 'بڕ', NumBox(amount)),
        formRow(c, 'تێبینی', textBox(c, note)),
      ],
      onSave: (_) => amount.n > 0
          ? [date.iso, cat.text.trim().isEmpty ? 'هیتر' : cat.text.trim(), amount.n, note.text.trim()]
          : null,
    );
  }

  Future<void> addExp() async {
    final v = await expForm();
    if (v == null) return;
    db.x('INSERT INTO expenses(date,category,amount,note) VALUES(?,?,?,?)', v);
    appState.changed();
    toast('مەسروفەکە تۆمارکرا');
  }

  Future<void> editExp() async {
    if (pickedExp == null) return info(context, 'سەرەتا مەسروفێک هەڵبژێرە');
    final v = await expForm(db.one('SELECT * FROM expenses WHERE id=?', [pickedExp]));
    if (v == null) return;
    db.x('UPDATE expenses SET date=?,category=?,amount=?,note=? WHERE id=?', [...v, pickedExp]);
    appState.changed();
  }

  Future<void> removeExp() async {
    if (pickedExp == null) return info(context, 'سەرەتا مەسروفێک هەڵبژێرە');
    if (await confirm(context, 'بسڕدرێتەوە؟')) {
      db.x('DELETE FROM expenses WHERE id=?', [pickedExp]);
      pickedExp = null;
      appState.changed();
    }
  }

  // ---- کارمەند ----
  Future<List<Object?>?> empForm([Rec? r]) {
    final name = TextEditingController(text: r?['name'] ?? ''),
        pos = TextEditingController(text: r?['position'] ?? ''),
        phone = TextEditingController(text: r?['phone'] ?? '');
    final salary = NumCtrl(toD(r?['salary']));
    return formDialog<List<Object?>>(
      context,
      'کارمەند',
      canSave: () => name.text.trim().isNotEmpty,
      body: (c, set) => [
        formRow(c, 'ناو', textBox(c, name, autofocus: true, onChanged: (_) => set(() {}))),
        formRow(c, 'پۆست', textBox(c, pos)),
        formRow(c, 'مووچەی مانگانە', NumBox(salary)),
        formRow(c, 'مۆبایل', textBox(c, phone, ltr: true)),
      ],
      onSave: (_) => [name.text.trim(), pos.text.trim(), salary.n, phone.text.trim()],
    );
  }

  Future<void> addEmp() async {
    final v = await empForm();
    if (v == null) return;
    db.x('INSERT INTO employees(name,position,salary,phone) VALUES(?,?,?,?)', v);
    appState.changed();
    toast('کارمەند زیادکرا');
  }

  Future<void> editEmp() async {
    if (pickedEmp == null) return info(context, 'سەرەتا کارمەندێک هەڵبژێرە');
    final v = await empForm(db.one('SELECT * FROM employees WHERE id=?', [pickedEmp]));
    if (v == null) return;
    db.x('UPDATE employees SET name=?,position=?,salary=?,phone=? WHERE id=?', [...v, pickedEmp]);
    appState.changed();
  }

  Future<void> removeEmp() async {
    if (pickedEmp == null) return info(context, 'سەرەتا کارمەندێک هەڵبژێرە');
    if (await confirm(context, 'کارمەندەکە بسڕدرێتەوە؟\nمووچە دراوەکانی لە ڕاپۆرتدا دەمێننەوە.')) {
      db.x('DELETE FROM employees WHERE id=?', [pickedEmp]);
      pickedEmp = null;
      appState.changed();
    }
  }

  Future<void> paySalary() async {
    if (pickedEmp == null) return info(context, 'سەرەتا کارمەندێک هەڵبژێرە');
    final e = db.one('SELECT * FROM employees WHERE id=?', [pickedEmp])!;
    final date = DateCtrl(), amount = NumCtrl(toD(e['salary'])), note = TextEditingController();
    final ok = await formDialog<bool>(
      context,
      'مووچە — ${e['name']}',
      body: (c, _) => [
        formRow(c, 'بەروار', DateBox(date)),
        formRow(c, 'بڕ', NumBox(amount)),
        formRow(c, 'تێبینی', textBox(c, note)),
      ],
      onSave: (_) => amount.n > 0 ? true : null,
    );
    if (ok != true) return;
    db.x('INSERT INTO salaries(date,employee_id,amount,note) VALUES(?,?,?,?)', [date.iso, e['id'], amount.n, note.text.trim()]);
    appState.changed();
    toast('مووچەکە تۆمارکرا');
  }

  // ---------------------------------------------------------------- ڕووکار
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
      Row(children: [tabBtn('مەسروفات', 0), tabBtn('کارمەندان و مووچە', 1)]),
      const SizedBox(height: 14),
      Expanded(child: tab == 0 ? _expenses(context) : _employees(context)),
    ]);
  }

  Widget _expenses(BuildContext context) {
    final c = context.pal;
    final s = '%${search.text.trim()}%';
    var where = "(IFNULL(category,'') LIKE ? OR IFNULL(note,'') LIKE ?)";
    final args = <Object?>[s, s];
    if (filter == 1) {
      where += ' AND date>=?';
      args.add(isoDate(monthStart()));
    }
    final rows = db.q('SELECT * FROM expenses WHERE $where ORDER BY date DESC, id DESC LIMIT 300', args);
    final total = db.val('SELECT SUM(amount) FROM expenses WHERE $where', args);
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      Row(children: [
        Btn.primary('مەسروفی نوێ', addExp, icon: Icons.add),
        const SizedBox(width: 8),
        Btn('دەستکاری', editExp),
        const SizedBox(width: 8),
        Btn.danger('سڕینەوە', removeExp),
        const Spacer(),
        Chips(const ['هەموو', 'ئەم مانگە'], filter, (i) => setState(() => filter = i)),
        const SizedBox(width: 10),
        SearchBox('گەڕان بە جۆر یان تێبینی…', search, width: 220),
      ]),
      const SizedBox(height: 10),
      hint(context, '${rows.length} تۆمار   ·   کۆ: ${money(total)}'),
      const SizedBox(height: 10),
      Expanded(
        child: CardGrid(minWidth: 225, empty: 'هیچ مەسروفێک نەدۆزرایەوە', children: [
          for (final r in rows)
            PickCard(
              selected: pickedExp == r['id'],
              onTap: () => setState(() => pickedExp = r['id'] as int),
              onOpen: editExp,
              children: [
                cardHead(context, (r['category'] as String?) ?? '—', sub: lrm(r['date'])),
                if ((r['note'] as String?)?.isNotEmpty == true) ...[const SizedBox(height: 4), hint(context, r['note'] as String)],
                cardSep(context),
                cardRow(context, 'بڕ', money(r['amount']), color: c.goldHi),
              ],
            ),
        ]),
      ),
    ]);
  }

  Widget _employees(BuildContext context) {
    final c = context.pal;
    final m0 = isoDate(monthStart());
    final emps = db.q('SELECT e.*, (SELECT SUM(amount) FROM salaries WHERE employee_id=e.id AND date>=?) paid '
        'FROM employees e ORDER BY e.name', [m0]);
    final sals = db.q("SELECT s.*, IFNULL(e.name,'—') n FROM salaries s LEFT JOIN employees e ON e.id=s.employee_id "
        'ORDER BY s.date DESC, s.id DESC LIMIT 200');
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      Row(children: [
        Btn.primary('کارمەندی نوێ', addEmp, icon: Icons.add),
        const SizedBox(width: 8),
        Btn('دەستکاری', editEmp),
        const SizedBox(width: 8),
        Btn('دانی مووچە', paySalary, icon: Icons.payments_outlined),
        const SizedBox(width: 8),
        Btn.danger('سڕینەوە', removeEmp),
      ]),
      const SizedBox(height: 12),
      Expanded(
        flex: 3,
        child: CardGrid(empty: 'هێشتا هیچ کارمەندێک تۆمار نەکراوە', children: [
          for (final r in emps)
            () {
              final paid = toD(r['paid']), sal = toD(r['salary']);
              final (b, tone) = paid > 0 && paid >= sal - eps
                  ? ('مووچەی ئەم مانگە دراوە', c.green)
                  : paid > 0
                      ? ('بەشێکی دراوە', c.orange)
                      : ('مووچە نەدراوە', c.red);
              return PickCard(
                selected: pickedEmp == r['id'],
                onTap: () => setState(() => pickedEmp = r['id'] as int),
                onOpen: editEmp,
                children: [
                  cardHead(context, r['name'] as String, sub: (r['position'] as String?) ?? '', avatar: true),
                  const SizedBox(height: 8),
                  Align(alignment: AlignmentDirectional.centerStart, child: Pill(b, color: tone)),
                  if ((r['phone'] as String?)?.isNotEmpty == true) ...[const SizedBox(height: 4), hint(context, lrm(r['phone']))],
                  cardSep(context),
                  cardRow(context, 'مووچەی مانگانە', money(sal), color: c.goldHi),
                ],
              );
            }(),
        ]),
      ),
      const SizedBox(height: 12),
      Row(children: [
        panelTitle(context, 'مووچە دراوەکان'),
        const Spacer(),
        Btn.danger('سڕینەوەی مووچە', () async {
          if (pickedSal == null) return info(context, 'سەرەتا ڕیزێکی مووچە هەڵبژێرە');
          if (await confirm(context, 'ئەم مووچەیە بسڕدرێتەوە؟')) {
            db.x('DELETE FROM salaries WHERE id=?', [sals[pickedSal!]['id']]);
            pickedSal = null;
            appState.changed();
          }
        }),
      ]),
      const SizedBox(height: 10),
      Expanded(
        flex: 2,
        child: Grid(
          const [Col('بەروار', flex: 2), Col('کارمەند', flex: 3), Col('بڕ', flex: 2), Col('تێبینی', flex: 4)],
          [for (final r in sals) [lrm(r['date']), r['n'] as String, fmt(r['amount']), (r['note'] as String?)?.isNotEmpty == true ? r['note'] as String : '—']],
          selected: pickedSal,
          onSelect: (i) => setState(() => pickedSal = i),
          empty: 'هێشتا هیچ مووچەیەک نەدراوە',
        ),
      ),
    ]);
  }
}
