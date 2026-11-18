// بارکۆدی Code 128: کۆدکردن و درووستکردنی ژمارەی نوێ.
//
// Code 128 هەڵبژێردراوە چونکە هەموو سکانەرێکی USB دەیخوێنێتەوە و هەم
// ژمارە و هەم پیتی ئینگلیزی وەردەگرێت.
import 'dart:math';

import 'fmt.dart';

/// Bar/space widths (in modules) of every Code 128 symbol, per the standard.
/// Each symbol is 3 bars + 3 spaces summing to 11; STOP is 4 bars summing to 13.
const patterns = <String>[
  '212222', '222122', '222221', '121223', '121322', '131222', '122213', '122312',
  '132212', '221213', '221312', '231212', '112232', '122132', '122231', '113222',
  '123122', '123221', '223211', '221132', '221231', '213212', '223112', '312131',
  '311222', '321122', '321221', '312212', '322112', '322211', '212123', '212321',
  '232121', '111323', '131123', '131321', '112313', '132113', '132311', '211313',
  '231113', '231311', '112133', '112331', '132131', '113123', '113321', '133121',
  '313121', '211331', '231131', '213113', '213311', '213131', '311123', '311321',
  '331121', '312113', '312311', '332111', '314111', '221411', '431111', '111224',
  '111422', '121124', '121421', '141122', '141221', '112214', '112412', '122114',
  '122411', '142112', '142211', '241211', '221114', '413111', '241112', '134111',
  '111242', '121142', '121241', '114212', '124112', '124211', '411212', '421112',
  '421211', '212141', '214121', '412121', '111143', '111341', '131141', '114113',
  '114311', '411113', '411311', '113141', '114131', '311141', '411131', '211412',
  '211214', '211232', '2331112',
];
const _startB = 104, _startC = 105, _stop = 106;

/// Blank space required on each side, in modules.
const quietZone = 10;

/// Clean a typed or scanned code. A scanner "types" like a keyboard, so with
/// the Kurdish layout active digits can arrive as ١٢٣ — they become 123 here.
String normCode(String? code) => asciiDigits(code ?? '').replaceAll(RegExp(r'\s'), '');

bool validCode(String code) =>
    code.isNotEmpty && code.codeUnits.every((c) => c > 32 && c < 127);

/// Symbol values for `code`: start, data, checksum, stop.
List<int> encode(String code) {
  if (!validCode(code)) {
    throw ArgumentError('بارکۆد تەنها ژمارە و پیتی ئینگلیزی وەردەگرێت');
  }
  final List<int> vals;
  if (RegExp(r'^\d+$').hasMatch(code) && code.length.isEven) {
    // جۆری C: هەر دوو ژمارە یەک نیشانەیە، بۆیە بارکۆدەکە کورتتر دەبێت
    vals = [_startC, for (var i = 0; i < code.length; i += 2) int.parse(code.substring(i, i + 2))];
  } else {
    vals = [_startB, for (final c in code.codeUnits) c - 32];
  }
  var check = vals[0];
  for (var i = 1; i < vals.length; i++) {
    check += i * vals[i];
  }
  return [...vals, check % 103, _stop];
}

/// Alternating bar/space widths in modules, starting with a bar.
List<int> widths(String code) =>
    [for (final v in encode(code)) for (final ch in patterns[v].split('')) int.parse(ch)];

/// A new 12-digit in-shop code that [exists] says is unused. It starts with 2,
/// the range kept for codes a shop prints itself, so it cannot clash with a
/// manufacturer's barcode.
String generateCode(bool Function(String) exists) {
  final r = Random.secure();
  while (true) {
    final code = '2${List.generate(11, (_) => r.nextInt(10)).join()}';
    if (!exists(code)) return code;
  }
}
