// سیستەمی حیساباتی دووکانی جوملە — Flutter.
//
//   lib/core/    داتابەیس، ڕێکخستن، ژمارە و بارکۆد
//   lib/ui/      ڕەنگ، پارچە هاوبەشەکان، نەخشاندنی بارکۆد
//   lib/print/   پسووڵە، کەشف حساب، ڕاپۆرت و لەیبڵ (PDF و چاپ)
//   lib/pages/   هەشت بەشەکەی بەرنامەکە
import 'dart:io';
import 'dart:ui';

import 'package:flutter/services.dart';
import 'package:material_ui/material_ui.dart';

import 'core/config.dart';
import 'core/db.dart';
import 'core/fmt.dart';
import 'pages/dashboard.dart';
import 'pages/expenses.dart';
import 'pages/inventory.dart';
import 'pages/people.dart';
import 'pages/reports.dart';
import 'pages/sales.dart';
import 'pages/settings.dart';
import 'pages/suppliers.dart';
import 'ui/locale.dart';
import 'ui/theme.dart';
import 'ui/widgets.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  Object? error;
  try {
    openDb();
  } catch (e) {
    error = e;
  }
  runApp(ShopApp(error: error));
}

final themeName = ValueNotifier<String>('dark');

class ShopApp extends StatefulWidget {
  final Object? error;
  const ShopApp({super.key, this.error});
  @override
  State<ShopApp> createState() => _ShopAppState();
}

enum Stage { locked, firstRun, ready }

class _ShopAppState extends State<ShopApp> {
  late Stage stage;
  late final AppLifecycleListener _life;

  @override
  void initState() {
    super.initState();
    if (widget.error == null) {
      themeName.value = db.get('theme', 'dark');
      stage = db.get('pin').isNotEmpty ? Stage.locked : (db.get('company').isEmpty ? Stage.firstRun : Stage.ready);
    }
    _life = AppLifecycleListener(onExitRequested: _onExit);
  }

  @override
  void dispose() {
    _life.dispose();
    super.dispose();
  }

  /// One copy a day into the backup folder when the window is closed.
  Future<AppExitResponse> _onExit() async {
    try {
      final d = db.get('backup');
      if (d.isNotEmpty && Directory(d).existsSync()) db.backupTo(d, daily: true);
    } catch (_) {}
    return AppExitResponse.exit;
  }

  void next() => setState(() {
        stage = db.get('company').isEmpty ? Stage.firstRun : Stage.ready;
      });

  @override
  Widget build(BuildContext context) => ValueListenableBuilder(
        valueListenable: themeName,
        builder: (context, t, _) => MaterialApp(
          title: appTitle,
          debugShowCheckedModeBanner: false,
          scaffoldMessengerKey: messengerKey,
          theme: buildTheme(t == 'light' ? Palette.lightP : Palette.darkP),
          locale: const Locale('ckb'),
          supportedLocales: const [Locale('ckb')],
          localizationsDelegates: kuDelegates,
          home: Scaffold(
            body: widget.error != null
                ? Center(child: Padding(
                    padding: const EdgeInsets.all(40),
                    child: SelectableText('نەتوانرا داتابەیس بکرێتەوە:\n$dbPath\n\n${widget.error}'),
                  ))
                : switch (stage) {
                    Stage.locked => LockScreen(onOpen: next),
                    Stage.firstRun => FirstRun(onDone: next),
                    Stage.ready => const Shell(),
                  },
          ),
        ),
      );
}

// ---------------------------------------------------------------- قفڵ و یەکەم جار
class _Gate extends StatelessWidget {
  final List<Widget> children;
  const _Gate(this.children);
  @override
  Widget build(BuildContext context) => Center(
        child: SizedBox(
          width: 440,
          child: Panel(
            padding: const EdgeInsets.fromLTRB(28, 26, 28, 24),
            child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: children),
          ),
        ),
      );
}

class LockScreen extends StatefulWidget {
  final VoidCallback onOpen;
  const LockScreen({super.key, required this.onOpen});
  @override
  State<LockScreen> createState() => _LockScreenState();
}

class _LockScreenState extends State<LockScreen> {
  final pin = TextEditingController();
  bool wrong = false;

  void tryOpen() {
    if (pinHash(pin.text) == db.get('pin')) {
      widget.onOpen();
    } else {
      setState(() => wrong = true);
      pin.clear();
    }
  }

  @override
  Widget build(BuildContext context) => _Gate([
        Icon(Icons.lock_outline, size: 34, color: context.pal.gold),
        const SizedBox(height: 10),
        label(context, db.get('company').isEmpty ? appTitle : db.get('company'),
            size: 20, w: FontWeight.w700, color: context.pal.title, align: TextAlign.center),
        const SizedBox(height: 4),
        hint(context, 'بەرنامەکە قفڵ کراوە. ژمارەی نهێنی بنووسە.'),
        const SizedBox(height: 16),
        textBox(context, pin, obscure: true, ltr: true, autofocus: true, onSubmitted: (_) => tryOpen()),
        if (wrong) ...[const SizedBox(height: 6), label(context, 'ژمارەی نهێنی هەڵەیە', color: context.pal.red)],
        const SizedBox(height: 14),
        SizedBox(height: 44, child: Btn.primary('کردنەوە', tryOpen, icon: Icons.lock_open_outlined)),
      ]);
}

class FirstRun extends StatefulWidget {
  final VoidCallback onDone;
  const FirstRun({super.key, required this.onDone});
  @override
  State<FirstRun> createState() => _FirstRunState();
}

class _FirstRunState extends State<FirstRun> {
  final name = TextEditingController(), phone = TextEditingController(), address = TextEditingController();

  void done() {
    if (name.text.trim().isEmpty) return;
    db.set('company', name.text.trim());
    db.set('phone', phone.text.trim());
    db.set('address', address.text.trim());
    widget.onDone();
  }

  @override
  Widget build(BuildContext context) => _Gate([
        label(context, 'بەخێربێیت — ناوی دووکانەکەت بنووسە', size: 20, w: FontWeight.w700, color: context.pal.title),
        const SizedBox(height: 6),
        hint(context, 'ئەم ناوە لە سەرەوەی بەرنامەکە و لەسەر پسووڵەکان دەردەکەوێت. دواتر دەتوانیت لە ڕێکخستن بیگۆڕیت.'),
        const SizedBox(height: 18),
        formRow(context, 'ناوی دووکان', textBox(context, name, hintText: 'پێویستە', autofocus: true,
            onChanged: (_) => setState(() {}), onSubmitted: (_) => done()), captionWidth: 100),
        const SizedBox(height: 10),
        formRow(context, 'مۆبایل', textBox(context, phone, ltr: true), captionWidth: 100),
        const SizedBox(height: 10),
        formRow(context, 'ناونیشان', textBox(context, address), captionWidth: 100),
        const SizedBox(height: 18),
        SizedBox(height: 44, child: Btn.primary('دەستپێکردن', name.text.trim().isEmpty ? null : done)),
      ]);
}

// ---------------------------------------------------------------- پەنجەرەی سەرەکی
class PageInfo {
  final String title, sub;
  final IconData icon;
  const PageInfo(this.title, this.sub, this.icon);
}

const pages = [
  PageInfo('داشبۆرد', 'پوختەی دووکانەکە لە یەک ڕوانیندا', Icons.space_dashboard_outlined),
  PageInfo('فرۆشتن', 'دەرکردنی پسووڵە و بەڕێوەبردنی فرۆشتن', Icons.receipt_long_outlined),
  PageInfo('کڕیاران', 'قەرز، وەرگرتنی پارە و کەشف حساب', Icons.people_alt_outlined),
  PageInfo('مەخزەن', 'کاڵاکان، بارکۆد، کڕین و ئاگاداری کەمبوون', Icons.inventory_2_outlined),
  PageInfo('دابینکەران', 'قەرزی دابینکەران و مێژووی کڕین', Icons.local_shipping_outlined),
  PageInfo('مەسروفات و مووچە', 'خەرجییەکان و کارمەندان', Icons.account_balance_wallet_outlined),
  PageInfo('ڕاپۆرت', 'قازانج، فرۆشتن و هەناردەکردن', Icons.bar_chart_rounded),
  PageInfo('ڕێکخستن', 'زانیاری دووکان، پاراستن و باکئەپ', Icons.tune),
];

class Shell extends StatefulWidget {
  const Shell({super.key});
  @override
  State<Shell> createState() => ShellState();
}

class ShellState extends State<Shell> {
  int index = 0;
  final salesKey = GlobalKey<SalesPageState>();

  void go(int i) => setState(() => index = i);

  void newInvoice() {
    setState(() {
      index = 1;
      draft.tab = 0;
    });
    WidgetsBinding.instance.addPostFrameCallback((_) => salesKey.currentState?.focusScan());
  }

  void toggleTheme() {
    final t = themeName.value == 'dark' ? 'light' : 'dark';
    db.set('theme', t);
    themeName.value = t;
  }

  Widget _page() => switch (index) {
        0 => const DashboardPage(),
        1 => SalesPage(key: salesKey),
        2 => const CustomersPage(),
        3 => const InventoryPage(),
        4 => const SuppliersPage(),
        5 => const ExpensesPage(),
        6 => const ReportsPage(),
        _ => const SettingsPage(),
      };

  @override
  Widget build(BuildContext context) {
    final c = context.pal;
    return CallbackShortcuts(
      bindings: {
        const SingleActivator(LogicalKeyboardKey.keyN, control: true): newInvoice,
        const SingleActivator(LogicalKeyboardKey.f2): newInvoice,
        const SingleActivator(LogicalKeyboardKey.f5): appState.changed,
        for (var i = 0; i < pages.length; i++)
          SingleActivator(LogicalKeyboardKey(LogicalKeyboardKey.digit1.keyId + i), control: true): () => go(i),
      },
      child: Focus(
        autofocus: true,
        child: Row(children: [
          _sidebar(context),
          Expanded(
            child: Column(children: [
              _header(context),
              Expanded(
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(24, 18, 24, 22),
                  child: ListenableBuilder(
                    listenable: appState,
                    builder: (context, _) => KeyedSubtree(key: ValueKey(index), child: _page()),
                  ),
                ),
              ),
            ]),
          ),
        ]),
      ),
    ).withBackground(c.bg);
  }

  Widget _sidebar(BuildContext context) {
    final c = context.pal;
    final name = db.get('company').isEmpty ? 'دووکان' : db.get('company');
    return Container(
      width: 236,
      decoration: BoxDecoration(color: c.side, border: BorderDirectional(end: BorderSide(color: c.line))),
      padding: const EdgeInsets.fromLTRB(14, 20, 14, 16),
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        Row(children: [
          Container(
            width: 42,
            height: 42,
            alignment: Alignment.center,
            decoration: BoxDecoration(color: c.gold, borderRadius: BorderRadius.circular(12)),
            child: label(context, name.trim().characters.first, size: 22, w: FontWeight.w800, color: c.onGold),
          ),
          const SizedBox(width: 11),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              label(context, name, size: 16, w: FontWeight.w700, color: c.title, lines: 2),
              label(context, 'دووکانی جوملە', size: 13, color: c.faint),
            ]),
          ),
        ]),
        const SizedBox(height: 22),
        for (var i = 0; i < pages.length; i++) ...[
          _navItem(context, i),
          if (i == 1 || i == 4 || i == 6) const SizedBox(height: 10),   // sell / stock / money groups
        ],
        const Spacer(),
        TextButton.icon(
          onPressed: toggleTheme,
          icon: Icon(c.dark ? Icons.light_mode_outlined : Icons.dark_mode_outlined, size: 19),
          label: Text(c.dark ? 'دۆخی ڕووناک' : 'دۆخی تاریک'),
        ),
        const SizedBox(height: 6),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 6),
          child: label(context, 'وەشانی $appVersion', size: 12.5, color: c.faint),
        ),
      ]),
    );
  }

  Widget _navItem(BuildContext context, int i) {
    final c = context.pal;
    final on = i == index;
    return Tooltip(
      message: 'Ctrl+${i + 1}',
      waitDuration: const Duration(seconds: 1),
      child: InkWell(
        borderRadius: BorderRadius.circular(10),
        onTap: () => go(i),
        hoverColor: c.btn,
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 11),
          decoration: BoxDecoration(color: on ? c.soft(c.gold, .14) : null, borderRadius: BorderRadius.circular(10)),
          child: Row(children: [
            Icon(pages[i].icon, size: 20, color: on ? c.goldHi : c.muted),
            const SizedBox(width: 12),
            label(context, pages[i].title, size: 15, w: on ? FontWeight.w700 : FontWeight.w500, color: on ? c.goldHi : c.muted),
          ]),
        ),
      ),
    );
  }

  Widget _header(BuildContext context) {
    final c = context.pal;
    final rate = double.tryParse(db.get('usd')) ?? 0;
    Widget tag(String t) => Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
          decoration: BoxDecoration(color: c.card, borderRadius: BorderRadius.circular(9), border: Border.all(color: c.border)),
          child: Text(t, textDirection: TextDirection.ltr, style: st(context, size: 13.5, color: c.muted)),
        );
    return Container(
      height: 72,
      padding: const EdgeInsets.symmetric(horizontal: 24),
      decoration: BoxDecoration(border: Border(bottom: BorderSide(color: c.line))),
      child: Row(children: [
        Column(mainAxisAlignment: MainAxisAlignment.center, crossAxisAlignment: CrossAxisAlignment.start, children: [
          label(context, pages[index].title, size: 22, w: FontWeight.w700, color: c.title),
          label(context, pages[index].sub, size: 14, color: c.muted),
        ]),
        const Spacer(),
        if (rate > 0) ...[tag('\$1 = ${fmt(rate)} ${db.get('currency')}'), const SizedBox(width: 8)],
        tag(today()),
        const SizedBox(width: 12),
        Tooltip(message: 'Ctrl+N  /  F2', child: Btn.primary('پسووڵەی نوێ', newInvoice, icon: Icons.add)),
      ]),
    );
  }
}

extension on Widget {
  Widget withBackground(Color c) => ColoredBox(color: c, child: this);
}

