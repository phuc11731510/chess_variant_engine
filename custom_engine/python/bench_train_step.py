"""Đo tốc độ một bước huấn luyện trên GPU (Colab T4), cùng cấu hình ô 07.

    python bench_train_step.py --data games_gen1.zip [--max-records 200000] [--variants ...]

Phần 1 (đề xuất P1) -- bước bị chặn bởi GPU hay bởi CPU dựng plane:
  A. GPU thuần  -- batch nằm sẵn trên GPU, lặp forward+backward+optimizer.
  B. dữ liệu thuần -- chỉ lặp DataLoader (CPU dựng plane), với 0/2/4 worker.
  C. vòng thật  -- như train.py: DataLoader -> .to(cuda) -> bước GPU.
Phần 2 (đề xuất P4) -- các cách làm bước GPU nhanh hơn, từng cách và kết hợp:
  item      -- như train.py: .item() mỗi bước (CPU chờ GPU xong từng bước)
  noitem    -- cộng dồn loss trên GPU, không chờ (P4a)
  cl        -- channels_last (P4b);  compile -- torch.compile (P4c)
  Mọi phương án: cùng trọng số khởi đầu, cùng các batch -> so quỹ đạo loss với 'item'.
  'item' chạy hai lần: độ lệch giữa hai lần = mức không tất định sẵn có của cuDNN.
"""

import argparse
import os
import sys
import time

import torch
from torch.utils.data import DataLoader

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from model import FairyNet  # noqa: E402
from dataset import FairyDataset  # noqa: E402
from train import policy_loss, value_loss  # noqa: E402

DEV = "cuda"


def make_step(net, opt, scaler, cl):
    def step(x, pi, val):
        if cl:
            x = x.contiguous(memory_format=torch.channels_last)
        with torch.autocast(device_type=DEV):
            p, v = net(x)
            loss = policy_loss(p, pi) + value_loss(v, val)
        scaler.scale(loss).backward()
        scaler.step(opt)
        scaler.update()
        opt.zero_grad(set_to_none=True)
        return loss.detach()
    return step


def build(args, cl, comp):
    torch.manual_seed(1234)                      # cùng trọng số khởi đầu cho mọi phương án
    net = FairyNet(channels=args.channels, blocks=args.blocks).to(DEV)
    if cl:
        net = net.to(memory_format=torch.channels_last)
    opt = torch.optim.AdamW(net.parameters(), lr=1e-3, weight_decay=1e-4)
    scaler = torch.amp.GradScaler("cuda")
    model = torch.compile(net, mode=comp) if comp else net
    return make_step(model, opt, scaler, cl)


def run_variant(args, name, batches, cl, comp, item):
    """-> (ms/bước, giây bước đầu, [loss mỗi bước])"""
    step = build(args, cl, comp)
    torch.cuda.synchronize()
    t = time.perf_counter()
    losses = [step(*batches[0])]
    torch.cuda.synchronize()
    first = time.perf_counter() - t              # gồm thời gian biên dịch nếu compile
    for i in range(1, args.warmup):
        losses.append(step(*batches[i % len(batches)]))
    torch.cuda.synchronize()
    t = time.perf_counter()
    acc = torch.zeros((), device=DEV)
    for i in range(args.warmup, args.warmup + args.steps):
        loss = step(*batches[i % len(batches)])
        losses.append(loss)
        if item:
            loss.item()                          # như train.py
        else:
            acc += loss                          # P4a: không chờ GPU
    torch.cuda.synchronize()
    ms = (time.perf_counter() - t) / args.steps * 1000
    return ms, first, [float(v) for v in losses]


def part_p4(args, ds):
    k = args.n_batches
    dl = DataLoader(ds, batch_size=args.batch, shuffle=True, generator=torch.Generator().manual_seed(7))
    it = iter(dl)
    batches = [tuple(t.to(DEV) for t in next(it)) for _ in range(k)]
    print(f"\n=== P4: {k} batch cố định trên GPU, {args.warmup} bước khởi động + {args.steps} bước đo ===")
    specs = {
        "item":          (False, None, True),
        "item_lan2":     (False, None, True),
        "noitem":        (False, None, False),
        "cl":            (True, None, True),
        "cl+noitem":     (True, None, False),
        "compile":       (False, "default", True),
        "cl+compile":    (True, "default", False),
        "cl+compile_ro": (True, "reduce-overhead", False),

    }
    wanted = args.variants.split(",") if args.variants else list(specs)
    res = {}
    for name in wanted:
        cl, comp, item = specs[name]
        try:
            res[name] = run_variant(args, name, batches, cl, comp, item)
        except Exception as e:  # noqa: BLE001
            print(f"  {name:14s} LỖI: {type(e).__name__}: {str(e)[:300]}")
            continue
        ms, first, _ = res[name]
        print(f"  {name:14s} {ms:7.1f} ms/bước   bước đầu {first:6.1f} s", flush=True)
        torch.cuda.empty_cache()
    if "item" in res:
        base = res["item"][2]
        print("\n  Độ lệch loss so với 'item' (cùng trọng số, cùng batch):")
        for name, (ms, _, ls) in res.items():
            if name == "item":
                continue
            d = [abs(a - b) for a, b in zip(ls, base)]
            print(f"  {name:14s} bước 1: {d[0]:.2e}   lớn nhất: {max(d):.2e}   "
                  f"cuối: {d[-1]:.2e}   (loss cuối {ls[-1]:.4f} vs {base[-1]:.4f})"
                  f"   nhanh hơn {100 * (1 - ms / res['item'][0]):+.1f}%")
    return res


def part_p1(args, ds, cl, comp, item, label):
    step = build(args, cl, comp)
    x, pi, val = next(iter(DataLoader(ds, batch_size=args.batch, shuffle=True)))
    x, pi, val = x.to(DEV), pi.to(DEV), val.to(DEV)
    for _ in range(args.warmup):
        step(x, pi, val)
    torch.cuda.synchronize()
    t = time.perf_counter()
    for _ in range(args.steps):
        loss = step(x, pi, val)
        if item:
            loss.item()
    torch.cuda.synchronize()
    a = (time.perf_counter() - t) / args.steps * 1000
    print(f"\n=== vòng thật [{label}] ===\nA. GPU thuần: {a:7.1f} ms/bước")
    for w in (int(s) for s in args.workers.split(",")):
        dl = DataLoader(ds, batch_size=args.batch, shuffle=True, num_workers=w,
                        pin_memory=True, persistent_workers=(w > 0))
        it = iter(dl)
        for _ in range(3):               # khởi động worker
            next(it)
        t = time.perf_counter()
        for _ in range(args.steps):
            next(it)
        b = (time.perf_counter() - t) / args.steps * 1000
        torch.cuda.synchronize()
        t = time.perf_counter()
        for _ in range(args.steps):
            xb, pb, vb = next(it)
            loss = step(xb.to(DEV, non_blocking=True), pb.to(DEV, non_blocking=True),
                        vb.to(DEV, non_blocking=True))
            if item:
                loss.item()
        torch.cuda.synchronize()
        c = (time.perf_counter() - t) / args.steps * 1000
        print(f"workers={w}:  B. dữ liệu thuần {b:7.1f} ms/bước   C. vòng thật {c:7.1f} ms/bước"
              f"   -> GPU rảnh ~{max(0.0, 1 - a / c) * 100:.0f}% thời gian", flush=True)
        del it, dl


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--batch", type=int, default=1024)
    ap.add_argument("--max-records", type=int, default=200000)
    ap.add_argument("--steps", type=int, default=40)
    ap.add_argument("--warmup", type=int, default=5)
    ap.add_argument("--n-batches", type=int, default=8)
    ap.add_argument("--channels", type=int, default=144)
    ap.add_argument("--blocks", type=int, default=12)
    ap.add_argument("--workers", default="2")
    ap.add_argument("--variants", default="", help="phần P4: danh sách phương án (mặc định: tất cả)")
    ap.add_argument("--real", default="item,cl+noitem,cl+compile",
                    help="phần P1: các phương án đo vòng thật với DataLoader ('' = bỏ)")
    args = ap.parse_args()
    print(f"[bench] {torch.cuda.get_device_name(0)}  cpu_count={os.cpu_count()}  "
          f"torch={torch.__version__}")
    t = time.perf_counter()
    ds = FairyDataset(args.data, q_ratio=0.2, cache=True, sparse=True,
                      max_records=args.max_records)
    print(f"[bench] nạp {len(ds)} bản ghi: {time.perf_counter() - t:.1f} s")
    t = time.perf_counter()
    for i in range(2000):
        ds[i]
    print(f"[bench] __getitem__: {(time.perf_counter() - t) / 2000 * 1e6:.0f} µs/thế cờ")

    part_p4(args, ds)
    real = {"item": (False, None, True), "cl+noitem": (True, None, False),
            "cl+compile": (True, "default", False)}
    for name in filter(None, args.real.split(",")):
        part_p1(args, ds, *real[name], label=name)


if __name__ == "__main__":
    main()
