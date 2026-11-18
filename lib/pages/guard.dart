// ڕێگری لە گۆڕانکاری لە ڕۆژە داخراوەکاندا.
import 'package:material_ui/material_ui.dart';

import '../core/db.dart';
import '../core/fmt.dart';
import '../ui/widgets.dart';

/// False (after telling the user why) when [date] is on a closed day.
///
/// Once a day is closed its cash count is final, so nothing dated on it may
/// be added, changed or deleted until that closing is reopened.
bool dayOpen(BuildContext context, String date) {
  if (!db.isClosed(date)) return true;
  info(context,
      'ڕۆژی ${lrm(date)} داخراوە، بۆیە ناتوانرێت گۆڕانکاری تێدا بکرێت.\n'
      'ئەگەر پێویستە، لە بەشی «سندوق» دوایین داخستن بکەرەوە.');
  return false;
}
