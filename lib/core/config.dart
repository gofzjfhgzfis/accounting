// شوێنی فایلەکان و config.ini.
//
// config.ini لەسەر ئەم کۆمپیوتەرە دەمێنێتەوە، بۆیە داتابەیسەکە دەتوانێت
// لە شوێنێکی تر بێت (فۆڵدەرێکی تۆڕ یان کلاود) بێ ئەوەی هیچی تر بگۆڕێت.
import 'dart:io';

import 'package:path/path.dart' as p;

const appTitle = 'سیستەمی دووکانی جوملە';
const appVersion = '٣٫٠٫١';

/// OILSHOP_HOME lets tests run against a throw-away folder.
final String homeDir = Platform.environment['OILSHOP_HOME'] ??
    Platform.environment['USERPROFILE'] ?? Platform.environment['HOME'] ?? '.';
final String appDir = p.join(homeDir, 'OilShopAccounting');
final String cfgPath = p.join(appDir, 'config.ini');

/// The `[app]` section of config.ini (same file the older version wrote).
final Map<String, String> _cfg = _readCfg();

Map<String, String> _readCfg() {
  Directory(appDir).createSync(recursive: true);
  _carryOverOldFolder();
  final out = <String, String>{};
  final f = File(cfgPath);
  if (!f.existsSync()) return out;
  var inApp = false;
  for (final raw in f.readAsLinesSync()) {
    final line = raw.trim();
    if (line.startsWith('[')) {
      inApp = line == '[app]';
    } else if (inApp && line.contains('=')) {
      final i = line.indexOf('=');
      out[line.substring(0, i).trim()] = line.substring(i + 1).trim();
    }
  }
  return out;
}

/// Data saved under the folder this app used to have is copied once, so the
/// rename does not look like the records disappeared.
void _carryOverOldFolder() {
  final old = p.join(homeDir, 'GoldenBaseShop');
  if (!Directory(old).existsSync()) return;
  for (final (a, b) in [('config.ini', 'config.ini'), ('golden_shop.db', 'oil_shop.db')]) {
    final src = File(p.join(old, a)), dst = File(p.join(appDir, b));
    if (src.existsSync() && !dst.existsSync()) {
      try {
        src.copySync(dst.path);
      } catch (_) {}
    }
  }
}

String get dbPath {
  final v = _cfg['db_path'] ?? '';
  return v.isNotEmpty ? v : p.join(appDir, 'oil_shop.db');
}

void saveCfg(Map<String, String> values) {
  _cfg.addAll(values);
  final b = StringBuffer('[app]\n');
  _cfg.forEach((k, v) => b.writeln('$k = $v'));
  File(cfgPath).writeAsStringSync('$b\n');
}
