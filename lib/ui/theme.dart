// ڕەنگەکان و شێوازی گشتی (تاریک / ڕووناک).
import 'package:material_ui/material_ui.dart';

@immutable
class Palette extends ThemeExtension<Palette> {
  final bool dark;
  final Color bg, side, card, cardHi, field, border, borderHi, line;
  final Color text, title, muted, faint;
  final Color gold, goldHi, goldHover, goldPress, onGold;
  final Color btn, btnHover;
  final Color green, red, blue, violet, orange;

  const Palette({
    required this.dark,
    required this.bg, required this.side, required this.card, required this.cardHi,
    required this.field, required this.border, required this.borderHi, required this.line,
    required this.text, required this.title, required this.muted, required this.faint,
    required this.gold, required this.goldHi, required this.goldHover, required this.goldPress,
    required this.onGold, required this.btn, required this.btnHover,
    required this.green, required this.red, required this.blue, required this.violet, required this.orange,
  });

  static const darkP = Palette(
    dark: true,
    bg: Color(0xFF0E1117), side: Color(0xFF0A0D12), card: Color(0xFF161B24), cardHi: Color(0xFF1B212C),
    field: Color(0xFF0F131A), border: Color(0xFF252C38), borderHi: Color(0xFF3B4556), line: Color(0xFF1E2530),
    text: Color(0xFFDFE3EA), title: Color(0xFFF6F8FB), muted: Color(0xFF8D97A8), faint: Color(0xFF667082),
    gold: Color(0xFFE2B84F), goldHi: Color(0xFFEFCB70), goldHover: Color(0xFFEDC864),
    goldPress: Color(0xFFC99F3A), onGold: Color(0xFF1A1503),
    btn: Color(0xFF1D2430), btnHover: Color(0xFF273040),
    green: Color(0xFF47C79B), red: Color(0xFFF0797F), blue: Color(0xFF6CA6FF),
    violet: Color(0xFFA890F2), orange: Color(0xFFF3A566),
  );

  static const lightP = Palette(
    dark: false,
    bg: Color(0xFFF2F4F8), side: Color(0xFFFFFFFF), card: Color(0xFFFFFFFF), cardHi: Color(0xFFFAFBFD),
    field: Color(0xFFFFFFFF), border: Color(0xFFE1E6EE), borderHi: Color(0xFFC3CCD9), line: Color(0xFFECEFF4),
    text: Color(0xFF2B3441), title: Color(0xFF111823), muted: Color(0xFF687385), faint: Color(0xFF98A2B1),
    gold: Color(0xFFDDB246), goldHi: Color(0xFF94700F), goldHover: Color(0xFFE6BE58),
    goldPress: Color(0xFFC99D33), onGold: Color(0xFF1F1903),
    btn: Color(0xFFFFFFFF), btnHover: Color(0xFFF4F6FA),
    green: Color(0xFF1C9468), red: Color(0xFFD2414C), blue: Color(0xFF2C6FCB),
    violet: Color(0xFF6C4EC4), orange: Color(0xFFC76B27),
  );

  /// A quiet tint of [c] that sits on a card (pills, icon tiles).
  Color soft(Color c, [double t = .15]) => Color.lerp(card, c, t)!;

  @override
  Palette copyWith() => this;

  @override
  Palette lerp(Palette? other, double t) => t < .5 ? this : (other ?? this);
}

extension PaletteX on BuildContext {
  Palette get pal => Theme.of(this).extension<Palette>()!;
}

const fontFamily = 'Segoe UI';

ThemeData buildTheme(Palette c) {
  final r9 = BorderRadius.circular(9);
  OutlineInputBorder ob(Color col, [double w = 1]) =>
      OutlineInputBorder(borderRadius: r9, borderSide: BorderSide(color: col, width: w));
  final base = ThemeData(
    useMaterial3: true,
    brightness: c.dark ? Brightness.dark : Brightness.light,
    fontFamily: fontFamily,
    fontFamilyFallback: const ['Tahoma', 'Arial'],
  );
  return base.copyWith(
    extensions: [c],
    scaffoldBackgroundColor: c.bg,
    canvasColor: c.card,
    dividerColor: c.line,
    colorScheme: base.colorScheme.copyWith(
      primary: c.gold, onPrimary: c.onGold, secondary: c.gold, onSecondary: c.onGold,
      surface: c.card, onSurface: c.text, error: c.red, outline: c.border,
      surfaceContainerHighest: c.btn, surfaceContainerHigh: c.card, surfaceContainer: c.card,
      surfaceContainerLow: c.card, surfaceContainerLowest: c.field,
    ),
    textTheme: base.textTheme.apply(bodyColor: c.text, displayColor: c.title, fontFamily: fontFamily),
    textSelectionTheme: TextSelectionThemeData(
      cursorColor: c.gold, selectionColor: c.gold.withValues(alpha: .35), selectionHandleColor: c.gold),
    inputDecorationTheme: InputDecorationTheme(
      isDense: true,
      filled: true,
      fillColor: c.field,
      contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 13),
      hintStyle: TextStyle(color: c.faint, fontSize: 14),
      border: ob(c.border), enabledBorder: ob(c.border), disabledBorder: ob(c.line),
      focusedBorder: ob(c.gold, 1.4), errorBorder: ob(c.red), focusedErrorBorder: ob(c.red, 1.4),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        backgroundColor: c.gold, foregroundColor: c.onGold,
        disabledBackgroundColor: c.btn, disabledForegroundColor: c.faint,
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        shape: RoundedRectangleBorder(borderRadius: r9),
        textStyle: const TextStyle(fontFamily: fontFamily, fontWeight: FontWeight.w700, fontSize: 14),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        backgroundColor: c.btn, foregroundColor: c.text,
        side: BorderSide(color: c.border),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        shape: RoundedRectangleBorder(borderRadius: r9),
        textStyle: const TextStyle(fontFamily: fontFamily, fontWeight: FontWeight.w600, fontSize: 14),
      ),
    ),
    textButtonTheme: TextButtonThemeData(
      style: TextButton.styleFrom(
        foregroundColor: c.muted,
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        shape: RoundedRectangleBorder(borderRadius: r9),
        textStyle: const TextStyle(fontFamily: fontFamily, fontWeight: FontWeight.w600, fontSize: 14),
      ),
    ),
    dialogTheme: DialogThemeData(
      backgroundColor: c.bg,
      surfaceTintColor: Colors.transparent,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14), side: BorderSide(color: c.border)),
      titleTextStyle: TextStyle(fontFamily: fontFamily, fontSize: 18, fontWeight: FontWeight.w700, color: c.title),
      contentTextStyle: TextStyle(fontFamily: fontFamily, fontSize: 14.5, color: c.text),
    ),
    tooltipTheme: TooltipThemeData(
      decoration: BoxDecoration(color: c.card, borderRadius: BorderRadius.circular(6), border: Border.all(color: c.borderHi)),
      textStyle: TextStyle(color: c.text, fontSize: 12.5, fontFamily: fontFamily),
      waitDuration: const Duration(milliseconds: 400),
    ),
    snackBarTheme: SnackBarThemeData(
      backgroundColor: c.title,
      contentTextStyle: TextStyle(color: c.bg, fontWeight: FontWeight.w700, fontFamily: fontFamily, fontSize: 13.5),
      behavior: SnackBarBehavior.floating,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(11)),
      width: 420,
    ),
    scrollbarTheme: ScrollbarThemeData(
      thumbColor: WidgetStatePropertyAll(c.borderHi.withValues(alpha: .7)),
      radius: const Radius.circular(2),
      thickness: const WidgetStatePropertyAll(6),
    ),
    checkboxTheme: CheckboxThemeData(
      fillColor: WidgetStateProperty.resolveWith((s) => s.contains(WidgetState.selected) ? c.gold : Colors.transparent),
      checkColor: WidgetStatePropertyAll(c.onGold),
      side: BorderSide(color: c.borderHi, width: 1.4),
    ),
    datePickerTheme: DatePickerThemeData(
      backgroundColor: c.card,
      surfaceTintColor: Colors.transparent,
      headerBackgroundColor: c.gold,
      headerForegroundColor: c.onGold,
    ),
    popupMenuTheme: PopupMenuThemeData(
      color: c.card,
      surfaceTintColor: Colors.transparent,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10), side: BorderSide(color: c.borderHi)),
    ),
  );
}
