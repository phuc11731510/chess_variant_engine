// Ảnh quân cờ: bộ quân của GUI phải khớp biến thể của engine, mỗi quân hai màu có ảnh thật,
// và ảnh phải là SVG đã làm phẳng (flutter_svg không đọc khối <style> / class).
// Thêm ảnh mới: chép vào fairyzero_piece_svg/ rồi chạy `dart run tool/flatten_svgs.dart`.

import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

import 'package:fairyzero_gui/domain/board_state.dart';
import 'package:fairyzero_gui/ui/piece_assets.dart';

void main() {
  test('bộ quân khớp biến thể: 12 loại, không còn Archbishop / Chancellor / Amazon', () {
    expect(PieceAssets.pieceTypes.toSet(), {
      'p', 'n', 'b', 'r', 'q', 'k', 'm', 'v', 'y', 's', 'c', 'g', //
    });
    for (final gone in ['a', 'e', 'h']) {
      expect(PieceAssets.pieceTypes, isNot(contains(gone)));
    }
  });

  test('mỗi loại quân, hai màu: có tệp ảnh, không còn <style> / class', () {
    for (final t in PieceAssets.pieceTypes) {
      for (final letter in [t, t.toUpperCase()]) {
        final path = PieceAssets.assetFor(letter);
        final f = File(path);
        expect(f.existsSync(), true, reason: '$letter -> $path không có');
        final text = f.readAsStringSync();
        expect(text.contains('<style'), false, reason: '$path còn khối <style>: chạy flatten_svgs');
        expect(text.contains('class='), false, reason: '$path còn class=: chạy flatten_svgs');
      }
    }
  });

  test('không có tệp ảnh quân mồ côi (quân đã bỏ hoặc sai tên)', () {
    final expected = <String>{};
    for (final t in PieceAssets.pieceTypes) {
      expected.add(PieceAssets.assetFor(t).split('/').last);
      expected.add(PieceAssets.assetFor(t.toUpperCase()).split('/').last);
    }
    final colored = RegExp(r'^(white|black)-.*\.svg$');
    for (final e in Directory('assets/pieces').listSync()) {
      final name = e.uri.pathSegments.last;
      if (!colored.hasMatch(name)) continue; // *-promotion.svg: ảnh dùng riêng, không phải quân trên bàn
      expect(expected, contains(name), reason: '$name không thuộc quân nào của biến thể');
    }
  });

  test('Hoàng gia dùng ảnh king riêng, Centaur dùng ảnh general, Grasshopper và Pháo có ảnh', () {
    expect(PieceAssets.assetFor('K'), 'assets/pieces/white-king-K.svg');
    expect(PieceAssets.assetFor('k'), 'assets/pieces/black-king-k.svg');
    expect(PieceAssets.assetFor('M'), 'assets/pieces/white-general-M.svg');
    expect(PieceAssets.assetFor('g'), 'assets/pieces/black-grasshoper-g.svg');
    expect(PieceAssets.assetFor('C'), 'assets/pieces/white-cannon-C.svg');
    expect(PieceAssets.isRoyal('K'), true);
    expect(PieceAssets.isRoyal('k'), true);
    expect(PieceAssets.isRoyal('m'), false);
  });

  test('thế xuất phát chỉ dùng quân có ảnh', () {
    final placement = kVariantStartposFen.split(' ').first;
    final letters = placement.split('').where((c) => RegExp(r'[A-Za-z]').hasMatch(c)).toSet();
    for (final l in letters) {
      expect(PieceAssets.pieceTypes, contains(l.toLowerCase()), reason: 'quân $l không có ảnh');
    }
  });
}
