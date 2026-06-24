// Tool một-lần: làm phẳng CSS (<style> + class) trong các SVG quân cờ thành
// thuộc tính inline (fill/opacity/...), vì flutter_svg KHÔNG xử lý khối <style>.
//
// Đọc: fairyzero_piece_svg/*.svg  ->  Ghi: assets/pieces/*.svg
// Chạy (từ gui\): dart run tool/flatten_svgs.dart

// ignore_for_file: avoid_print

import 'dart:io';

import 'package:xml/xml.dart';

void main() {
  final srcDir = Directory('fairyzero_piece_svg');
  final outDir = Directory('assets/pieces')..createSync(recursive: true);
  if (!srcDir.existsSync()) {
    print('Khong thay ${srcDir.path}');
    exit(1);
  }

  var n = 0;
  for (final entity in srcDir.listSync()) {
    if (entity is! File || !entity.path.toLowerCase().endsWith('.svg')) continue;
    final doc = XmlDocument.parse(entity.readAsStringSync());

    // 1. Gom luật CSS từ mọi <style> rồi xóa <style>.
    final css = <String, Map<String, String>>{};
    for (final styleEl in doc.findAllElements('style').toList()) {
      _parseCss(styleEl.innerText, css);
      styleEl.parent?.children.remove(styleEl);
    }

    // 2. Áp luật vào mọi phần tử có class -> thuộc tính inline.
    for (final el in doc.descendantElements) {
      final cls = el.getAttribute('class');
      if (cls == null) continue;
      final props = <String, String>{};
      for (final c in cls.trim().split(RegExp(r'\s+'))) {
        final m = css[c];
        if (m != null) props.addAll(m);
      }
      props.forEach((k, v) {
        if (el.getAttribute(k) == null) el.setAttribute(k, v);
      });
      el.removeAttribute('class');
    }

    final name = entity.uri.pathSegments.last;
    File('${outDir.path}/$name').writeAsStringSync(doc.toXmlString());
    n++;
    print('flattened $name');
  }
  print('Xong: $n file -> ${outDir.path}');
}

/// Parse text CSS đơn giản: ".a,.b{fill:#fff;opacity:0.2}" -> map class->props.
void _parseCss(String text, Map<String, Map<String, String>> out) {
  text = text.replaceAll(RegExp(r'/\*.*?\*/', dotAll: true), '');
  for (final rule in text.split('}')) {
    final brace = rule.indexOf('{');
    if (brace < 0) continue;
    final selectors = rule.substring(0, brace);
    final body = rule.substring(brace + 1);

    final props = <String, String>{};
    for (final decl in body.split(';')) {
      final colon = decl.indexOf(':');
      if (colon < 0) continue;
      props[decl.substring(0, colon).trim()] = decl.substring(colon + 1).trim();
    }
    for (final sel in selectors.split(',')) {
      final s = sel.trim();
      if (s.startsWith('.')) {
        out.putIfAbsent(s.substring(1), () => {}).addAll(props);
      }
    }
  }
}
