// Đọc các dòng engine trả cho màn phân tích (lib/engine/phan_tich.dart). Các dòng mẫu là đúng chữ engine in ra
// (custom_engine.exe --uci-nn, mạng gen201 dựng từ khung, thế xuất phát, 400 lượt).
import 'package:fairyzero_gui/engine/phan_tich.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('nneval policy', () {
    final r = DanhGiaTho.parse('nneval q 0.114377 d 0.00122047 m 154.23 policy c3c5 0.07669 g3g4 0.07433 e3e5 0.06735')!;
    expect(r.q, closeTo(0.114377, 1e-9));
    expect(r.d, closeTo(0.00122047, 1e-9));
    expect(r.m, closeTo(154.23, 1e-9));
    expect(r.policy.keys.toList(), ['c3c5', 'g3g4', 'e3e5']);
    expect(r.policy['g3g4'], closeTo(0.07433, 1e-9));
  });

  test('nneval cũ (không policy) và nneval none', () {
    final r = DanhGiaTho.parse('nneval q 0.1 d 0.2')!;
    expect(r.policy, isEmpty);
    expect(DanhGiaTho.parse('nneval none'), isNull);
  });

  test('tree', () {
    final n = NutCay.parse(['h2f4'], const [
      'treenode N 32 Q -0.0687 D 0.0015 M 149.3',
      'treechild g8g7 N 4 P 0.0831 Q -0.0313 D 0.0013',
      'treechild c8c6 N 4 P 0.0735 Q -0.0419 D 0.0018 T',
      'treechild a9a8 N 0 P 0.0010 Q -0.0687 D 0.0015',
      'treeend',
    ]);
    expect(n.n, 32);
    expect(n.q, closeTo(-0.0687, 1e-9));
    expect(n.children.map((c) => c.move).toList(), ['g8g7', 'c8c6', 'a9a8']);
    expect(n.children[1].terminal, isTrue);
    expect(n.children[0].terminal, isFalse);
    expect(n.children[2].n, 0);
  });

  test('tree lỗi', () {
    expect(() => NutCay.parse(['a1a1'], const ['treeerror nut chua mo: a1a1']), throwsStateError);
  });

  test('lệnh position', () {
    expect(PhanTich.positionCmd('X w - - 0 1', const []), 'position fen X w - - 0 1');
    expect(PhanTich.positionCmd('X w - - 0 1', const ['e2e3', 'f9f8']), 'position fen X w - - 0 1 moves e2e3 f9f8');
  });
}
