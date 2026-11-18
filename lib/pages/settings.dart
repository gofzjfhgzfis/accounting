// ڕێکخستن: زانیاری دووکان، قفڵ، باکئەپ و شوێنی داتابەیس.
import 'dart:io';

import 'package:file_selector/file_selector.dart';
import 'package:material_ui/material_ui.dart';
import 'package:path/path.dart' as p;

import '../core/config.dart';
import '../core/db.dart';
import '../core/fmt.dart';
import '../ui/theme.dart';
import '../ui/widgets.dart';

class SettingsPage extends StatefulWidget {
  const SettingsPage({super.key});
  @override
  State<SettingsPage> createState() => _SettingsPageState();
}

class _SettingsPageState extends State<SettingsPage> {
  final company = TextEditingController(text: db.get('company')),
      phone = TextEditingController(text: db.get('phone')),
      address = TextEditingController(text: db.get('address')),
      currency = TextEditingController(text: db.get('currency'));
  final rate = NumCtrl(double.tryParse(db.get('usd')) ?? 0);

  void save() {
    if (company.text.trim().isEmpty) {
      info(context, 'ناوی دووکان پێویستە');
      return;
    }
    db.set('company', company.text.trim());
    db.set('phone', phone.text.trim());
    db.set('address', address.text.trim());
    db.set('currency', currency.text.trim());
    db.set('usd', rate.n);
    db.log('settings', 'edit', 'زانیاری دووکان پاشەکەوتکرا — ${company.text.trim()}، نرخی دۆلار ${fmt(rate.n)}');
    appState.changed();
    toast('پاشەکەوتکرا');
  }

  // ---- قفڵ ----
  Future<String?> askPin(String title, {bool twice = false}) {
    final a = TextEditingController(), b = TextEditingController();
    return formDialog<String>(
      context,
      title,
      width: 360,
      saveText: 'باشە',
      body: (c, _) => [
        formRow(c, 'ژمارەی نهێنی', textBox(c, a, obscure: true, ltr: true, autofocus: true), captionWidth: 110),
        if (twice) formRow(c, 'دووبارە', textBox(c, b, obscure: true, ltr: true), captionWidth: 110),
      ],
      onSave: (c) {
        if (twice && a.text != b.text) {
          info(c, 'دوو ژمارەکە وەک یەک نین');
          return null;
        }
        return a.text;
      },
    );
  }

  Future<void> setPin() async {
    if (db.get('pin').isNotEmpty) {
      final old = await askPin('ژمارەی نهێنی ئێستا');
      if (old == null) return;
      if (pinHash(old) != db.get('pin')) return mounted ? info(context, 'ژمارەی نهێنی هەڵەیە') : null;
    }
    final n = await askPin('ژمارەی نهێنی نوێ', twice: true);
    if (n == null) return;
    if (n.length < 4) return mounted ? info(context, 'لانیکەم ٤ پیت یان ژمارە بنووسە') : null;
    db.set('pin', pinHash(n));
    db.log('settings', 'edit', 'ژمارەی نهێنی دانرا یان گۆڕدرا');
    setState(() {});
    toast('قفڵ چالاککرا');
  }

  Future<void> removePin() async {
    final old = await askPin('ژمارەی نهێنی ئێستا');
    if (old == null) return;
    if (pinHash(old) != db.get('pin')) return mounted ? info(context, 'ژمارەی نهێنی هەڵەیە') : null;
    db.set('pin', '');
    db.log('settings', 'delete', 'قفڵی ژمارەی نهێنی لابرا');
    setState(() {});
    toast('قفڵ لابرا');
  }

  // ---- باکئەپ و داتابەیس ----
  Future<void> pickBackup() async {
    final d = await getDirectoryPath(confirmButtonText: 'هەڵبژاردن');
    if (d == null) return;
    db.set('backup', d);
    db.log('settings', 'edit', 'فۆڵدەری باکئەپ — $d');
    setState(() {});
  }

  void backupNow() {
    final d = db.get('backup');
    if (d.isEmpty || !Directory(d).existsSync()) {
      info(context, 'سەرەتا فۆڵدەری باکئەپ دیاری بکە');
      return;
    }
    try {
      final name = db.backupTo(d);
      db.log('backup', 'add', 'باکئەپ — $name');
      toast('باکئەپ درووستکرا: $name');
    } catch (e) {
      info(context, 'باکئەپ سەرکەوتوو نەبوو:\n$e');
    }
  }

  Future<void> restore() async {
    final f = await openFile(
      initialDirectory: db.get('backup').isEmpty ? appDir : db.get('backup'),
      acceptedTypeGroups: const [XTypeGroup(label: 'DB', extensions: ['db'])],
    );
    if (f == null || !mounted) return;
    if (!await confirm(context, 'هەموو داتای ئێستا دەگۆڕدرێت بە باکئەپەکە. دڵنیایت؟')) return;
    // keep what is being replaced, in case the wrong file was picked
    final safety = p.join(appDir, 'before_restore.db');
    try {
      if (File(safety).existsSync()) File(safety).deleteSync();
      db.con.execute('VACUUM INTO ?', [safety]);
      db.close();
      File(f.path).copySync(dbPath);
      openDb();
      db.log('backup', 'edit', 'داتا لە باکئەپ گەڕێندرایەوە — ${p.basename(f.path)} (داتای پێشوو: before_restore.db)');
    } catch (e) {
      openDb();
      if (mounted) info(context, 'گەڕاندنەوە سەرکەوتوو نەبوو:\n$e');
      return;
    }
    appState.changed();
    if (mounted) info(context, 'داتاکان گەڕێندرانەوە.\nداتای پێشوو لێرە هەڵگیرا:\n$safety');
  }

  Future<void> moveDb() async {
    final folder = await getDirectoryPath(confirmButtonText: 'هەڵبژاردن');
    if (folder == null || !mounted) return;
    final target = p.join(folder, 'oil_shop.db');
    if (p.equals(target, dbPath)) return info(context, 'هەمان شوێنە');
    if (File(target).existsSync()) {
      if (!await confirm(context, 'لەم فۆڵدەرەدا داتابەیسێک هەیە.\nبەکاری بهێنم؟ (داتای ئێستات لە شوێنی کۆنی خۆی دەمێنێتەوە)')) {
        return;
      }
    } else {
      try {
        db.con.execute('VACUUM INTO ?', [target]);
      } catch (e) {
        if (mounted) info(context, 'نەتوانرا کۆپی بکرێت:\n$e');
        return;
      }
    }
    db.close();
    saveCfg({'db_path': target});
    openDb();
    db.log('settings', 'edit', 'شوێنی داتابەیس گۆڕدرا — $target');
    appState.changed();
    toast('شوێنی داتابەیس گۆڕدرا');
  }

  @override
  Widget build(BuildContext context) {
    final c = context.pal;
    final locked = db.get('pin').isNotEmpty;
    final backup = db.get('backup');

    final shop = Panel(
      title: 'زانیاری دووکان',
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        formRow(context, 'ناوی دووکان', textBox(context, company), captionWidth: 110),
        const SizedBox(height: 10),
        formRow(context, 'مۆبایل', textBox(context, phone, ltr: true), captionWidth: 110),
        const SizedBox(height: 10),
        formRow(context, 'ناونیشان', textBox(context, address), captionWidth: 110),
        const SizedBox(height: 10),
        formRow(context, 'دراو', textBox(context, currency), captionWidth: 110),
        const SizedBox(height: 10),
        formRow(context, 'نرخی ١ دۆلار', NumBox(rate), captionWidth: 110),
        const SizedBox(height: 12),
        hint(context, 'ئەم زانیارییانە لەسەر پسووڵە و ڕاپۆرتە چاپکراوەکان دەردەکەون. '
            'نرخی دۆلار بۆ پیشاندانی بەهای نزیکەیی بە دۆلار بەکاردێت.'),
        const Spacer(),
        Btn.primary('پاشەکەوتکردن', save),
      ]),
    );

    final lock = Panel(
      title: 'پاراستن',
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        label(context, locked
            ? 'قفڵ چالاکە — لە کاتی کردنەوەی بەرنامەکە ژمارەی نهێنی دەپرسرێت.'
            : 'قفڵ ناچالاکە — هەر کەسێک دەتوانێت بەرنامەکە بکاتەوە.', color: c.muted),
        const SizedBox(height: 14),
        Wrap(spacing: 8, children: [
          Btn(locked ? 'گۆڕینی ژمارەی نهێنی' : 'دانانی ژمارەی نهێنی', setPin, icon: Icons.lock_outline),
          if (locked) Btn.danger('لابردنی قفڵ', removePin),
        ]),
      ]),
    );

    final bk = Panel(
      title: 'باکئەپ',
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        label(context, backup.isEmpty ? 'هێشتا فۆڵدەری باکئەپ دیاری نەکراوە.' : 'فۆڵدەری ئێستا:  $backup',
            color: backup.isEmpty ? c.muted : c.goldHi, w: FontWeight.w600),
        const SizedBox(height: 8),
        hint(context, 'فۆڵدەرێکی هاوبەش یان فۆڵدەری کلاودی سەر کۆمپیوتەرەکەت هەڵبژێرە. هەر جارێک '
            'بەرنامەکە دادەخرێت کۆپییەک دەنێردرێت و ٢٠ دانەی دوایی هەڵدەگیرێن.'),
        const SizedBox(height: 14),
        Wrap(spacing: 8, runSpacing: 8, children: [
          Btn('هەڵبژاردنی فۆڵدەر', pickBackup),
          Btn.primary('باکئەپی ئێستا', backupNow),
          Btn.danger('گەڕاندنەوە', restore),
        ]),
      ]),
    );

    final loc = Panel(
      title: 'شوێنی داتابەیس',
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        SelectableText(dbPath, style: st(context, color: c.muted), textDirection: TextDirection.ltr),
        const SizedBox(height: 8),
        hint(context, 'ئەگەر دەتەوێت چەند کۆمپیوتەرێکی دووکان هەمان داتا بەکاربهێنن، '
            'لە هەموویان هەمان فۆڵدەری هاوبەش دیاری بکە.'),
        const SizedBox(height: 14),
        Wrap(spacing: 8, children: [
          Btn('گۆڕینی شوێن', moveDb),
          Btn.ghost('کردنەوەی فۆڵدەر', () => Process.run('explorer', [p.dirname(dbPath)])),
        ]),
      ]),
    );

    return Align(
      alignment: Alignment.topCenter,
      child: SizedBox(
        height: 540,
        child: Row(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Expanded(child: shop),
          const SizedBox(width: 12),
          Expanded(
            flex: 2,
            child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              Expanded(child: Row(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                Expanded(child: lock),
                const SizedBox(width: 12),
                Expanded(child: bk),
              ])),
              const SizedBox(height: 12),
              Expanded(child: loc),
            ]),
          ),
        ]),
      ),
    );
  }
}
