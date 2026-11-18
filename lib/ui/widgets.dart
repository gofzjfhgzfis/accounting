// پارچە هاوبەشەکانی ڕووکار: دوگمە، خانە، کارت، خشتە، چارت و دیالۆگ.
import 'package:flutter/services.dart';
import 'package:material_ui/material_ui.dart';

import '../core/fmt.dart';
import 'theme.dart';

// ---------------------------------------------------------------- گۆڕانکاری
/// Bumped after every write so the pages on screen redraw from the database.
class AppState extends ChangeNotifier {
  int rev = 0;
  void changed() {
    rev++;
    notifyListeners();
  }
}

final appState = AppState();
final messengerKey = GlobalKey<ScaffoldMessengerState>();

/// A short confirmation that disappears by itself.
void toast(String text) {
  messengerKey.currentState
    ?..hideCurrentSnackBar()
    ..showSnackBar(SnackBar(
      content: Text(text, textAlign: TextAlign.center),
      duration: const Duration(milliseconds: 2600),
    ));
}

// ---------------------------------------------------------------- دەق
TextStyle st(BuildContext c, {double size = 14, FontWeight w = FontWeight.w400, Color? color}) =>
    TextStyle(fontFamily: fontFamily, fontSize: size, fontWeight: w, color: color ?? c.pal.text);

Widget label(BuildContext c, String t,
        {double size = 14, FontWeight w = FontWeight.w400, Color? color, TextAlign? align, int? lines}) =>
    Text(t,
        style: st(c, size: size, w: w, color: color),
        textAlign: align,
        maxLines: lines,
        overflow: lines == null ? null : TextOverflow.ellipsis);

Widget hint(BuildContext c, String t) => label(c, t, size: 13.5, color: c.pal.muted);

Widget heading(BuildContext c, String t) => label(c, t, size: 13, w: FontWeight.w700, color: c.pal.muted);

Widget panelTitle(BuildContext c, String t) => label(c, t, size: 16, w: FontWeight.w700, color: c.pal.title);

// ---------------------------------------------------------------- دوگمە
enum BtnKind { normal, primary, danger, ghost }

class Btn extends StatelessWidget {
  final String text;
  final VoidCallback? onPressed;
  final IconData? icon;
  final BtnKind kind;
  final String? tip;
  const Btn(this.text, this.onPressed, {super.key, this.icon, this.kind = BtnKind.normal, this.tip});
  const Btn.primary(this.text, this.onPressed, {super.key, this.icon, this.tip}) : kind = BtnKind.primary;
  const Btn.danger(this.text, this.onPressed, {super.key, this.icon, this.tip}) : kind = BtnKind.danger;
  const Btn.ghost(this.text, this.onPressed, {super.key, this.icon, this.tip}) : kind = BtnKind.ghost;

  @override
  Widget build(BuildContext context) {
    final c = context.pal;
    final child = icon == null
        ? Text(text)
        : Row(mainAxisSize: MainAxisSize.min, children: [Icon(icon, size: 18), const SizedBox(width: 7), Text(text)]);
    final Widget b = switch (kind) {
      BtnKind.primary => FilledButton(onPressed: onPressed, child: child),
      BtnKind.danger => OutlinedButton(
          onPressed: onPressed,
          style: OutlinedButton.styleFrom(
              backgroundColor: Colors.transparent,
              foregroundColor: c.red,
              side: BorderSide(color: c.soft(c.red, .4))),
          child: child),
      BtnKind.ghost => TextButton(onPressed: onPressed, child: child),
      BtnKind.normal => OutlinedButton(onPressed: onPressed, child: child),
    };
    return tip == null ? b : Tooltip(message: tip!, child: b);
  }
}

// ---------------------------------------------------------------- کارت
class Panel extends StatelessWidget {
  final Widget child;
  final EdgeInsets padding;
  final String? title;
  final Widget? trailing;
  const Panel({super.key, required this.child, this.padding = const EdgeInsets.fromLTRB(18, 16, 18, 16), this.title, this.trailing});

  @override
  Widget build(BuildContext context) {
    final c = context.pal;
    return Container(
      decoration: BoxDecoration(color: c.card, borderRadius: BorderRadius.circular(14), border: Border.all(color: c.border)),
      padding: padding,
      child: title == null
          ? child
          : Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              Row(children: [panelTitle(context, title!), const Spacer(), ?trailing]),
              const SizedBox(height: 12),
              Expanded(child: child),
            ]),
    );
  }
}

class Pill extends StatelessWidget {
  final String text;
  final Color? color;
  const Pill(this.text, {super.key, this.color});

  @override
  Widget build(BuildContext context) {
    final c = context.pal;
    final col = color ?? c.muted;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 3),
      decoration: BoxDecoration(
          color: color == null ? c.btn : c.soft(col, .16), borderRadius: BorderRadius.circular(9)),
      child: Text(text, style: st(context, size: 12.5, w: FontWeight.w700, color: col)),
    );
  }
}

class IconTile extends StatelessWidget {
  final IconData icon;
  final Color color;
  final double size;
  const IconTile(this.icon, this.color, {super.key, this.size = 44});

  @override
  Widget build(BuildContext context) => Container(
        width: size,
        height: size,
        decoration: BoxDecoration(color: context.pal.soft(color, .16), borderRadius: BorderRadius.circular(12)),
        child: Icon(icon, color: color, size: size * .48),
      );
}

class StatCard extends StatelessWidget {
  final String caption, value, sub;
  final IconData icon;
  final Color color;
  const StatCard(this.caption, this.value, this.sub, this.icon, this.color, {super.key});

  @override
  Widget build(BuildContext context) {
    final c = context.pal;
    return Panel(
      padding: const EdgeInsets.fromLTRB(16, 14, 16, 14),
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        IconTile(icon, color),
        const SizedBox(width: 13),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            label(context, caption, size: 14, color: c.muted),
            const SizedBox(height: 2),
            FittedBox(
              fit: BoxFit.scaleDown,
              alignment: AlignmentDirectional.centerStart,
              child: label(context, value, size: 23, w: FontWeight.w700, color: c.title),
            ),
            if (sub.isNotEmpty) label(context, sub, size: 13, color: c.muted, lines: 1),
          ]),
        ),
      ]),
    );
  }
}

// ---------------------------------------------------------------- کارتی هەڵبژاردن
class PickCard extends StatefulWidget {
  final bool selected;
  final VoidCallback onTap;
  final VoidCallback? onOpen;
  final List<Widget> children;
  const PickCard({super.key, required this.selected, required this.onTap, this.onOpen, required this.children});

  @override
  State<PickCard> createState() => _PickCardState();
}

class _PickCardState extends State<PickCard> {
  bool hover = false;
  DateTime _last = DateTime(2000);

  /// Select at once; a second click within a moment opens the record. (A
  /// double-tap recogniser would hold every single click back by 300 ms.)
  void _tap() {
    final now = DateTime.now();
    final second = now.difference(_last) < const Duration(milliseconds: 400);
    _last = second ? DateTime(2000) : now;
    widget.onTap();
    if (second) widget.onOpen?.call();
  }

  @override
  Widget build(BuildContext context) {
    final c = context.pal;
    return MouseRegion(
      cursor: SystemMouseCursors.click,
      onEnter: (_) => setState(() => hover = true),
      onExit: (_) => setState(() => hover = false),
      child: GestureDetector(
        onTap: _tap,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 120),
          padding: const EdgeInsets.fromLTRB(16, 14, 16, 14),
          decoration: BoxDecoration(
            color: widget.selected ? c.soft(c.gold, .07) : (hover ? c.cardHi : c.card),
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: widget.selected ? c.gold : (hover ? c.borderHi : c.border)),
          ),
          child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, mainAxisSize: MainAxisSize.min, children: widget.children),
        ),
      ),
    );
  }
}

/// Title row of a card: optional avatar, title + subtitle, optional status pill.
Widget cardHead(BuildContext c, String title, {String sub = '', String? badge, Color? tone, bool avatar = false}) {
  final p = c.pal;
  return Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
    if (avatar) ...[
      Container(
        width: 38,
        height: 38,
        alignment: Alignment.center,
        decoration: BoxDecoration(color: p.soft(p.gold, .14), shape: BoxShape.circle),
        child: label(c, title.trim().isEmpty ? '؟' : title.trim().characters.first,
            size: 16, w: FontWeight.w700, color: p.goldHi),
      ),
      const SizedBox(width: 11),
    ],
    Expanded(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        label(c, title, size: 16, w: FontWeight.w700, color: p.title, lines: 2),
        if (sub.isNotEmpty) label(c, sub, size: 13.5, color: p.muted, lines: 1),
      ]),
    ),
    if (badge != null) Pill(badge, color: tone),
  ]);
}

Widget cardSep(BuildContext c) =>
    Padding(padding: const EdgeInsets.symmetric(vertical: 9), child: Divider(height: 1, color: c.pal.line));

Widget cardRow(BuildContext c, String key, String value, {Color? color, bool strong = true}) => Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(children: [
        label(c, key, size: 14, color: c.pal.muted),
        const SizedBox(width: 8),
        Expanded(
          child: Text(value,
              textAlign: TextAlign.end,
              overflow: TextOverflow.ellipsis,
              style: st(c, size: 14.5, w: strong ? FontWeight.w700 : FontWeight.w400, color: color ?? c.pal.title)),
        ),
      ]),
    );

/// Grid of cards that reflows with the window width.
class CardGrid extends StatelessWidget {
  final List<Widget> children;
  final double minWidth;
  final String empty;
  const CardGrid({super.key, required this.children, this.minWidth = 250, this.empty = 'هیچ تۆمارێک نییە'});

  @override
  Widget build(BuildContext context) {
    if (children.isEmpty) return Center(child: hint(context, empty));
    const gap = 12.0;
    return LayoutBuilder(builder: (context, box) {
      final w = box.maxWidth - 12;   // room for the scrollbar
      final cols = ((w + gap) / (minWidth + gap)).floor().clamp(1, 99);
      final cw = (w - gap * (cols - 1)) / cols;
      return Scrollbar(
        child: SingleChildScrollView(
          padding: const EdgeInsetsDirectional.only(end: 12, bottom: 8),
          child: Wrap(
            spacing: gap,
            runSpacing: gap,
            children: [for (final ch in children) SizedBox(width: cw, child: ch)],
          ),
        ),
      );
    });
  }
}

// ---------------------------------------------------------------- لیستی بچووک
class ListCard extends StatelessWidget {
  final String title, empty;
  final List<(String, String, Color)> rows;
  const ListCard(this.title, this.empty, this.rows, {super.key});

  @override
  Widget build(BuildContext context) {
    final c = context.pal;
    return Panel(
      title: title,
      child: rows.isEmpty
          ? Align(alignment: AlignmentDirectional.topStart, child: hint(context, empty))
          : ListView.separated(
              itemCount: rows.length,
              separatorBuilder: (_, _) => Divider(height: 1, color: c.line),
              itemBuilder: (_, i) => Padding(
                padding: const EdgeInsets.symmetric(vertical: 9),
                child: Row(children: [
                  Expanded(child: label(context, rows[i].$1, size: 14.5, lines: 1)),
                  const SizedBox(width: 8),
                  label(context, rows[i].$2, size: 14.5, w: FontWeight.w700, color: rows[i].$3),
                ]),
              ),
            ),
    );
  }
}

// ---------------------------------------------------------------- فلتەر و گەڕان
class Chips extends StatelessWidget {
  final List<String> labels;
  final int value;
  final ValueChanged<int> onChanged;
  const Chips(this.labels, this.value, this.onChanged, {super.key});

  @override
  Widget build(BuildContext context) {
    final c = context.pal;
    return Wrap(spacing: 6, children: [
      for (var i = 0; i < labels.length; i++)
        InkWell(
          borderRadius: BorderRadius.circular(16),
          onTap: () => onChanged(i),
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
            decoration: BoxDecoration(
              color: i == value ? c.soft(c.gold, .14) : Colors.transparent,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: i == value ? c.soft(c.gold, .5) : c.border),
            ),
            child: Text(labels[i],
                style: st(context,
                    size: 14,
                    w: i == value ? FontWeight.w700 : FontWeight.w500,
                    color: i == value ? c.goldHi : c.muted)),
          ),
        ),
    ]);
  }
}

class SearchBox extends StatelessWidget {
  final String hintText;
  final TextEditingController controller;
  final double width;
  const SearchBox(this.hintText, this.controller, {super.key, this.width = 230});

  @override
  Widget build(BuildContext context) => SizedBox(
        width: width,
        child: ValueListenableBuilder(
          valueListenable: controller,
          builder: (context, v, _) => TextField(
            controller: controller,
            style: st(context),
            decoration: InputDecoration(
              hintText: hintText,
              prefixIcon: Icon(Icons.search, size: 19, color: context.pal.faint),
              suffixIcon: v.text.isEmpty
                  ? null
                  : IconButton(icon: const Icon(Icons.close, size: 16), onPressed: controller.clear),
            ),
          ),
        ),
      );
}

// ---------------------------------------------------------------- خانەکان
/// A caption stacked above its input.
Widget field(BuildContext c, String caption, Widget input) => Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [label(c, caption, size: 13.5, color: c.pal.muted), const SizedBox(height: 5), input],
    );

Widget textBox(BuildContext c, TextEditingController ctl,
        {String? hintText, bool ltr = false, bool obscure = false, FocusNode? focus,
        ValueChanged<String>? onSubmitted, ValueChanged<String>? onChanged, bool autofocus = false,
        Widget? prefix}) =>
    TextField(
      controller: ctl,
      focusNode: focus,
      autofocus: autofocus,
      obscureText: obscure,
      textDirection: ltr ? TextDirection.ltr : null,
      style: st(c),
      onSubmitted: onSubmitted,
      onChanged: onChanged,
      decoration: InputDecoration(hintText: hintText, prefixIcon: prefix),
    );

/// Holds a number typed into a [NumBox].
class NumCtrl extends TextEditingController {
  NumCtrl([double v = 0]) : super(text: plain(v));

  double get n => parseNum(text);
  set n(double v) => text = plain(v);

  static String plain(double v) =>
      (v - v.roundToDouble()).abs() < 1e-9 ? fmt(v) : fmt(double.parse(v.toStringAsFixed(2)));
}

class NumBox extends StatelessWidget {
  final NumCtrl ctl;
  final bool enabled;
  final ValueChanged<double>? onChanged;
  final ValueChanged<String>? onSubmitted;
  final FocusNode? focus;
  const NumBox(this.ctl, {super.key, this.enabled = true, this.onChanged, this.onSubmitted, this.focus});

  @override
  Widget build(BuildContext context) => Focus(
        skipTraversal: true,
        onFocusChange: (f) {
          if (!f) ctl.n = ctl.n;   // tidy to 1,234.5 when leaving the box
        },
        child: TextField(
          controller: ctl,
          focusNode: focus,
          enabled: enabled,
          textDirection: TextDirection.ltr,
          textAlign: TextAlign.left,
          style: st(context, color: enabled ? null : context.pal.faint),
          inputFormatters: [FilteringTextInputFormatter.allow(RegExp(r'[0-9٠-٩۰-۹.,٫]'))],
          onChanged: onChanged == null ? null : (_) => onChanged!(ctl.n),
          onSubmitted: onSubmitted,
          onTap: () => ctl.selection = TextSelection(baseOffset: 0, extentOffset: ctl.text.length),
        ),
      );
}

/// Holds the date picked in a [DateBox].
class DateCtrl extends ValueNotifier<DateTime> {
  DateCtrl([DateTime? d]) : super(d ?? DateTime.now());
  String get iso => isoDate(value);
}

class DateBox extends StatelessWidget {
  final DateCtrl ctl;
  const DateBox(this.ctl, {super.key});

  @override
  Widget build(BuildContext context) {
    final c = context.pal;
    return ValueListenableBuilder(
      valueListenable: ctl,
      builder: (context, d, _) => InkWell(
        borderRadius: BorderRadius.circular(9),
        onTap: () async {
          final picked = await showDatePicker(
              context: context, initialDate: d, firstDate: DateTime(2000), lastDate: DateTime(2100));
          if (picked != null) ctl.value = picked;
        },
        child: InputDecorator(
          decoration: const InputDecoration(),
          child: Row(children: [
            Icon(Icons.calendar_today_outlined, size: 17, color: c.muted),
            const SizedBox(width: 10),
            Text(isoDate(d), textDirection: TextDirection.ltr, style: st(context)),
          ]),
        ),
      ),
    );
  }
}

/// A dropdown that also accepts typing, with matches anywhere in the name.
class PickBox<T> extends StatefulWidget {
  final List<(String, T)> options;
  final TextEditingController ctl;
  final FocusNode? focus;
  final String? hintText;
  final ValueChanged<String>? onSubmitted;
  final ValueChanged<String>? onChanged;
  final Widget? prefix;
  const PickBox(this.options, this.ctl, {super.key, this.focus, this.hintText, this.onSubmitted, this.onChanged, this.prefix});

  /// The value of the option whose text is shown, or null when typed text matches none.
  static T? valueOf<T>(List<(String, T)> options, TextEditingController ctl) {
    for (final o in options) {
      if (o.$1 == ctl.text.trim()) return o.$2;
    }
    return null;
  }

  @override
  State<PickBox<T>> createState() => _PickBoxState<T>();
}

class _PickBoxState<T> extends State<PickBox<T>> {
  late final FocusNode _own = FocusNode();
  FocusNode get node => widget.focus ?? _own;

  @override
  void dispose() {
    _own.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final c = context.pal;
    final options = widget.options, onChanged = widget.onChanged, onSubmitted = widget.onSubmitted;
    return RawAutocomplete<String>(
      textEditingController: widget.ctl,
      focusNode: node,
      optionsBuilder: (v) {
        final t = v.text.trim();
        final all = options.map((o) => o.$1);
        if (t.isEmpty || all.contains(t)) return all;
        return all.where((o) => o.contains(t));
      },
      onSelected: (v) => onChanged?.call(v),
      fieldViewBuilder: (context, controller, node, submit) => TextField(
        controller: controller,
        focusNode: node,
        style: st(context),
        onChanged: onChanged,
        onSubmitted: (v) {
          submit();
          onSubmitted?.call(v);
        },
        decoration: InputDecoration(
          hintText: widget.hintText,
          prefixIcon: widget.prefix,
          suffixIcon: Icon(Icons.expand_more, size: 20, color: c.muted),
        ),
      ),
      optionsViewBuilder: (context, select, opts) => Align(
        alignment: AlignmentDirectional.topStart,
        child: Material(
          color: c.card,
          elevation: 6,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10), side: BorderSide(color: c.borderHi)),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxHeight: 320, maxWidth: 380),
            child: ListView(
              padding: const EdgeInsets.all(5),
              shrinkWrap: true,
              children: [
                for (final o in opts)
                  InkWell(
                    borderRadius: BorderRadius.circular(7),
                    onTap: () => select(o),
                    child: Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 9),
                      child: Text(o, style: st(context)),
                    ),
                  ),
              ],
            ),
          ),
        ),
      ),
    );
  }

}

// ---------------------------------------------------------------- خشتە
class Col {
  final String title;
  final int flex;
  final bool grow;
  const Col(this.title, {this.flex = 1, this.grow = false});
}

/// A selectable table. [colors] picks a colour per (row, column) or null.
class Grid extends StatelessWidget {
  final List<Col> cols;
  final List<List<String>> rows;
  final int? selected;
  final ValueChanged<int>? onSelect;
  final Color? Function(int row, int col)? colors;
  final bool flat;
  final String empty;
  const Grid(this.cols, this.rows,
      {super.key, this.selected, this.onSelect, this.colors, this.flat = false, this.empty = ''});

  @override
  Widget build(BuildContext context) {
    final c = context.pal;
    Widget cell(String t, int ci, {bool head = false, Color? color}) => Expanded(
          flex: cols[ci].flex,
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 8),
            child: Text(t,
                textAlign: TextAlign.center,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: head
                    ? st(context, size: 13, w: FontWeight.w700, color: c.faint)
                    : st(context, size: 14.5, color: color)),
          ),
        );
    final body = Column(children: [
      Container(
        height: 42,
        decoration: BoxDecoration(border: Border(bottom: BorderSide(color: c.border))),
        child: Row(children: [for (var i = 0; i < cols.length; i++) cell(cols[i].title, i, head: true)]),
      ),
      Expanded(
        child: rows.isEmpty
            ? Center(child: hint(context, empty))
            : Scrollbar(
                child: ListView.builder(
                  itemCount: rows.length,
                  itemExtent: 42,
                  itemBuilder: (_, r) => InkWell(
                    onTap: onSelect == null ? null : () => onSelect!(r),
                    child: Container(
                      decoration: BoxDecoration(
                        color: r == selected ? c.soft(c.gold, .14) : null,
                        border: Border(bottom: BorderSide(color: c.line)),
                      ),
                      child: Row(children: [
                        for (var i = 0; i < cols.length; i++)
                          cell(i < rows[r].length ? rows[r][i] : '', i, color: colors?.call(r, i)),
                      ]),
                    ),
                  ),
                ),
              ),
      ),
    ]);
    if (flat) return body;
    return Container(
      clipBehavior: Clip.antiAlias,
      decoration: BoxDecoration(color: c.card, borderRadius: BorderRadius.circular(12), border: Border.all(color: c.border)),
      child: body,
    );
  }
}

// ---------------------------------------------------------------- چارت
class BarChart extends StatefulWidget {
  /// (axis label, value, tooltip)
  final List<(String, double, String)> data;
  const BarChart(this.data, {super.key});

  @override
  State<BarChart> createState() => _BarChartState();
}

class _BarChartState extends State<BarChart> {
  int hover = -1;

  @override
  Widget build(BuildContext context) {
    final c = context.pal;
    return LayoutBuilder(builder: (context, box) {
      final n = widget.data.length;
      int at(double x) {
        if (n == 0) return -1;
        final i = ((x - 8) / ((box.maxWidth - 16) / n)).floor();
        return i >= 0 && i < n ? i : -1;
      }

      return Directionality(
        textDirection: TextDirection.ltr,   // time runs left to right
        child: MouseRegion(
          onHover: (e) => setState(() => hover = at(e.localPosition.dx)),
          onExit: (_) => setState(() => hover = -1),
          child: Tooltip(
            message: hover >= 0 ? widget.data[hover].$3 : '',
            child: CustomPaint(
              size: Size(box.maxWidth, box.maxHeight),
              painter: _BarPainter(widget.data, hover, c, st(context, size: 11, color: c.faint)),
            ),
          ),
        ),
      );
    });
  }
}

class _BarPainter extends CustomPainter {
  final List<(String, double, String)> data;
  final int hover;
  final Palette c;
  final TextStyle axis;
  _BarPainter(this.data, this.hover, this.c, this.axis);

  @override
  void paint(Canvas canvas, Size size) {
    final r = Rect.fromLTWH(8, 12, size.width - 16, size.height - 12 - 26);
    final grid = Paint()..color = c.line..strokeWidth = 1;
    for (var k = 0; k < 4; k++) {
      final y = r.bottom - (r.height - 6) * k / 3;
      canvas.drawLine(Offset(r.left, y), Offset(r.right, y), grid);
    }
    final top = data.fold<double>(0, (m, d) => d.$2 > m ? d.$2 : m);
    if (top <= 0) {
      final tp = TextPainter(
          text: TextSpan(text: 'هێشتا هیچ فرۆشتنێک نییە', style: axis.copyWith(fontSize: 13)),
          textDirection: TextDirection.rtl)
        ..layout();
      tp.paint(canvas, size.center(Offset.zero) - Offset(tp.width / 2, tp.height / 2));
      return;
    }
    final n = data.length, slot = r.width / n;
    final bw = (slot * .62).clamp(3.0, 34.0);
    final step = (n / 12).ceil().clamp(1, 99);
    for (var i = 0; i < n; i++) {
      final h = data[i].$2 / top * (r.height - 6);
      final x = r.left + slot * i + (slot - bw) / 2;
      final paint = Paint()..color = i == hover || !c.dark ? c.gold : c.soft(c.gold, .78);
      if (h >= 1) {
        canvas.drawRRect(
            RRect.fromRectAndRadius(Rect.fromLTWH(x, r.bottom - h, bw, h), Radius.circular(bw / 2 < 4 ? bw / 2 : 4)),
            paint);
      }
      if (i % step == 0) {
        final tp = TextPainter(text: TextSpan(text: data[i].$1, style: axis), textDirection: TextDirection.ltr)..layout();
        tp.paint(canvas, Offset(x + bw / 2 - tp.width / 2, r.bottom + 7));
      }
    }
  }

  @override
  bool shouldRepaint(_BarPainter old) => old.data != data || old.hover != hover || old.c != c;
}

// ---------------------------------------------------------------- دیالۆگ
Future<bool> confirm(BuildContext context, String text) async =>
    await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('دڵنیابوونەوە'),
        content: Text(text),
        actions: [
          Btn('نەخێر', () => Navigator.pop(ctx, false)),
          Btn.primary('بەڵێ', () => Navigator.pop(ctx, true)),
        ],
      ),
    ) ??
    false;

Future<void> info(BuildContext context, String text, {String title = 'ئاگاداری'}) => showDialog<void>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(title),
        content: Text(text),
        actions: [Btn.primary('باشە', () => Navigator.pop(ctx))],
      ),
    );

/// A form dialog. [onSave] returns the result to close with, or null to stay open
/// (after showing its own message).
Future<T?> formDialog<T>(BuildContext context, String title,
    {required List<Widget> Function(BuildContext, StateSetter) body,
    required T? Function(BuildContext) onSave,
    String saveText = 'پاشەکەوتکردن',
    double width = 460,
    bool Function()? canSave}) {
  return showDialog<T>(
    context: context,
    builder: (ctx) => StatefulBuilder(
      builder: (ctx, setState) => AlertDialog(
        title: Text(title),
        content: SizedBox(
          width: width,
          child: SingleChildScrollView(
            child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, mainAxisSize: MainAxisSize.min, children: [
              for (final w in body(ctx, setState)) Padding(padding: const EdgeInsets.only(bottom: 12), child: w),
            ]),
          ),
        ),
        actions: [
          Btn('پاشگەزبوونەوە', () => Navigator.pop(ctx)),
          Btn.primary(saveText, canSave == null || canSave() ? () {
            final r = onSave(ctx);
            if (r != null) Navigator.pop(ctx, r);
          } : null),
        ],
      ),
    ),
  );
}

/// One labelled row inside a form dialog: caption on the right, input on the left.
Widget formRow(BuildContext c, String caption, Widget input, {double captionWidth = 130}) => Row(children: [
      SizedBox(width: captionWidth, child: label(c, caption, size: 14, color: c.pal.muted)),
      Expanded(child: input),
    ]);
