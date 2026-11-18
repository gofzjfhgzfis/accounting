// زمانی ڕووکار: کوردی، لە ڕاستەوە بۆ چەپ.
//
// Flutter وەرگێڕانی کوردی بۆ دوگمەکانی خۆی نییە (بۆ نموونە ڕۆژژمێر)،
// بۆیە ئەو چەند دەقەی بەکاردێن لێرە وەرگێڕدراون.
import 'package:cupertino_ui/cupertino_ui.dart' show CupertinoLocalizations, DefaultCupertinoLocalizations;
import 'package:material_ui/material_ui.dart';

class KuMaterialLocalizations extends DefaultMaterialLocalizations {
  const KuMaterialLocalizations();
  @override
  String get okButtonLabel => 'باشە';
  @override
  String get cancelButtonLabel => 'پاشگەزبوونەوە';
  @override
  String get closeButtonLabel => 'داخستن';
  @override
  String get datePickerHelpText => 'بەروار هەڵبژێرە';
  @override
  String get dateInputLabel => 'بەروار';
  @override
  String get dateHelpText => 'yyyy/mm/dd';
  @override
  String get inputDateModeButtonLabel => 'نووسینی بەروار';
  @override
  String get calendarModeButtonLabel => 'ڕۆژژمێر';
  @override
  String get invalidDateFormatLabel => 'بەروارەکە هەڵەیە';
  @override
  String get dateOutOfRangeLabel => 'لە دەرەوەی ماوەکەیە';
  @override
  String get selectYearSemanticsLabel => 'هەڵبژاردنی ساڵ';
  @override
  String get copyButtonLabel => 'کۆپی';
  @override
  String get cutButtonLabel => 'بڕین';
  @override
  String get pasteButtonLabel => 'لکاندن';
  @override
  String get selectAllButtonLabel => 'هەمووی';
}

class _MaterialDelegate extends LocalizationsDelegate<MaterialLocalizations> {
  const _MaterialDelegate();
  @override
  bool isSupported(Locale l) => true;
  @override
  Future<MaterialLocalizations> load(Locale l) async => const KuMaterialLocalizations();
  @override
  bool shouldReload(_MaterialDelegate old) => false;
}

class _RtlWidgets extends DefaultWidgetsLocalizations {
  const _RtlWidgets();
  @override
  TextDirection get textDirection => TextDirection.rtl;
}

class _WidgetsDelegate extends LocalizationsDelegate<WidgetsLocalizations> {
  const _WidgetsDelegate();
  @override
  bool isSupported(Locale l) => true;
  @override
  Future<WidgetsLocalizations> load(Locale l) async => const _RtlWidgets();
  @override
  bool shouldReload(_WidgetsDelegate old) => false;
}

class _CupertinoDelegate extends LocalizationsDelegate<CupertinoLocalizations> {
  const _CupertinoDelegate();
  @override
  bool isSupported(Locale l) => true;
  @override
  Future<CupertinoLocalizations> load(Locale l) async => const DefaultCupertinoLocalizations();
  @override
  bool shouldReload(_CupertinoDelegate old) => false;
}

const kuDelegates = <LocalizationsDelegate<dynamic>>[
  _MaterialDelegate(),
  _WidgetsDelegate(),
  _CupertinoDelegate(),
];
