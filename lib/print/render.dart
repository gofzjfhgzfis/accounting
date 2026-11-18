// نەخشاندنی ویجێت بۆ وێنە بەبێ پیشاندانی لەسەر شاشە.
//
// پسووڵە و ڕاپۆرتەکان بە Flutter خۆی دەنەخشێنرێن و پاشان وەک وێنە دەخرێنە
// ناو PDF ـەوە. هۆکارەکەی ئەوەیە کە پاکێجی PDF هەموو پیتە کوردییەکان
// (ڕ، ڵ، ێ، ە) بە دروستی پێکەوە نابەستێت، بەڵام Flutter دەیانبەستێت.
import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:flutter/rendering.dart';
import 'package:material_ui/material_ui.dart';

Future<Uint8List> renderPng(Widget widget, Size size, double pixelRatio) async {
  final view = WidgetsBinding.instance.platformDispatcher.views.first;
  final boundary = RenderRepaintBoundary();
  final renderView = RenderView(
    view: view,
    child: RenderPositionedBox(alignment: Alignment.topLeft, child: boundary),
    configuration: ViewConfiguration(
      logicalConstraints: BoxConstraints.tight(size),
      physicalConstraints: BoxConstraints.tight(size),
      devicePixelRatio: 1.0,
    ),
  );
  final pipeline = PipelineOwner()..rootNode = renderView;
  renderView.prepareInitialFrame();
  final buildOwner = BuildOwner(focusManager: FocusManager());
  final root = RenderObjectToWidgetAdapter<RenderBox>(
    container: boundary,
    child: MediaQuery(
      data: const MediaQueryData(),
      child: Directionality(
        textDirection: TextDirection.rtl,
        child: DefaultTextStyle(
          style: const TextStyle(fontFamily: 'Segoe UI', color: Color(0xFF2B2F36), fontSize: 10),
          child: widget,
        ),
      ),
    ),
  ).attachToRenderTree(buildOwner);
  buildOwner.buildScope(root);
  buildOwner.finalizeTree();
  pipeline.flushLayout();
  pipeline.flushCompositingBits();
  pipeline.flushPaint();
  final image = await boundary.toImage(pixelRatio: pixelRatio);
  final bytes = await image.toByteData(format: ui.ImageByteFormat.png);
  image.dispose();
  return bytes!.buffer.asUint8List();
}
