// تاقیکردنەوەی تەواوی بەرنامەکە لەسەر ویندۆز:
//   flutter test integration_test -d windows
// بە OILSHOP_HOME فۆڵدەرێکی تاقیکردنەوە دیاری بکە، و SHOTS بۆ وێنەکان.
import 'dart:io';
import 'dart:ui' as ui;

import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:material_ui/material_ui.dart';
import 'package:oil_shop/core/db.dart';
import 'package:oil_shop/core/fmt.dart';
import 'package:oil_shop/main.dart' as app;
import 'package:oil_shop/pages/reports.dart';
import 'package:oil_shop/pages/sales.dart';
import 'package:oil_shop/print/docs.dart';
import 'package:oil_shop/print/render.dart';
import 'package:oil_shop/ui/barcode_view.dart';

final out = Platform.environment['SHOTS'] ?? 'build/shots';

Future<void> shot(WidgetTester t, String name) async {
  await t.pumpAndSettle();
  await t.runAsync(() async {
    final rv = t.binding.renderViews.first;
    // the root layer is in physical pixels
    final img = await (rv.debugLayer! as OffsetLayer).toImage(Offset.zero & rv.flutterView.physicalSize, pixelRatio: 1);
    final bytes = await img.toByteData(format: ui.ImageByteFormat.png);
    File('$out/$name.png').writeAsBytesSync(bytes!.buffer.asUint8List());
  });
}

Future<void> nav(WidgetTester t, String title) async {
  await t.tap(find.descendant(of: find.byType(InkWell), matching: find.text(title)).first);
  await t.pumpAndSettle();
}

Future<void> press(WidgetTester t, String text) async {
  await t.tap(find.text(text).last);
  await t.pumpAndSettle();
}

Finder fieldWithHint(String h) =>
    find.byWidgetPredicate((w) => w is TextField && w.decoration?.hintText == h);

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();
  Directory(out).createSync(recursive: true);

  testWidgets('whole app', (t) async {
    app.main();
    await t.pumpAndSettle(const Duration(seconds: 1));

    // ---- migration from the Python version ----
    expect(db.q('PRAGMA table_info(items)').any((r) => r['name'] == 'barcode'), isTrue);
    final item = db.q('SELECT * FROM items ORDER BY id').first;
    db.x("UPDATE items SET barcode='212345678901' WHERE id=?", [item['id']]);
    await shot(t, 'dark_dash');

    // ---- sales: scan twice, unknown code, then pick by name ----
    await t.sendKeyEvent(LogicalKeyboardKey.f2);
    await t.pumpAndSettle();
    final scan = fieldWithHint('سکانی بارکۆد بکە…  (F2)');
    expect(scan, findsOneWidget);
    for (final code in ['٢١٢٣٤٥٦٧٨٩٠١', '212345678901']) {   // Kurdish digits too
      await t.enterText(scan, code);
      await t.testTextInput.receiveAction(TextInputAction.done);
      await t.pumpAndSettle();
    }
    expect(draft.lines.single.qty, 2);
    await t.enterText(scan, '999');
    await t.testTextInput.receiveAction(TextInputAction.done);
    await t.pumpAndSettle();
    expect(find.textContaining('لە مەخزەندا نییە'), findsOneWidget);
    expect(draft.lines.length, 1);

    final cust = db.q('SELECT * FROM customers ORDER BY id').first;
    final second = db.q('SELECT * FROM items ORDER BY id')[1];
    draft.cust.text = cust['name'] as String;
    draft.item.text = second['name'] as String;
    await t.pumpAndSettle();
    final s = t.state<SalesPageState>(find.byType(SalesPage));
    s.pickItem(second['name'] as String);
    draft.qty.n = 3;
    await s.addLine();
    await t.pumpAndSettle();
    draft.disc.n = 1000;
    draft.paid.n = 5000;
    await t.pumpAndSettle();
    await shot(t, 'dark_sale');

    final bal0 = db.balance(cust['id'] as int);
    final q0 = toD(db.one('SELECT qty FROM items WHERE id=?', [item['id']])!['qty']);
    final n0 = db.val('SELECT COUNT(*) FROM invoices');
    await press(t, 'تۆمارکردنی پسووڵە');
    await shot(t, 'dark_saved');
    await press(t, 'باشە');
    final inv = db.one('SELECT * FROM invoices ORDER BY id DESC')!;
    final expected = 2 * toD(item['price']) + 3 * toD(second['price']) - 1000;
    expect(db.val('SELECT COUNT(*) FROM invoices'), n0 + 1);
    expect(toD(inv['total']), closeTo(expected, .001));
    expect(toD(inv['paid']), 5000);
    expect(db.balance(cust['id'] as int), closeTo(bal0 + expected - 5000, .001));
    expect(toD(db.one('SELECT qty FROM items WHERE id=?', [item['id']])!['qty']), closeTo(q0 - 2, .001));
    expect(draft.lines, isEmpty);

    // ---- documents ----
    await t.runAsync(() async {
      File('$out/invoice.pdf').writeAsBytesSync(await docPdf(invoiceDoc(inv['id'] as int)));
      File('$out/labels_a4.pdf').writeAsBytesSync(await labelsPdf(0, 30, item['name'] as String, '212345678901', money(item['price'])));
      File('$out/labels_roll.pdf').writeAsBytesSync(await labelsPdf(2, 2, item['name'] as String, '212345678901', money(item['price'])));
      // one sticker as an image, for a scanner library to read back
      File('$out/label.png').writeAsBytesSync(await renderPng(
          SizedBox(width: 198.4, height: 105.2, child: LabelView(item['name'] as String, '212345678901', '6,000 د.ع', pixelRatio: 4)),
          const Size(198.4, 105.2), 4));
    });

    await press(t, 'پسووڵەکان');
    await shot(t, 'dark_sale_list');

    // ---- every other page ----
    await nav(t, 'کڕیاران');
    await shot(t, 'dark_cust');
    await t.tap(find.text(cust['name'] as String).first);
    await press(t, 'کەشف حساب');
    await shot(t, 'dark_statement');
    await press(t, 'داخستن');

    await nav(t, 'مەخزەن');
    await shot(t, 'dark_inv');
    await t.tap(find.text(item['name'] as String).first);
    await press(t, 'دەستکاری');
    await shot(t, 'dark_item_form');
    await press(t, 'پاشگەزبوونەوە');
    await press(t, 'چاپی بارکۆد');
    await shot(t, 'dark_labels');
    await press(t, 'داخستن');

    await nav(t, 'دابینکەران');
    await shot(t, 'dark_sup');
    await nav(t, 'مەسروفات و مووچە');
    await shot(t, 'dark_exp');
    await nav(t, 'ڕاپۆرت');
    await shot(t, 'dark_rep');
    final rep = t.state<ReportsPageState>(find.byType(ReportsPage));
    await t.runAsync(() async => File('$out/report.pdf').writeAsBytesSync(await docPdf(rep.reportDoc())));
    await nav(t, 'ڕێکخستن');
    await shot(t, 'dark_settings');

    // ---- light theme ----
    await press(t, 'دۆخی ڕووناک');
    await nav(t, 'داشبۆرد');
    await shot(t, 'light_dash');
    await nav(t, 'فرۆشتن');
    await shot(t, 'light_sale');
    await press(t, 'دۆخی تاریک');
  });
}
