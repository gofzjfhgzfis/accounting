// داتابەیسی SQLite — هەمان شێوەی وەشانی پێشوو، بۆیە داتاکان وەک خۆیان دەمێننەوە.
import 'dart:io';

import 'package:path/path.dart' as p;
import 'package:sqlite3/sqlite3.dart';

import 'config.dart';
import 'fmt.dart';

const schema = '''
CREATE TABLE IF NOT EXISTS settings(k TEXT PRIMARY KEY, v TEXT);
CREATE TABLE IF NOT EXISTS customers(
    id INTEGER PRIMARY KEY, name TEXT, phone TEXT, address TEXT, note TEXT);
CREATE TABLE IF NOT EXISTS items(
    id INTEGER PRIMARY KEY, name TEXT, kind TEXT, unit TEXT,
    qty REAL DEFAULT 0, cost REAL DEFAULT 0, price REAL DEFAULT 0, minq REAL DEFAULT 0);
CREATE TABLE IF NOT EXISTS invoices(
    id INTEGER PRIMARY KEY, date TEXT, customer_id INTEGER,
    subtotal REAL, discount REAL, total REAL, paid REAL, note TEXT);
CREATE TABLE IF NOT EXISTS invoice_items(
    id INTEGER PRIMARY KEY, invoice_id INTEGER, item_id INTEGER,
    qty REAL, price REAL, cost REAL);
CREATE TABLE IF NOT EXISTS payments(
    id INTEGER PRIMARY KEY, date TEXT, customer_id INTEGER, amount REAL, note TEXT);
CREATE TABLE IF NOT EXISTS suppliers(
    id INTEGER PRIMARY KEY, name TEXT, phone TEXT, address TEXT, note TEXT);
CREATE TABLE IF NOT EXISTS purchases(
    id INTEGER PRIMARY KEY, date TEXT, supplier TEXT, item_id INTEGER,
    qty REAL, price REAL, note TEXT, supplier_id INTEGER, paid REAL DEFAULT 0);
CREATE TABLE IF NOT EXISTS supplier_payments(
    id INTEGER PRIMARY KEY, date TEXT, supplier_id INTEGER, amount REAL, note TEXT);
CREATE TABLE IF NOT EXISTS expenses(
    id INTEGER PRIMARY KEY, date TEXT, category TEXT, amount REAL, note TEXT);
CREATE TABLE IF NOT EXISTS employees(
    id INTEGER PRIMARY KEY, name TEXT, position TEXT, salary REAL, phone TEXT);
CREATE TABLE IF NOT EXISTS salaries(
    id INTEGER PRIMARY KEY, date TEXT, employee_id INTEGER, amount REAL, note TEXT);
''';

/// What a customer still owes: unpaid invoice totals minus later payments.
const custBal = '(IFNULL((SELECT SUM(total-paid) FROM invoices WHERE customer_id=c.id),0)'
    ' - IFNULL((SELECT SUM(amount) FROM payments WHERE customer_id=c.id),0))';

/// What the shop still owes a supplier.
const supBal = '(IFNULL((SELECT SUM(qty*price-paid) FROM purchases WHERE supplier_id=s.id),0)'
    ' - IFNULL((SELECT SUM(amount) FROM supplier_payments WHERE supplier_id=s.id),0))';

/// One database row, by column name.
typedef Rec = Map<String, dynamic>;

class Period {
  final double sales, cogs, exp, sal, pur;
  final int count;
  Period(this.sales, this.count, this.cogs, this.exp, this.sal, this.pur);
  double get gross => sales - cogs;
  double get net => gross - exp - sal;
}

class Db {
  late final Database con;
  final String path;

  Db(this.path) {
    Directory(p.dirname(path)).createSync(recursive: true);
    con = sqlite3.open(path);
    con.execute(schema);
    _migrate();
    for (final (k, v) in [
      ('company', ''), ('phone', ''), ('address', ''), ('currency', 'د.ع'),
      ('usd', '1320'), ('backup', ''), ('theme', 'dark'), ('pin', ''),
    ]) {
      con.execute('INSERT OR IGNORE INTO settings(k,v) VALUES(?,?)', [k, v]);
    }
  }

  /// Bring a database made by an older version up to today's shape.
  void _migrate() {
    Set<String> cols(String t) => {for (final r in q('PRAGMA table_info($t)')) r['name'] as String};
    if (!cols('purchases').contains('supplier_id')) {
      con.execute('ALTER TABLE purchases ADD COLUMN supplier_id INTEGER');
      con.execute('ALTER TABLE purchases ADD COLUMN paid REAL DEFAULT 0');
      // the oldest version had no supplier debts: every purchase was cash
      con.execute('UPDATE purchases SET paid=qty*price');
    }
    if (!cols('items').contains('barcode')) {
      con.execute('ALTER TABLE items ADD COLUMN barcode TEXT');
    }
    con.execute('CREATE INDEX IF NOT EXISTS items_barcode ON items(barcode)');
    // purchases that only carry a typed supplier name get a real supplier
    for (final r in q("SELECT DISTINCT TRIM(supplier) n FROM purchases "
        "WHERE supplier_id IS NULL AND TRIM(IFNULL(supplier,''))<>''")) {
      final sid = supplierId(r['n'] as String);
      con.execute('UPDATE purchases SET supplier_id=? WHERE supplier_id IS NULL AND TRIM(supplier)=?',
          [sid, r['n']]);
    }
  }

  // ---- بنەڕەت ----
  List<Rec> q(String sql, [List<Object?> args = const []]) => con.select(sql, args);

  Rec? one(String sql, [List<Object?> args = const []]) {
    final r = con.select(sql, args);
    return r.isEmpty ? null : r.first;
  }

  /// Run a statement and return the new row id (for INSERTs).
  int x(String sql, [List<Object?> args = const []]) {
    con.execute(sql, args);
    return con.lastInsertRowId;
  }

  double val(String sql, [List<Object?> args = const []]) {
    final r = one(sql, args);
    return r == null ? 0 : toD(r.values.first);
  }

  /// All-or-nothing: a failure part way leaves the data as it was.
  T tx<T>(T Function() body) {
    con.execute('BEGIN');
    try {
      final out = body();
      con.execute('COMMIT');
      return out;
    } catch (_) {
      con.execute('ROLLBACK');
      rethrow;
    }
  }

  String get(String k, [String d = '']) => (one('SELECT v FROM settings WHERE k=?', [k])?['v'] as String?) ?? d;

  void set(String k, Object v) =>
      con.execute('INSERT INTO settings(k,v) VALUES(?,?) ON CONFLICT(k) DO UPDATE SET v=excluded.v', [k, '$v']);

  // ---- حیساب ----
  double balance(int cid) => val('SELECT $custBal FROM customers c WHERE c.id=?', [cid]);

  List<Rec> customers([String search = '']) => q(
      'SELECT c.*, $custBal bal FROM customers c '
      "WHERE c.name LIKE ? OR IFNULL(c.phone,'') LIKE ? ORDER BY c.name",
      ['%$search%', '%$search%']);

  double supplierBalance(int sid) => val('SELECT $supBal FROM suppliers s WHERE s.id=?', [sid]);

  List<Rec> suppliers([String search = '']) => q(
      'SELECT s.*, $supBal bal FROM suppliers s '
      "WHERE s.name LIKE ? OR IFNULL(s.phone,'') LIKE ? ORDER BY s.name",
      ['%$search%', '%$search%']);

  /// Id of the supplier with this name, creating it when it is new.
  int? supplierId(String? name) {
    final n = (name ?? '').trim();
    if (n.isEmpty) return null;
    final r = one('SELECT id FROM suppliers WHERE name=?', [n]);
    if (r != null) return r['id'] as int;
    return x('INSERT INTO suppliers(name) VALUES(?)', [n]);
  }

  /// The item carrying this barcode (other than item [skip]), or null.
  Rec? itemByCode(String code, [int? skip]) {
    if (code.isEmpty) return null;
    return one('SELECT * FROM items WHERE barcode=? AND id IS NOT ?', [code, skip]);
  }

  /// Sales, cost and profit figures between two ISO dates (inclusive).
  Period period(String a, String b) {
    final s = one('SELECT IFNULL(SUM(total),0) t, COUNT(*) c FROM invoices WHERE date BETWEEN ? AND ?', [a, b])!;
    return Period(
      toD(s['t']),
      s['c'] as int,
      val('SELECT SUM(ii.qty*ii.cost) FROM invoice_items ii JOIN invoices i ON i.id=ii.invoice_id '
          'WHERE i.date BETWEEN ? AND ?', [a, b]),
      val('SELECT SUM(amount) FROM expenses WHERE date BETWEEN ? AND ?', [a, b]),
      val('SELECT SUM(amount) FROM salaries WHERE date BETWEEN ? AND ?', [a, b]),
      val('SELECT SUM(qty*price) FROM purchases WHERE date BETWEEN ? AND ?', [a, b]),
    );
  }

  // ---- باکئەپ ----
  /// Write a consistent copy into [folder] and keep only the newest [keep].
  String backupTo(String folder, {bool daily = false, int keep = 20}) {
    final n = DateTime.now();
    String two(int v) => v.toString().padLeft(2, '0');
    final stamp = daily ? isoDate(n) : '${isoDate(n)}_${two(n.hour)}-${two(n.minute)}';
    final name = 'oil_shop_$stamp.db';
    final target = File(p.join(folder, name));
    if (target.existsSync()) target.deleteSync();
    con.execute('VACUUM INTO ?', [target.path]);
    final old = Directory(folder)
        .listSync()
        .whereType<File>()
        .map((f) => p.basename(f.path))
        .where((f) => f.startsWith('oil_shop_') && f.endsWith('.db'))
        .toList()
      ..sort();
    for (final f in old.take(old.length > keep ? old.length - keep : 0)) {
      try {
        File(p.join(folder, f)).deleteSync();
      } catch (_) {}
    }
    return name;
  }

  void close() => con.close();
}

/// The open database. Set once at start-up by [openDb].
late Db db;

void openDb() => db = Db(dbPath);
