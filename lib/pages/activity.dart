// تۆماری چالاکی: هەموو گۆڕانکارییەک، کەی و لە کام کۆمپیوتەر.
// ئەم تۆمارانە تەنها دەخوێنرێنەوە؛ هیچ شوێنێک نییە بیانسڕێتەوە.
import 'package:material_ui/material_ui.dart';

import '../core/db.dart';
import '../core/fmt.dart';
import '../print/docs.dart';
import '../ui/theme.dart';
import '../ui/widgets.dart';

const _kinds = {
  'sale': 'فرۆشتن', 'return': 'گەڕاندنەوە', 'payment': 'پارەدان', 'cash': 'سندوق',
  'item': 'کاڵا', 'purchase': 'کڕین', 'customer': 'کڕیار', 'supplier': 'دابینکەر',
  'expense': 'مەسروف', 'salary': 'مووچە', 'employee': 'کارمەند', 'settings': 'ڕێکخستن', 'backup': 'باکئەپ',
};
const _actions = {'add': 'زیادکردن', 'edit': 'دەستکاری', 'delete': 'سڕینەوە', 'close': 'داخستن', 'reopen': 'هەڵوەشاندنەوە'};

/// Filter groups: (label, kinds or null for all, only deletions).
const _groups = <(String, List<String>?, bool)>[
  ('هەموو', null, false),
  ('فرۆشتن و گەڕاندنەوە', ['sale', 'return'], false),
  ('پارە و سندوق', ['payment', 'cash', 'expense', 'salary'], false),
  ('مەخزەن و کڕین', ['item', 'purchase'], false),
  ('سڕینەوەکان', null, true),
  ('ڕێکخستن', ['settings', 'backup', 'customer', 'supplier', 'employee'], false),
];

class ActivityPage extends StatefulWidget {
  const ActivityPage({super.key});
  @override
  State<ActivityPage> createState() => _ActivityPageState();
}

class _ActivityPageState extends State<ActivityPage> {
  final search = TextEditingController();
  int range = 1, group = 0;
  int? picked;

  @override
  void initState() {
    super.initState();
    search.addListener(() => setState(() => picked = null));
  }

  List<Rec> rows() {
    final t = DateTime.now();
    final from = [isoDate(t), isoDate(t.subtract(const Duration(days: 6))), isoDate(monthStart(t)), '0000-00-00'][range];
    final where = <String>['at>=?'], args = <Object?>[from];
    final g = _groups[group];
    if (g.$2 != null) {
      where.add('kind IN (${List.filled(g.$2!.length, '?').join(',')})');
      args.addAll(g.$2!);
    }
    if (g.$3) where.add("action='delete'");
    final s = search.text.trim();
    if (s.isNotEmpty) {
      where.add('text LIKE ?');
      args.add('%$s%');
    }
    return db.q('SELECT * FROM activity WHERE ${where.join(' AND ')} ORDER BY id DESC LIMIT 1000', args);
  }

  Doc doc(List<Rec> list) => Doc(
        'تۆماری چالاکی',
        '${_groups[group].$1}   ·   ${['ئەمڕۆ', '٧ ڕۆژی ڕابردوو', 'ئەم مانگە', 'هەموو'][range]}   ·   ${list.length} تۆمار',
        [
          DocTable(['کات', 'جۆر', 'کردار', 'ڕوونکردنەوە'], [4, 3, 3, 14], [
            for (final r in list)
              [lrm(r['at']), _kinds[r['kind']] ?? '${r['kind']}', _actions[r['action']] ?? '${r['action']}', r['text'] as String]
          ]),
        ],
      );

  @override
  Widget build(BuildContext context) {
    final c = context.pal;
    final list = rows();
    if (picked != null && picked! >= list.length) picked = null;
    final sel = picked == null ? null : list[picked!];
    final deletes = list.where((r) => r['action'] == 'delete').length;
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      Row(children: [
        Chips(const ['ئەمڕۆ', '٧ ڕۆژ', 'ئەم مانگە', 'هەموو'], range, (i) => setState(() {
              range = i;
              picked = null;
            })),
        const Spacer(),
        Btn('PDF', () async => savePdf(await docPdf(doc(list)), 'activity_${today()}.pdf'), icon: Icons.picture_as_pdf_outlined),
        const SizedBox(width: 8),
        Btn('چاپکردن', () async => printPdf(await docPdf(doc(list)), 'activity'), icon: Icons.print_outlined),
        const SizedBox(width: 10),
        SearchBox('گەڕان لە ڕوونکردنەوە…', search, width: 230),
      ]),
      const SizedBox(height: 10),
      Row(children: [
        Chips([for (final g in _groups) g.$1], group, (i) => setState(() {
              group = i;
              picked = null;
            })),
        const Spacer(),
        hint(context, '${list.length} تۆمار${deletes > 0 ? '   ·   $deletes سڕینەوە' : ''}'
            '${list.length == 1000 ? '   ·   تەنها دوایین ١٠٠٠ پیشان دەدرێن' : ''}'),
      ]),
      const SizedBox(height: 10),
      Expanded(
        child: Grid(
          const [Col('کات', flex: 3), Col('جۆر', flex: 2), Col('کردار', flex: 2), Col('ڕوونکردنەوە', flex: 11),
              Col('کۆمپیوتەر', flex: 2)],
          [
            for (final r in list)
              [
                lrm(r['at']), _kinds[r['kind']] ?? '${r['kind']}', _actions[r['action']] ?? '${r['action']}',
                r['text'] as String, (r['device'] as String?) ?? '',
              ]
          ],
          selected: picked,
          onSelect: (i) => setState(() => picked = i),
          colors: (r, col) => col == 2
              ? switch (list[r]['action']) {
                  'delete' => c.red,
                  'reopen' => c.orange,
                  'close' => c.green,
                  _ => null,
                }
              : (col == 0 || col == 4 ? c.muted : null),
          empty: 'هیچ چالاکییەک لەم ماوەیەدا نییە',
        ),
      ),
      const SizedBox(height: 10),
      Panel(
        padding: const EdgeInsets.fromLTRB(18, 12, 18, 12),
        child: sel == null
            ? hint(context, 'ڕیزێک هەڵبژێرە بۆ بینینی تەواوی ڕوونکردنەوەکەی.')
            : Row(children: [
                Pill(_kinds[sel['kind']] ?? '${sel['kind']}', color: sel['action'] == 'delete' ? c.red : c.gold),
                const SizedBox(width: 12),
                Expanded(child: SelectableText(sel['text'] as String, style: st(context, size: 14.5, color: c.title))),
                const SizedBox(width: 12),
                label(context, lrm(sel['at']), color: c.muted),
              ]),
      ),
    ]);
  }
}
