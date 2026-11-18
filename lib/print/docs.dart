// پسووڵە، کەشف حساب، ڕاپۆرت و لەیبڵی بارکۆد — درووستکردنی PDF و چاپکردن.
import 'dart:io';
import 'dart:typed_data';

import 'package:file_selector/file_selector.dart';
import 'package:material_ui/material_ui.dart';
import 'package:path/path.dart' as p;
import 'package:pdf/pdf.dart';
import 'package:pdf/widgets.dart' as pw;
import 'package:printing/printing.dart';

import '../core/config.dart';
import '../core/db.dart';
import '../core/fmt.dart';
import '../ui/barcode_view.dart';
import 'render.dart';

// ---------------------------------------------------------------- پێکهاتەی بەڵگەنامە
const _ink = Color(0xFF2B2F36), _grey = Color(0xFF5A626C), _faint = Color(0xFF8A9099);
const _gold = Color(0xFFB8860B), _goldLight = Color(0xFFE2CF95), _cream = Color(0xFFFAF5E8);
const _rule = Color(0xFFE4E0D8), _red = Color(0xFFC0392B);

/// A4 in PDF points (1/72 inch); the page is laid out in these units.
const _pageW = 595.28, _pageH = 841.89, _margin = 40.0;
const _rowH = 22.0, _headH = 26.0;

sealed class Block {
  double get height;
}

class Gap extends Block {
  @override
  final double height;
  Gap(this.height);
}

class Heading extends Block {
  final String text;
  Heading(this.text);
  @override
  double get height => 34;
}

class Para extends Block {
  final String text;
  final Color color;
  final double size;
  final bool bold;
  final TextAlign align;
  Para(this.text, {this.color = _grey, this.size = 10, this.bold = false, this.align = TextAlign.right});
  @override
  double get height => size * 2.2;
}

/// (label, value, bold, colour, cream background)
class Totals extends Block {
  final List<(String, String, bool, Color, bool)> rows;
  Totals(this.rows);
  @override
  double get height => rows.length * 25.0 + 6;
}

class DocTable extends Block {
  final List<String> headers;
  final List<int> flex;
  final List<List<String>> rows;
  DocTable(this.headers, this.flex, this.rows);
  @override
  double get height => _headH + (rows.isEmpty ? 1 : rows.length) * _rowH;
}

class Doc {
  final String title, sub;
  final List<Block> blocks;
  Doc(this.title, this.sub, this.blocks);
}

/// Spread the blocks over A4 pages; long tables continue on the next page
/// with their header repeated.
List<List<Block>> _paginate(Doc d) {
  const usable = _pageH - 2 * _margin - 20;       // 20 = page-number line
  const letterhead = 128.0, contHead = 30.0;
  final pages = <List<Block>>[[]];
  var left = usable - letterhead;
  void newPage() {
    pages.add([]);
    left = usable - contHead;
  }

  for (final b in d.blocks) {
    if (b is DocTable) {
      var rows = b.rows;
      while (true) {
        final fit = ((left - _headH) / _rowH).floor();
        if (rows.isEmpty) {
          if (left < _headH + _rowH) newPage();
          pages.last.add(DocTable(b.headers, b.flex, const []));
          left -= _headH + _rowH;
          break;
        }
        if (fit < 1) {
          newPage();
          continue;
        }
        final take = rows.take(fit).toList();
        pages.last.add(DocTable(b.headers, b.flex, take));
        left -= _headH + take.length * _rowH;
        rows = rows.skip(take.length).toList();
        if (rows.isEmpty) break;
        newPage();
      }
    } else {
      if (b.height > left && pages.last.isNotEmpty) newPage();
      pages.last.add(b);
      left -= b.height;
    }
  }
  return pages;
}

class _Page extends StatelessWidget {
  final Doc doc;
  final List<Block> blocks;
  final int n, of;
  const _Page(this.doc, this.blocks, this.n, this.of);

  @override
  Widget build(BuildContext context) {
    TextStyle s(double size, {Color color = _ink, bool bold = false}) => TextStyle(
        fontFamily: 'Segoe UI', fontSize: size, color: color, fontWeight: bold ? FontWeight.w700 : FontWeight.w400);
    final contact = [db.get('address'), if (db.get('phone').isNotEmpty) lrm(db.get('phone'))]
        .where((e) => e.isNotEmpty)
        .join('   ·   ');

    Widget block(Block b) => switch (b) {
          Gap() => SizedBox(height: b.height),
          Heading() => Padding(
              padding: const EdgeInsets.only(top: 12, bottom: 6),
              child: Text(b.text, style: s(12, color: _gold, bold: true))),
          Para() => SizedBox(
              height: b.height,
              child: Align(
                  alignment: AlignmentDirectional.centerStart,
                  child: Text(b.text, textAlign: b.align, style: s(b.size, color: b.color, bold: b.bold)))),
          Totals() => Padding(
              padding: const EdgeInsets.only(top: 6),
              child: Column(children: [
                for (final r in b.rows)
                  Container(
                    height: 25,
                    color: r.$5 ? _cream : null,
                    padding: const EdgeInsets.symmetric(horizontal: 14),
                    child: Row(children: [
                      Expanded(flex: 6, child: Text(r.$1, style: s(11, color: r.$4, bold: r.$3))),
                      Expanded(flex: 4, child: Text(r.$2, style: s(11, color: r.$4, bold: r.$3))),
                    ]),
                  ),
              ])),
          DocTable() => _table(b, s),
        };

    return Container(
      width: _pageW,
      height: _pageH,
      color: Colors.white,
      padding: const EdgeInsets.all(_margin),
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        if (n == 1) ...[
          Text(db.get('company'), textAlign: TextAlign.center, style: s(22, color: _gold, bold: true)),
          if (contact.isNotEmpty)
            Padding(
                padding: const EdgeInsets.only(top: 4),
                child: Text(contact, textAlign: TextAlign.center, style: s(10, color: _faint))),
          const SizedBox(height: 10),
          Container(height: 3, color: _gold),
          const SizedBox(height: 2),
          Container(height: 1, color: _goldLight),
          const SizedBox(height: 14),
          Text(doc.title, style: s(14, bold: true)),
          const SizedBox(height: 3),
          Text(doc.sub, style: s(10.5, color: _grey)),
          const SizedBox(height: 8),
        ] else
          SizedBox(
            height: 30,
            child: Text('${doc.title} — ${db.get('company')}', style: s(10, color: _faint)),
          ),
        for (final b in blocks) block(b),
        const Spacer(),
        if (of > 1)
          Text('لاپەڕە $n لە $of', textAlign: TextAlign.center, style: s(8.5, color: _faint)),
      ]),
    );
  }

  Widget _table(DocTable t, TextStyle Function(double, {Color color, bool bold}) s) {
    Widget row(List<String> cells, {bool head = false}) => Container(
          height: head ? _headH : _rowH,
          decoration: BoxDecoration(
            color: head ? _cream : null,
            border: const Border(
                left: BorderSide(color: _rule), right: BorderSide(color: _rule), bottom: BorderSide(color: _rule)),
          ),
          child: Row(children: [
            for (var i = 0; i < t.headers.length; i++)
              Expanded(
                flex: t.flex[i],
                child: Container(
                  alignment: Alignment.center,
                  padding: const EdgeInsets.symmetric(horizontal: 5),
                  decoration: BoxDecoration(
                      border: i == t.headers.length - 1 ? null : const Border(left: BorderSide(color: _rule))),
                  child: Text(i < cells.length ? cells[i] : '',
                      maxLines: 1, overflow: TextOverflow.ellipsis, style: s(head ? 10.5 : 10, bold: head)),
                ),
              ),
          ]),
        );
    return Container(
      decoration: const BoxDecoration(border: Border(top: BorderSide(color: _rule))),
      child: Column(children: [
        row(t.headers, head: true),
        if (t.rows.isEmpty) row(['—']) else for (final r in t.rows) row(r),
      ]),
    );
  }
}

/// Render [doc] to a multi-page A4 PDF.
Future<Uint8List> docPdf(Doc doc) async {
  final pages = _paginate(doc);
  final pdf = pw.Document(title: doc.title, creator: appTitle);
  for (var i = 0; i < pages.length; i++) {
    final png = await renderPng(_Page(doc, pages[i], i + 1, pages.length), const Size(_pageW, _pageH), 4);
    pdf.addPage(pw.Page(
      pageFormat: PdfPageFormat.a4.copyWith(marginTop: 0, marginBottom: 0, marginLeft: 0, marginRight: 0),
      build: (_) => pw.Image(pw.MemoryImage(png), fit: pw.BoxFit.fill),
    ));
  }
  return pdf.save();
}

// ---------------------------------------------------------------- بەڵگەنامەکان
const walkIn = 'کڕیاری نەقد';

Doc invoiceDoc(int iid) {
  final inv = db.one('SELECT * FROM invoices WHERE id=?', [iid])!;
  final cus = db.one('SELECT * FROM customers WHERE id=?', [inv['customer_id']]);
  final rows = db.q("SELECT ii.*, IFNULL(it.name,'—') name, IFNULL(it.unit,'') unit FROM invoice_items ii "
      'LEFT JOIN items it ON it.id=ii.item_id WHERE ii.invoice_id=?', [iid]);
  final due = toD(inv['total']) - toD(inv['paid']);
  final cur = db.get('currency');
  String m(Object? v) => '${fmt(v)} $cur';
  return Doc(
    'پسووڵەی فرۆشتن',
    'ژمارە: ${lrm(iid)}   ·   بەروار: ${lrm(inv['date'])}   ·   کڕیار: ${cus?['name'] ?? walkIn}'
        '   ·   مۆبایل: ${(cus?['phone'] as String?)?.isNotEmpty == true ? lrm(cus!['phone']) : '—'}',
    [
      DocTable(['ژ', 'کاڵا', 'بڕ', 'نرخ', 'کۆ'], [2, 12, 4, 4, 5], [
        for (var i = 0; i < rows.length; i++)
          [
            '${i + 1}', rows[i]['name'] as String, '${fmt(rows[i]['qty'])} ${rows[i]['unit']}'.trim(),
            fmt(rows[i]['price']), fmt(toD(rows[i]['qty']) * toD(rows[i]['price'])),
          ]
      ]),
      Gap(10),
      Totals([
        ('کۆی گشتی', m(inv['subtotal']), false, _ink, false),
        ('داشکاندن', m(inv['discount']), false, _ink, false),
        ('دوای داشکاندن', m(inv['total']), true, _ink, true),
        ('پارەی دراو', m(inv['paid']), false, _ink, false),
        ('ماوە', m(due), true, due > 0.004 ? _red : _ink, false),
      ]),
      if ((inv['note'] as String?)?.isNotEmpty == true) Para('تێبینی: ${inv['note']}', color: _faint),
      Gap(18),
      Para('سوپاس بۆ متمانەتان — ${db.get('company')}', color: _faint, size: 9),
    ],
  );
}

/// [rows]: (date, text, debit, credit, running balance) already formatted.
Doc statementDoc(String title, String name, List<List<String>> rows, double balance) => Doc(
      title,
      'ناو: $name   ·   بەروار: ${lrm(today())}',
      [
        DocTable(['بەروار', 'ڕوونکردنەوە', 'بڕ', 'پارەی دراو', 'ماوە'], [4, 9, 4, 4, 4], rows),
        Gap(10),
        Para('کۆی ماوە:  ${money(balance)}', color: _red, size: 13, bold: true),
      ],
    );

// ---------------------------------------------------------------- لەیبڵ
/// (name, label width mm, height mm, columns, rows)
const labelLayouts = <(String, double, double, int, int)>[
  ('پەڕەی A4 — ٢٤ لەیبڵ (٣ × ٨)', 70.0, 37.125, 3, 8),
  ('پەڕەی A4 — ٤٠ لەیبڵ (٤ × ١٠)', 52.5, 29.7, 4, 10),
  ('پرینتەری لەیبڵ — ٥٠ × ٣٠ mm', 50.0, 30.0, 1, 1),
  ('پرینتەری لەیبڵ — ٤٠ × ٢٥ mm', 40.0, 25.0, 1, 1),
];

const _mm = 72 / 25.4;

PdfPageFormat labelFormat(int layout) {
  final l = labelLayouts[layout];
  return l.$4 * l.$5 == 1
      ? PdfPageFormat(l.$2 * _mm, l.$3 * _mm, marginAll: 0)
      : PdfPageFormat.a4.copyWith(marginTop: 0, marginBottom: 0, marginLeft: 0, marginRight: 0);
}

/// [count] copies of one label laid out on sheets (filled right to left).
Future<Uint8List> labelsPdf(int layout, int count, String name, String code, String price) async {
  final l = labelLayouts[layout];
  final perPage = l.$4 * l.$5;
  final fmtPage = labelFormat(layout);
  final size = Size(fmtPage.width, fmtPage.height);
  final ratio = perPage == 1 ? 8.0 : 4.0;   // ~576 / 288 dpi
  final pdf = pw.Document(title: 'بارکۆد', creator: appTitle);
  for (var start = 0; start < count; start += perPage) {
    final n = (count - start).clamp(0, perPage);
    final page = Container(
      width: size.width,
      height: size.height,
      color: Colors.white,
      child: Stack(children: [
        for (var i = 0; i < n; i++)
          PositionedDirectional(
            start: (i % l.$4) * l.$2 * _mm,
            top: (i ~/ l.$4) * l.$3 * _mm,
            width: l.$2 * _mm,
            height: l.$3 * _mm,
            child: LabelView(name, code, price, pixelRatio: ratio),
          ),
      ]),
    );
    final png = await renderPng(page, size, ratio);
    pdf.addPage(pw.Page(pageFormat: fmtPage, build: (_) => pw.Image(pw.MemoryImage(png), fit: pw.BoxFit.fill)));
  }
  return pdf.save();
}

// ---------------------------------------------------------------- پاشەکەوت و چاپ
/// Ask where to save, write the PDF and open it. Returns the path or null.
Future<String?> savePdf(Uint8List bytes, String suggested) async {
  final loc = await getSaveLocation(
    suggestedName: suggested,
    initialDirectory: appDir,
    acceptedTypeGroups: const [XTypeGroup(label: 'PDF', extensions: ['pdf'])],
  );
  if (loc == null) return null;
  var path = loc.path;
  if (p.extension(path).toLowerCase() != '.pdf') path = '$path.pdf';
  await File(path).writeAsBytes(bytes);
  openPath(path);
  return path;
}

Future<void> printPdf(Uint8List bytes, String name, {PdfPageFormat? format}) =>
    Printing.layoutPdf(
      onLayout: (_) async => bytes,
      name: name,
      format: format ?? PdfPageFormat.a4,
      dynamicLayout: false,
    );

/// Open a file or folder with its default Windows program.
void openPath(String path) => Process.run('explorer', [path]);
