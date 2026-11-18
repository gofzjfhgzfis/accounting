// نەخشاندنی هێڵەکانی بارکۆد و لەیبڵ.
import 'package:material_ui/material_ui.dart';

import '../core/barcode.dart';

class BarcodePainter extends CustomPainter {
  final String code;

  /// Device pixels per logical pixel. Bars are snapped to whole device pixels
  /// so a printed barcode keeps sharp, even edges a scanner can read.
  final double pixelRatio;
  BarcodePainter(this.code, {this.pixelRatio = 1});

  @override
  void paint(Canvas canvas, Size size) {
    final ws = widths(code);
    final total = ws.fold<int>(0, (s, w) => s + w) + 2 * quietZone;
    var unit = size.width / total;
    final px = (unit * pixelRatio).floorToDouble();
    if (px >= 1) unit = px / pixelRatio;
    var x = (size.width - unit * total) / 2 + quietZone * unit;
    x = (x * pixelRatio).roundToDouble() / pixelRatio;
    final paint = Paint()..color = const Color(0xFF000000)..isAntiAlias = false;
    for (var i = 0; i < ws.length; i++) {
      if (i.isEven) canvas.drawRect(Rect.fromLTWH(x, 0, ws[i] * unit, size.height), paint);
      x += ws[i] * unit;
    }
  }

  @override
  bool shouldRepaint(BarcodePainter old) => old.code != code || old.pixelRatio != pixelRatio;
}

/// One sticker: item name, bars, the code in digits and (optionally) the price.
class LabelView extends StatelessWidget {
  final String name, code, price;
  final double pixelRatio;
  const LabelView(this.name, this.code, this.price, {super.key, this.pixelRatio = 1});

  @override
  Widget build(BuildContext context) => LayoutBuilder(builder: (context, box) {
        final w = box.maxWidth, h = box.maxHeight;
        final pad = (w < h ? w : h) * .06;
        final inner = h - pad * 1.6;
        final rows = price.isEmpty ? [.26, .56, .18, 0.0] : [.22, .46, .14, .18];
        const black = Color(0xFF000000);
        Widget line(String t, double frac, {bool bold = true, String? family}) => SizedBox(
              height: inner * frac,
              child: Center(
                child: Text(t,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    textAlign: TextAlign.center,
                    style: TextStyle(
                        fontFamily: family ?? 'Segoe UI',
                        fontSize: inner * frac * (family == null ? .66 : .78),
                        height: 1.1,
                        fontWeight: bold ? FontWeight.w700 : FontWeight.w400,
                        color: black)),
              ),
            );
        return Container(
          color: const Color(0xFFFFFFFF),
          padding: EdgeInsets.symmetric(horizontal: pad, vertical: pad * .8),
          child: Column(children: [
            line(name, rows[0]),
            SizedBox(
              height: inner * rows[1],
              child: Padding(
                padding: EdgeInsets.only(top: inner * rows[1] * .06),
                child: CustomPaint(size: Size.infinite, painter: BarcodePainter(code, pixelRatio: pixelRatio)),
              ),
            ),
            Directionality(textDirection: TextDirection.ltr, child: line(code, rows[2], bold: false, family: 'Consolas')),
            if (price.isNotEmpty) line(price, rows[3]),
          ]),
        );
      });
}
