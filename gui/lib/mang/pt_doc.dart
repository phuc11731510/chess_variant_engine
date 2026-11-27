import 'dart:convert';
import 'dart:typed_data';

import 'package:archive/archive.dart' show ZipDecoder;

/// Một tensor trong tệp `.pt` (state_dict do `torch.save` ghi): chỗ của nó trong một "storage" (tệp thô `data/<khoá>`
/// của gói zip), hình dạng và bước nhảy theo phần tử.
class PtTensor {
  final String storageKey;
  final int storageOffset; // theo phần tử
  final List<int> shape;
  final List<int> stride;
  const PtTensor(this.storageKey, this.storageOffset, this.shape, this.stride);

  int get numel => shape.fold(1, (a, b) => a * b);

  /// Lưu liền theo hàng (như `contiguous()` của PyTorch): bước nhảy của chiều cuối là 1, chiều trước bằng tích các chiều sau.
  bool get isContiguous {
    var want = 1;
    for (var i = shape.length - 1; i >= 0; i--) {
      if (shape[i] != 1 && stride[i] != want) return false;
      want *= shape[i];
    }
    return true;
  }
}

class PtFormatException implements Exception {
  final String message;
  PtFormatException(this.message);
  @override
  String toString() => 'Tệp .pt không đúng dạng: $message';
}

/// State_dict của một tệp `.pt`: tên tensor -> byte float32 (thứ tự hàng, little-endian).
///
/// `torch.save` ghi một gói zip KHÔNG nén: `<gốc>/data.pkl` (pickle mô tả từ điển tên -> tensor), `<gốc>/data/<khoá>`
/// (byte thô của từng storage), `<gốc>/byteorder`. Bộ đọc pickle ở đây chỉ hiểu đúng các lệnh và ĐÚNG BA tên toàn cục mà
/// một state_dict cần (`collections.OrderedDict`, `torch._utils._rebuild_tensor_v2`, `torch.FloatStorage`): gặp gì khác
/// thì báo lỗi, không bao giờ "chạy" thứ trong tệp như `pickle` của Python.
class PtStateDict {
  final Map<String, PtTensor> tensors;
  final Map<String, Uint8List> _storages;
  PtStateDict._(this.tensors, this._storages);

  factory PtStateDict.decode(Uint8List bytes) {
    final arch = ZipDecoder().decodeBytes(bytes);
    final files = <String, Uint8List>{};
    for (final f in arch.files) {
      if (f.isFile) files[f.name] = f.readBytes() ?? Uint8List(0);
    }
    final pkl = files.keys.where((n) => n.endsWith('/data.pkl') || n == 'data.pkl').toList();
    if (pkl.length != 1) throw PtFormatException('cần đúng một data.pkl, thấy ${pkl.length}');
    final root = pkl.single.substring(0, pkl.single.length - 'data.pkl'.length); // '' hoặc '<gốc>/'
    final order = files['${root}byteorder'];
    if (order != null && ascii.decode(order).trim() != 'little') {
      throw PtFormatException('byteorder ${ascii.decode(order).trim()} (chỉ đọc little-endian)');
    }
    final obj = _Unpickler(files[pkl.single]!).load();
    if (obj is! Map) throw PtFormatException('data.pkl không phải từ điển tên -> tensor');
    final tensors = <String, PtTensor>{};
    final storages = <String, Uint8List>{};
    obj.forEach((k, v) {
      if (k is! String || v is! PtTensor) throw PtFormatException('mục $k không phải tensor');
      tensors[k] = v;
      final data = files['${root}data/${v.storageKey}'];
      if (data == null) throw PtFormatException('thiếu storage ${v.storageKey} của $k');
      storages[v.storageKey] = data;
    });
    return PtStateDict._(tensors, storages);
  }

  /// Byte float32 của tensor [name] (một khung nhìn, không chép). Tensor phải liền theo hàng.
  Uint8List bytesOf(String name) {
    final t = tensors[name]!;
    if (!t.isContiguous) throw PtFormatException('$name không liền theo hàng (stride ${t.stride})');
    final s = _storages[t.storageKey]!;
    final start = t.storageOffset * 4, len = t.numel * 4;
    if (start + len > s.length) throw PtFormatException('$name vượt quá storage ${t.storageKey}');
    return Uint8List.sublistView(s, start, start + len);
  }
}

class _Global {
  final String module, name;
  const _Global(this.module, this.name);
  String get full => '$module.$name';
}

class _StorageRef {
  final String key;
  const _StorageRef(this.key);
}

class _Mark {
  const _Mark();
}

/// Bộ đọc pickle tối thiểu cho state_dict của PyTorch (giao thức 2..4, các lệnh `torch.save` dùng).
class _Unpickler {
  final Uint8List b;
  final ByteData _bd;
  int _p = 0;
  final List<Object?> _st = [];
  final Map<int, Object?> _memo = {};
  static const _mark = _Mark();
  static const _allowed = {'collections.OrderedDict', 'torch._utils._rebuild_tensor_v2', 'torch.FloatStorage'};

  _Unpickler(this.b) : _bd = ByteData.sublistView(b);

  int _u8() => b[_p++];
  int _u16() { final v = _bd.getUint16(_p, Endian.little); _p += 2; return v; }
  int _u32() { final v = _bd.getUint32(_p, Endian.little); _p += 4; return v; }
  int _i32() { final v = _bd.getInt32(_p, Endian.little); _p += 4; return v; }
  String _utf8(int n) { final s = utf8.decode(Uint8List.sublistView(b, _p, _p + n)); _p += n; return s; }
  String _line() { final e = b.indexOf(10, _p); if (e < 0) throw PtFormatException('GLOBAL thiếu xuống dòng'); final s = ascii.decode(b.sublist(_p, e)); _p = e + 1; return s; }

  List<Object?> _popMark() {
    final i = _st.lastIndexOf(_mark);
    if (i < 0) throw PtFormatException('thiếu MARK');
    final items = _st.sublist(i + 1);
    _st.removeRange(i, _st.length);
    return items;
  }

  Object? _pop() => _st.removeLast();

  Object? load() {
    while (_p < b.length) {
      final op = _u8();
      switch (op) {
        case 0x80: _u8(); // PROTO
        case 0x95: _p += 8; // FRAME (giao thức 4)
        case 0x7d: _st.add(<Object?, Object?>{}); // EMPTY_DICT '}'
        case 0x5d: _st.add(<Object?>[]); // EMPTY_LIST ']'
        case 0x29: _st.add(const <Object?>[]); // EMPTY_TUPLE ')'
        case 0x28: _st.add(_mark); // MARK '('
        case 0x71: _memo[_u8()] = _st.last; // BINPUT 'q'
        case 0x72: _memo[_u32()] = _st.last; // LONG_BINPUT 'r'
        case 0x94: _memo[_memo.length] = _st.last; // MEMOIZE
        case 0x68: _st.add(_memo[_u8()]); // BINGET 'h'
        case 0x6a: _st.add(_memo[_u32()]); // LONG_BINGET 'j'
        case 0x58: _st.add(_utf8(_u32())); // BINUNICODE 'X'
        case 0x8c: _st.add(_utf8(_u8())); // SHORT_BINUNICODE
        case 0x4b: _st.add(_u8()); // BININT1 'K'
        case 0x4d: _st.add(_u16()); // BININT2 'M'
        case 0x4a: _st.add(_i32()); // BININT 'J'
        case 0x8a: // LONG1
          final n = _u8();
          var v = 0;
          for (var i = n - 1; i >= 0; i--) { v = (v << 8) | b[_p + i]; }
          if (n > 0 && b[_p + n - 1] >= 0x80) v -= 1 << (8 * n);
          _p += n;
          _st.add(v);
        case 0x47: _st.add(_bd.getFloat64(_p, Endian.big)); _p += 8; // BINFLOAT 'G'
        case 0x4e: _st.add(null); // NONE 'N'
        case 0x88: _st.add(true); // NEWTRUE
        case 0x89: _st.add(false); // NEWFALSE
        case 0x74: _st.add(List<Object?>.unmodifiable(_popMark())); // TUPLE 't'
        case 0x85: _st.add(List<Object?>.unmodifiable([_pop()])); // TUPLE1
        case 0x86: final y = _pop(), x = _pop(); _st.add(List<Object?>.unmodifiable([x, y])); // TUPLE2
        case 0x87: final z = _pop(), y = _pop(), x = _pop(); _st.add(List<Object?>.unmodifiable([x, y, z])); // TUPLE3
        case 0x63: // GLOBAL 'c'
          final g = _Global(_line(), _line());
          if (!_allowed.contains(g.full)) throw PtFormatException('tên toàn cục không cho phép: ${g.full}');
          _st.add(g);
        case 0x93: // STACK_GLOBAL
          final name = _pop(), mod = _pop();
          final g = _Global('$mod', '$name');
          if (!_allowed.contains(g.full)) throw PtFormatException('tên toàn cục không cho phép: ${g.full}');
          _st.add(g);
        case 0x51: _st.add(_persistent(_pop())); // BINPERSID 'Q'
        case 0x52: final args = _pop(), fn = _pop(); _st.add(_reduce(fn, args)); // REDUCE 'R'
        case 0x73: final v = _pop(), k = _pop(); (_st.last as Map)[k] = v; // SETITEM 's'
        case 0x75: // SETITEMS 'u'
          final items = _popMark();
          final m = _st.last as Map;
          for (var i = 0; i + 1 < items.length; i += 2) { m[items[i]] = items[i + 1]; }
        case 0x62: _pop(); // BUILD 'b': trạng thái phụ (_metadata của state_dict) -> bỏ qua
        case 0x2e: return _pop(); // STOP '.'
        default:
          throw PtFormatException('lệnh pickle 0x${op.toRadixString(16)} ở byte ${_p - 1} chưa hỗ trợ');
      }
    }
    throw PtFormatException('hết tệp mà chưa gặp STOP');
  }

  Object _persistent(Object? pid) {
    // ('storage', torch.FloatStorage, '<khoá>', 'cpu', <số phần tử>)
    if (pid is List && pid.length >= 5 && pid[0] == 'storage' && pid[1] is _Global) {
      final g = pid[1] as _Global;
      if (g.full != 'torch.FloatStorage') throw PtFormatException('storage ${g.full} (chỉ đọc float32)');
      return _StorageRef('${pid[2]}');
    }
    throw PtFormatException('persistent id lạ: $pid');
  }

  Object? _reduce(Object? fn, Object? args) {
    if (fn is! _Global || args is! List) throw PtFormatException('REDUCE lạ');
    switch (fn.full) {
      case 'collections.OrderedDict':
        return <Object?, Object?>{};
      case 'torch._utils._rebuild_tensor_v2':
        final s = args[0], off = args[1], size = args[2], stride = args[3];
        if (s is! _StorageRef || off is! int || size is! List || stride is! List) {
          throw PtFormatException('_rebuild_tensor_v2 với đối số lạ');
        }
        return PtTensor(s.key, off, size.cast<int>(), stride.cast<int>());
    }
    throw PtFormatException('không gọi được ${fn.full}');
  }
}
