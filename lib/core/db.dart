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
CREATE TABLE IF NOT EXISTS returns(
    id INTEGER PRIMARY KEY, date TEXT, invoice_id INTEGER, customer_id INTEGER,
    total REAL, refund REAL, note TEXT);
CREATE TABLE IF NOT EXISTS return_items(
    id INTEGER PRIMARY KEY, return_id INTEGER, item_id INTEGER, qty REAL, price REAL, cost REAL);
CREATE TABLE IF NOT EXISTS cash_moves(
    id INTEGER PRIMARY KEY, date TEXT, amount REAL, note TEXT);
CREATE TABLE IF NOT EXISTS closings(
    id INTEGER PRIMARY KEY, date TEXT UNIQUE, at TEXT, opening REAL, cash_in REAL,
    cash_out REAL, expected REAL, counted REAL, note TEXT);
CREATE TABLE IF NOT EXISTS activity(
    id INTEGER PRIMARY KEY, at TEXT, kind TEXT, action TEXT, ref INTEGER,
    text TEXT, amount REAL, device TEXT);
CREATE INDEX IF NOT EXISTS activity_at ON activity(at);
''';

/// What a customer still owes: unpaid invoice totals, minus later payments,
/// minus returned goods that were not paid back in cash.
const custBal = '(IFNULL((SELECT SUM(total-paid) FROM invoices WHERE customer_id=c.id),0)'
    ' - IFNULL((SELECT SUM(amount) FROM payments WHERE customer_id=c.id),0)'
    ' - IFNULL((SELECT SUM(total-refund) FROM returns WHERE customer_id=c.id),0))';

/// What the shop still owes a supplier.
const supBal = '(IFNULL((SELECT SUM(qty*price-paid) FROM purchases WHERE supplier_id=s.id),0)'
    ' - IFNULL((SELECT SUM(amount) FROM supplier_payments WHERE supplier_id=s.id),0))';

/// One database row, by column name.
typedef Rec = Map<String, dynamic>;

/// One movement of cash in (+) or out (-) of the drawer.
class Move {
  final String date, kind, text;
  final double amount;
  final int? ref;   // the cash_moves row, for movements typed in by hand
  Move(this.date, this.kind, this.text, this.amount, [this.ref]);
}

/// Sales and profit for a period. [sales] and [cogs] are already net of
/// returned goods; [returns] is the value that came back.
class Period {
  final double sales, cogs, exp, sal, pur, returns;
  final int count;
  Period(this.sales, this.count, this.cogs, this.exp, this.sal, this.pur, this.returns);
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
    final ret = val('SELECT SUM(total) FROM returns WHERE date BETWEEN ? AND ?', [a, b]);
    final retCost = val('SELECT SUM(ri.qty*ri.cost) FROM return_items ri JOIN returns r ON r.id=ri.return_id '
        'WHERE r.date BETWEEN ? AND ?', [a, b]);
    return Period(
      toD(s['t']) - ret,
      s['c'] as int,
      val('SELECT SUM(ii.qty*ii.cost) FROM invoice_items ii JOIN invoices i ON i.id=ii.invoice_id '
          'WHERE i.date BETWEEN ? AND ?', [a, b]) - retCost,
      val('SELECT SUM(amount) FROM expenses WHERE date BETWEEN ? AND ?', [a, b]),
      val('SELECT SUM(amount) FROM salaries WHERE date BETWEEN ? AND ?', [a, b]),
      val('SELECT SUM(qty*price) FROM purchases WHERE date BETWEEN ? AND ?', [a, b]),
      ret,
    );
  }

  // ---- گەڕاندنەوە ----
  /// How much of [itemId] on invoice [invoiceId] has already come back.
  double returnedQty(int invoiceId, int itemId) => val(
      'SELECT SUM(ri.qty) FROM return_items ri JOIN returns r ON r.id=ri.return_id '
      'WHERE r.invoice_id=? AND ri.item_id=?', [invoiceId, itemId]);

  // ---- سندوق ----
  /// The most recent day closing, or null when no day was ever closed.
  Rec? get lastClosing => one('SELECT * FROM closings ORDER BY date DESC LIMIT 1');

  /// Days up to and including the last closing are locked: nothing dated on
  /// them may be added, changed or deleted.
  bool isClosed(String date) {
    final c = lastClosing;
    return c != null && date.compareTo(c['date'] as String) <= 0;
  }

  /// Every cash movement dated after [after] (exclusive) up to [upTo], oldest first.
  List<Move> cashMoves(String? after, String upTo) {
    final a = after ?? '0000-00-00';
    String note(Object? n) => (n as String?)?.isNotEmpty == true ? ' — $n' : '';
    final out = <Move>[
      for (final r in q("SELECT i.id, i.date, i.paid, IFNULL(c.name,'کڕیاری نەقد') n FROM invoices i "
          'LEFT JOIN customers c ON c.id=i.customer_id WHERE i.date>? AND i.date<=? AND i.paid>0', [a, upTo]))
        Move(r['date'], 'sale', 'پسووڵە ${no(r['id'])} — ${r['n']}', toD(r['paid'])),
      for (final r in q("SELECT p.date, p.amount, IFNULL(c.name,'—') n FROM payments p "
          'LEFT JOIN customers c ON c.id=p.customer_id WHERE p.date>? AND p.date<=?', [a, upTo]))
        Move(r['date'], 'payment', 'وەرگرتنی پارە — ${r['n']}', toD(r['amount'])),
      for (final r in q('SELECT date, invoice_id, refund FROM returns WHERE date>? AND date<=? AND refund>0', [a, upTo]))
        Move(r['date'], 'return', 'گەڕاندنەوەی پارە — پسووڵە ${no(r['invoice_id'])}', -toD(r['refund'])),
      for (final r in q("SELECT p.date, p.paid, p.qty, IFNULL(i.name,'—') n FROM purchases p "
          'LEFT JOIN items i ON i.id=p.item_id WHERE p.date>? AND p.date<=? AND p.paid>0', [a, upTo]))
        Move(r['date'], 'purchase', 'کڕین — ${r['n']} × ${fmt(r['qty'])}', -toD(r['paid'])),
      for (final r in q("SELECT p.date, p.amount, IFNULL(s.name,'—') n FROM supplier_payments p "
          'LEFT JOIN suppliers s ON s.id=p.supplier_id WHERE p.date>? AND p.date<=?', [a, upTo]))
        Move(r['date'], 'supplier', 'دانی پارە بە دابینکەر — ${r['n']}', -toD(r['amount'])),
      for (final r in q('SELECT date, amount, category FROM expenses WHERE date>? AND date<=?', [a, upTo]))
        Move(r['date'], 'expense', 'مەسروف — ${r['category'] ?? ''}', -toD(r['amount'])),
      for (final r in q("SELECT s.date, s.amount, IFNULL(e.name,'—') n FROM salaries s "
          'LEFT JOIN employees e ON e.id=s.employee_id WHERE s.date>? AND s.date<=?', [a, upTo]))
        Move(r['date'], 'salary', 'مووچە — ${r['n']}', -toD(r['amount'])),
      for (final r in q('SELECT id, date, amount, note FROM cash_moves WHERE date>? AND date<=?', [a, upTo]))
        Move(r['date'], 'cash',
            '${toD(r['amount']) >= 0 ? 'خستنە ناو سندوق' : 'دەرهێنان لە سندوق'}${note(r['note'])}',
            toD(r['amount']), r['id'] as int),
    ];
    out.sort((x, y) => x.date.compareTo(y.date));
    return out;
  }

  /// Cash the drawer should hold at the end of [upTo]: the last counted
  /// amount plus everything that moved since. Before the very first closing
  /// nobody has counted the drawer, so only [upTo]'s own movements count.
  double cashAt(String upTo) {
    final c = lastClosing;
    final closed = c != null && (c['date'] as String).compareTo(upTo) <= 0;
    final base = closed ? toD(c['counted']) : 0.0;
    final from = closed ? c['date'] as String : dayBefore(upTo);
    return base + cashMoves(from, upTo).fold<double>(0, (s, m) => s + m.amount);
  }

  // ---- تۆماری چالاکی ----
  /// Append one line to the activity log. Nothing ever edits or deletes these.
  void log(String kind, String action, String text, {int? ref, double? amount}) {
    final n = DateTime.now();
    String two(int v) => v.toString().padLeft(2, '0');
    con.execute('INSERT INTO activity(at,kind,action,ref,text,amount,device) VALUES(?,?,?,?,?,?,?)', [
      '${isoDate(n)} ${two(n.hour)}:${two(n.minute)}:${two(n.second)}',
      kind, action, ref, text, amount, _device,
    ]);
  }

  static final String _device = () {
    try {
      return Platform.localHostname;
    } catch (_) {
      return '';
    }
  }();

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
