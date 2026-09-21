#!/usr/bin/env python3
"""Do toc do suy luan THUAN TUY cua mot mang .onnx qua cac Execution Provider.

Khong MCTS, khong cay, khong gi khac -- chi nap mang va ban tensor ngau nhien.
Muc dich: tach bach "toc do suy luan" khoi "moi thu khac trong engine".

PHAI chay trong tien trinh co LD_LIBRARY_PATH tro toi cuDNN/cuBLAS, neu khong
CUDAExecutionProvider se im lang roi ve CPU. Tren Colab cac thu vien do nam
trong cac goi pip nvidia-* cua torch. Dung scripts/bench_ort.sh de goi cho dung.

    python bench_ort.py <model.onnx> [--board 10] [--providers cuda,trt,cpu]
"""
import argparse
import os
import sys
import time


def onnx_flops(path, board):
    """FLOP moi vi tri, doc thang tu do thi ONNX (khong doan kien truc).

    Mang resnet kieu nay giu nguyen kich thuoc khong gian qua moi conv, nen
    so o = board*board cho moi conv. Trong so nam trong initializer voi shape
    [Cout, Cin, kh, kw].
    """
    import onnx
    m = onnx.load(path)
    init = {i.name: i for i in m.graph.initializer}
    total = 0
    for n in m.graph.node:
        if not (len(n.input) > 1 and n.input[1] in init):
            continue
        w = list(init[n.input[1]].dims)
        if n.op_type == "Conv" and len(w) == 4:
            total += 2 * w[0] * w[1] * w[2] * w[3] * board * board
        elif n.op_type in ("Gemm", "MatMul") and len(w) == 2:
            total += 2 * w[0] * w[1]
    return total


def bench(model, provider, board, batches, gflop, iters, warmup, popts=None):
    import numpy as np
    import onnxruntime as ort

    so = ort.SessionOptions()
    so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    plist = [(provider, popts)] if popts else [provider]
    try:
        sess = ort.InferenceSession(model, so, providers=plist)
    except Exception as e:
        print("  %-28s KHONG KHA DUNG: %s" % (provider, str(e)[:100]))
        return {}
    active = sess.get_providers()
    if provider not in active:
        print("  %-28s KHONG kich hoat duoc -- dang chay %s" % (provider, active))
        print("       (thuong la thieu cuDNN/cuBLAS trong LD_LIBRARY_PATH,")
        print("        hoac onnxruntime-gpu khong khop phien ban CUDA)")
        return {}

    iname = sess.get_inputs()[0].name
    res = {}
    for b in batches:
        x = np.random.rand(b, 226, board, board).astype(np.float32)
        try:
            for _ in range(warmup):
                sess.run(None, {iname: x})
            t0 = time.perf_counter()
            for _ in range(iters):
                sess.run(None, {iname: x})
            dt = (time.perf_counter() - t0) / iters
        except Exception as e:
            print("  %-28s batch=%-4d LOI: %s" % (provider, b, str(e)[:70]))
            continue
        res[b] = b / dt
        print("  %-28s batch=%-4d %9.1f pos/s   %6.2f TFLOP/s"
              % (provider, b, b / dt, b / dt * gflop))
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model")
    ap.add_argument("--board", type=int, default=10)
    ap.add_argument("--providers", default="cuda,trt,cpu")
    ap.add_argument("--iters", type=int, default=30)
    ap.add_argument("--warmup", type=int, default=8)
    ap.add_argument("--trt-cache", default="/content/trt_cache")
    a = ap.parse_args()

    import onnxruntime as ort

    gflop = onnx_flops(a.model, a.board) / 1e9
    print("Mang        : %s" % a.model)
    print("Ban co      : %dx%d" % (a.board, a.board))
    print("FLOP/vi tri : %.3f GFLOP" % gflop)
    print("ORT         : %s" % ort.__version__)
    print("Providers   : %s" % ort.get_available_providers())
    print("LD_LIBRARY_PATH co %d muc" % len(os.environ.get("LD_LIBRARY_PATH", "").split(":")))
    print()

    want = [p.strip() for p in a.providers.split(",")]
    BATCHES = [1, 8, 16, 32, 64, 128, 256]
    out = {}

    if "cuda" in want:
        print("=== CUDAExecutionProvider (dung ngan xep giong engine) ===")
        out["CUDA"] = bench(a.model, "CUDAExecutionProvider", a.board,
                            BATCHES, gflop, a.iters, a.warmup)
        print()

    if "trt" in want:
        os.makedirs(a.trt_cache, exist_ok=True)
        print("=== TensorrtExecutionProvider (fp32, KHONG doi do chinh xac) ===")
        print("    lan dau moi co batch phai bien dich ke hoach: 1-5 phut. Kien nhan.")
        out["TensorRT"] = bench(a.model, "TensorrtExecutionProvider", a.board,
                                [16, 64, 256], gflop, max(10, a.iters // 2), a.warmup,
                                popts={"trt_engine_cache_enable": True,
                                       "trt_engine_cache_path": a.trt_cache,
                                       "trt_fp16_enable": False})
        print()

    if "cpu" in want:
        print("=== CPUExecutionProvider (tham chieu, chi vai co batch) ===")
        out["CPU"] = bench(a.model, "CPUExecutionProvider", a.board,
                           [1, 16], gflop, 5, 2)
        print()

    cuda, trt = out.get("CUDA", {}), out.get("TensorRT", {})
    hdr = "%6s | %14s %8s | %15s %8s | %7s" % (
        "batch", "CUDA EP pos/s", "TFLOP/s", "TensorRT pos/s", "TFLOP/s", "loi")
    print("=" * len(hdr))
    print(hdr)
    print("-" * len(hdr))
    for b in BATCHES:
        c, t = cuda.get(b), trt.get(b)
        cs = ("%14.1f %8.2f" % (c, c * gflop)) if c else ("%14s %8s" % ("-", "-"))
        ts = ("%15.1f %8.2f" % (t, t * gflop)) if t else ("%15s %8s" % ("-", "-"))
        gain = ("%6.2fx" % (t / c)) if (c and t) else ("%6s" % "-")
        print("%6d | %s | %s | %7s" % (b, cs, ts, gain))
    print("=" * len(hdr))
    print()
    print("MOC SO SANH: engine dat ~2200 NN eval/giay = ~2.2 TFLOP/s")
    print("  suy luan thuan CAO HON NHIEU -> engine mat hieu nang o khau dieu phoi")
    print("  xap xi 2200                  -> backend chinh la tran that su")
    print("  cot 'loi' > 1.3x             -> TensorRT dang co gia tri")
    if not cuda:
        print()
        print("!! CUDA EP khong chay duoc -> moi so lieu tren vo nghia.")
        print("   Kiem tra: da goi qua bench_ort.sh chua? onnxruntime-gpu co khop")
        print("   phien ban CUDA cua may khong?")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
