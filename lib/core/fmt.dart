// یارمەتیدەرەکانی نووسینی ژمارە، بەروار و دەق.
import 'dart:convert';

import 'package:crypto/crypto.dart';

import 'db.dart';

/// 1234567 → "1,234,567"; 12.5 → "12.50".
String fmt(Object? n) {
  final v = (n is num) ? n.toDouble() : double.tryParse('$n') ?? 0;
  final whole = (v - v.round()).abs() < 0.01;
  final s = whole ? v.round().abs().toString() : v.abs().toStringAsFixed(2);
  final parts = s.split('.');
  final b = StringBuffer();
  final digits = parts[0];
  for (var i = 0; i < digits.length; i++) {
    if (i > 0 && (digits.length - i) % 3 == 0) b.write(',');
    b.write(digits[i]);
  }
  final sign = v < 0 && (whole ? v.round() != 0 : true) ? '-' : '';
  return '$sign$b${parts.length > 1 ? '.${parts[1]}' : ''}';
}

String money(Object? n) => '${fmt(n)} ${db.get('currency')}';

/// Dollar equivalent at the rate from Settings, or '' when no rate is set.
String usd(Object? n) {
  final rate = double.tryParse(db.get('usd')) ?? 0;
  if (rate <= 0) return '';
  final v = ((n is num) ? n.toDouble() : 0) / rate;
  return '≈ $lrmChar\$${fmt(v.roundToDouble())}';
}

final lrmChar = String.fromCharCode(0x200E);

/// Pin a digit-only string so RTL text cannot reorder it (0750 123 4567).
String lrm(Object? v) {
  final s = '${v ?? ''}'.trim();
  return s.isEmpty ? s : '$lrmChar$s';
}

/// "#47" that stays "#47" inside right-to-left text.
String no(Object? id) => '$lrmChar#$id';

/// A left-to-right run such as "12 / 50" that RTL text must not reverse.
String ltrRun(String s) => '${String.fromCharCode(0x2066)}$s${String.fromCharCode(0x2069)}';

/// Keep a phrase like «ڕۆنی 5W-30» in one piece inside RTL text.
String iso(String s) => '${String.fromCharCode(0x2068)}$s${String.fromCharCode(0x2069)}';

String isoDate(DateTime d) =>
    '${d.year.toString().padLeft(4, '0')}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';

String today() => isoDate(DateTime.now());

DateTime monthStart([DateTime? d]) {
  d ??= DateTime.now();
  return DateTime(d.year, d.month, 1);
}

const _ku = '٠١٢٣٤٥٦٧٨٩', _fa = '۰۱۲۳۴۵۶۷۸۹';

/// Turn Kurdish/Persian digits (١٢٣ / ۱۲۳) into 123.
String asciiDigits(String s) {
  final b = StringBuffer();
  for (final ch in s.split('')) {
    var i = _ku.indexOf(ch);
    if (i < 0) i = _fa.indexOf(ch);
    b.write(i >= 0 ? '$i' : ch);
  }
  return b.toString();
}

/// Parse a typed amount: Kurdish digits, thousands commas and «٫» are fine.
double parseNum(String s) =>
    double.tryParse(asciiDigits(s).replaceAll(',', '').replaceAll('٫', '.').trim()) ?? 0;

String pinHash(String pin) => sha256.convert(utf8.encode('oilshop:$pin')).toString();

/// Any number-ish database value as a double (null → 0).
double toD(Object? v) => v is num ? v.toDouble() : double.tryParse('${v ?? ''}') ?? 0;
