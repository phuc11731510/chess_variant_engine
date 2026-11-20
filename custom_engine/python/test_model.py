"""The transformer (model.py), its losses (train.py) and its ONNX export. Pure Python (the last section also runs the
engine when build/custom_engine.exe exists). Run: python test_model.py   (about 30 seconds)

What it pins down, each of which was added with the transformer and had no test before:
  1. shapes, parameter count, the policy layout (logit index = move type * 100 + square), gradients everywhere;
  2. the relative-position table: one row per (rank offset, file offset), 19 x 19 of them, the same for every pair of
     squares with the same offset;
  3. policy_loss: the mean over the positions that HAVE a policy target (sum / count, not sum / batch size), no NaN
     when a batch has none;
  4. mlh_loss: lc0's formula (both sides / 20, Huber with delta 10 / 20), positions without a target ignored;
  5. compute_losses: the three losses are wired to the right outputs and target columns;
  6. the exported .onnx: one self-contained file (weights inside, no .data), outputs policy / value / mlh, opset the
     engine's ONNX Runtime reads, FP32, any batch size, the same numbers as PyTorch -- by the new exporter AND by the
     legacy one the code falls back to;
  7. lay_mang.suy_kien_truc reads d_model / layers / heads back from a checkpoint;
  8. the engine refuses a network that has no `mlh` output, with a message that says so.
  9. lay_mang.py against a Release that holds only .pt (the Release keeps no .onnx since 2026-11-20): it downloads the
     .pt, converts it, never asks for the .onnx, leaves an existing .onnx alone, exits 10 for a missing generation.
"""
import os
import subprocess
import sys
import tempfile

import numpy as np
import torch
import torch.nn.functional as F

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lay_mang  # noqa: E402
import train as T  # noqa: E402
from model import FairyNet, ExportNet, NUM_PLANES, POLICY_SIZE, POLICY_TYPES, SQUARES  # noqa: E402
from model import _relative_index  # noqa: E402

FAILS = []


def check(ok, what):
    print(("  [ok] " if ok else "  [FAIL] ") + what)
    if not ok:
        FAILS.append(what)


def small_net(seed=0):
    torch.manual_seed(seed)
    return FairyNet(d_model=24, layers=2, heads=3).eval()


def test_shapes_and_layout():
    print("\n[1] shapes, size, policy layout, gradients")
    net = FairyNet()
    n = sum(p.numel() for p in net.parameters())
    check(4.5e6 < n < 5.6e6, f"the default network has {n / 1e6:.2f}M parameters (d_model 192, 10 layers, 6 heads)")
    net = small_net().train()
    x = torch.randn(3, NUM_PLANES, 10, 10)
    pol, val, mlh = net(x)
    check(pol.shape == (3, POLICY_SIZE) and val.shape == (3, 3) and mlh.shape == (3, 1),
          "outputs: policy [B,11500], value [B,3], mlh [B,1]")
    (pol.logsumexp(1).sum() + val.sum() + mlh.sum()).backward()
    missing = [k for k, p in net.named_parameters() if p.grad is None]
    check(not missing, f"every parameter gets a gradient (missing: {missing[:3]})")
    check(float(net.blocks[0].attn.rel_bias.grad.abs().sum()) > 0, "the relative-position table is trained")
    # logit [type * 100 + square] must be the head of THAT square's token (rank * 10 + file)
    net.eval()
    with torch.no_grad():
        pol, _, _ = net(x[:1])
        h = net.embed(x[:1].flatten(2).transpose(1, 2)) + net.pos_embed
        for blk in net.blocks:
            h = blk(h)
        h = net.final_ln(h)
        ok = all(torch.allclose(pol[0, t * 100 + s], net.pol_head(h)[0, s, t], atol=1e-6)
                 for t in (0, 5, 72, 88, POLICY_TYPES - 1) for s in (0, 9, 37, 90, 99))
    check(ok, "policy index = move type * 100 + square (rank * 10 + file) = MoveToNNIndex")
    # a board with one piece moved to another square changes the logits of that square's token most
    with torch.no_grad():
        a = x[:1].clone()
        b = a.clone()
        b[0, :, 4, 4] += 1.0
        pa, _, _ = net(a)
        pb, _, _ = net(b)
        diff = (pa - pb).abs().reshape(POLICY_TYPES, 100).sum(0)
    check(int(diff.argmax()) == 44, "changing square e5 (rank 4, file 4) moves the logits of square 44 the most")


def test_relative_index():
    print("\n[2] relative-position table")
    idx = _relative_index()
    check(idx.shape == (100, 100) and int(idx.min()) == 0 and int(idx.max()) == 19 * 19 - 1,
          "100 x 100 indices into a 19 x 19 table (0 .. 360)")
    check(int(idx.unique().numel()) == 19 * 19, "all 361 offsets occur")
    same = True
    for i, j, k, l in ((0, 11, 55, 66), (3, 3, 99, 99), (20, 3, 77, 60), (5, 94, 10, 99)):
        ri, fi, rj, fj = i // 10, i % 10, j // 10, j % 10
        rk, fk, rl, fl = k // 10, k % 10, l // 10, l % 10
        if (rj - ri, fj - fi) == (rl - rk, fl - fk):
            same &= int(idx[i, j]) == int(idx[k, l])
    check(same and int(idx[0, 11]) == int(idx[55, 66]), "two pairs with the same offset share one table row")
    check(int(idx[0, 11]) != int(idx[11, 0]), "the offset has a direction (a -> b differs from b -> a)")


def _ce_rows(logits, pi):
    """Reference: the masked cross-entropy of each row, in numpy float64."""
    out = []
    for lg, p in zip(logits.double().numpy(), pi.double().numpy()):
        legal = p >= 0
        z = lg[legal] - lg[legal].max()
        logp = z - np.log(np.exp(z).sum())
        out.append(float(-(p[legal] * logp).sum()))
    return np.array(out)


def test_policy_loss_mask():
    print("\n[3] policy_loss over the positions that have a policy target")
    g = torch.Generator().manual_seed(1)
    b = 6
    logits = torch.randn(b, POLICY_SIZE, generator=g)
    pi = torch.full((b, POLICY_SIZE), -1.0)
    for r in range(b):
        legal = torch.randperm(POLICY_SIZE, generator=g)[:30]
        w = torch.rand(30, generator=g)
        pi[r, legal] = w / w.sum()
    ce = _ce_rows(logits, pi)
    has = torch.tensor([1.0, 0.0, 1.0, 1.0, 0.0, 1.0])
    got = T.policy_loss(logits, pi, has).item()
    want = ce[[0, 2, 3, 5]].mean()
    check(abs(got - want) < 1e-5, f"mean over the 4 positions with a target ({got:.5f}, expected {want:.5f})")
    check(abs(got - (ce * has.numpy()).sum() / b) > 1e-3, "NOT the sum divided by the batch size of 6")
    check(abs(T.policy_loss(logits, pi).item() - ce.mean()) < 1e-5, "no mask: the plain mean")
    zero = T.policy_loss(logits, pi, torch.zeros(b))
    check(torch.isfinite(zero).item() and zero.item() == 0.0, "a batch with no policy target gives 0, not NaN")
    # the gradient of the masked-out rows is exactly zero
    lg = logits.clone().requires_grad_(True)
    T.policy_loss(lg, pi, has).backward()
    check(float(lg.grad[1].abs().sum()) == 0.0 and float(lg.grad[4].abs().sum()) == 0.0
          and float(lg.grad[0].abs().sum()) > 0.0, "rows without a target get no gradient")


def test_mlh_loss():
    print("\n[4] mlh_loss: lc0's moves-left Huber loss")
    one = lambda pred, plies: T.mlh_loss(torch.tensor([float(pred)]), torch.tensor([float(plies)])).item()
    check(abs(one(60, 50) - 0.125) < 1e-6, "10 plies off -> 0.5 * (10/20)^2 = 0.125")
    check(abs(one(60, 100) - 0.875) < 1e-6, "40 plies off -> 0.5 * (2.0 - 0.25) = 0.875 (linear above delta)")
    check(one(77, 77) == 0.0, "exact -> 0")
    check(abs(one(40, 50) - one(60, 50)) < 1e-9, "symmetric in the error")
    got = T.mlh_loss(torch.tensor([5.0, 5.0, 60.0]), torch.tensor([0.0, 0.0, 50.0])).item()
    check(abs(got - 0.125) < 1e-6, "positions with plies_left = 0 (not filled in) are left out of the mean")
    check(T.mlh_loss(torch.tensor([5.0]), torch.tensor([0.0])).item() == 0.0, "all unfilled -> 0, not NaN")
    ref = F.huber_loss(torch.tensor([3.0]) / 20, torch.tensor([30.0]) / 20, delta=0.5).item()
    check(abs(one(3, 30) - ref) < 1e-9, "same as torch's Huber on the 1/20-scaled numbers")


def test_compute_losses():
    print("\n[5] compute_losses wires each loss to its output and its target column")
    torch.manual_seed(2)
    b = 5
    pol = torch.randn(b, POLICY_SIZE)
    val_logits = torch.randn(b, 3)
    mlh = torch.rand(b, 1) * 80
    pi = torch.full((b, POLICY_SIZE), -1.0)
    pi[:, :10] = 0.1
    wdl = torch.softmax(torch.randn(b, 3), 1)
    plies = torch.tensor([10.0, 20.0, 0.0, 40.0, 5.0])
    has = torch.tensor([1.0, 1.0, 0.0, 1.0, 0.0])
    val = torch.cat([wdl, plies[:, None], has[:, None]], 1)
    lp, lv, lm = T.compute_losses((pol, val_logits, mlh), pi, val)
    check(abs(lp.item() - T.policy_loss(pol, pi, has).item()) < 1e-6, "policy loss uses column 4 (has_policy)")
    check(abs(lv.item() - T.value_loss(val_logits, wdl).item()) < 1e-6, "value loss uses columns 0..2")
    check(abs(lm.item() - T.mlh_loss(mlh[:, 0], plies).item()) < 1e-6, "mlh loss uses column 3 (plies_left)")


def _run_onnx(path, x):
    import onnxruntime as ort
    sess = ort.InferenceSession(path, providers=["CPUExecutionProvider"])
    return sess.run(["policy", "value", "mlh"], {"input": x})


def test_export():
    print("\n[6] ONNX export: self-contained, three outputs, the engine's opset, FP32, any batch")
    import onnx
    net = small_net(3)
    rng = np.random.default_rng(0)
    with tempfile.TemporaryDirectory() as tmp:
        for name, legacy in (("dynamo", False), ("legacy", True)):
            path = os.path.join(tmp, f"{name}.onnx")
            if legacy:
                exp = ExportNet(net).eval()
                torch.onnx.export(exp, torch.randn(2, NUM_PLANES, 10, 10), path, input_names=["input"],
                                  output_names=["policy", "value", "mlh"],
                                  dynamic_axes={"input": {0: "batch"}, "policy": {0: "batch"},
                                                "value": {0: "batch"}, "mlh": {0: "batch"}},
                                  opset_version=T.ONNX_OPSET, dynamo=False)
            else:
                T.export_onnx(net, path)
            m = onnx.load(path)
            ext = [t.name for t in m.graph.initializer if t.data_location == onnx.TensorProto.EXTERNAL]
            check(not ext and not os.path.exists(path + ".data"), f"{name}: the weights are inside the one .onnx file")
            opset = max(o.version for o in m.opset_import if (o.domain or "ai.onnx") == "ai.onnx")
            check(opset <= 21, f"{name}: opset {opset} <= 21 (what the engine's ONNX Runtime reads)")
            check(all(t.data_type == onnx.TensorProto.FLOAT for t in m.graph.initializer
                      if t.data_type in (onnx.TensorProto.FLOAT, onnx.TensorProto.FLOAT16, onnx.TensorProto.DOUBLE)),
                  f"{name}: FP32 weights only")
            check({o.name for o in m.graph.output} == {"policy", "value", "mlh"} and
                  [i.name for i in m.graph.input] == ["input"], f"{name}: input 'input'; outputs policy, value, mlh")
            ok = True
            for bs in (1, 3, 9):
                x = (rng.random((bs, NUM_PLANES, 10, 10)) < 0.08).astype(np.float32)
                o_pol, o_val, o_mlh = _run_onnx(path, x)
                with torch.no_grad():
                    t_pol, t_val, t_mlh = ExportNet(net)(torch.from_numpy(x))
                ok &= (o_pol.shape == (bs, POLICY_SIZE) and o_mlh.shape == (bs, 1)
                       and np.abs(o_pol - t_pol.numpy()).max() < 1e-4
                       and np.abs(o_val - t_val.numpy()).max() < 1e-5
                       and np.abs(o_mlh - t_mlh.numpy()).max() < 1e-3
                       and np.allclose(o_val.sum(1), 1.0, atol=1e-5))
            check(ok, f"{name}: batch 1, 3 and 9 give PyTorch's numbers; value sums to 1")
        T.verify_onnx(os.path.join(tmp, "dynamo.onnx"), net)    # its own asserts (shapes, names, no .data, opset)
        check(True, "verify_onnx accepts the exported file")


def test_checkpoint_architecture():
    print("\n[7] lay_mang.suy_kien_truc")
    net = FairyNet(d_model=24, layers=2, heads=3)
    check(lay_mang.suy_kien_truc(net.state_dict()) == (24, 2, 3), "d_model, layers, heads are read back from a .pt")
    net2 = FairyNet(d_model=32, layers=4, heads=2)
    check(lay_mang.suy_kien_truc(net2.state_dict()) == (32, 4, 2), "also for another size")


def test_engine_refuses_net_without_mlh():
    print("\n[8] the engine refuses a network without the mlh output")
    exe = os.path.join(HERE, "..", "build", "custom_engine.exe")
    if not os.path.exists(exe):
        print("  [skip] build/custom_engine.exe not found")
        return

    class NoMlh(torch.nn.Module):          # what a network from before the moves-left head exported
        def __init__(self, net):
            super().__init__()
            self.exp = ExportNet(net)

        def forward(self, x):
            policy, value, _ = self.exp(x)
            return policy, value

    net = small_net(4)
    with tempfile.TemporaryDirectory() as tmp:
        bad = os.path.join(tmp, "no_mlh.onnx")
        torch.onnx.export(NoMlh(net).eval(), torch.randn(2, NUM_PLANES, 10, 10), bad, input_names=["input"],
                          output_names=["policy", "value"], dynamic_axes={"input": {0: "batch"}},
                          opset_version=T.ONNX_OPSET, dynamo=False)
        good = os.path.join(tmp, "with_mlh.onnx")
        T.export_onnx(net, good)
        script = "uci\nisready\nquit\n"
        for path, want_ok in ((bad, False), (good, True)):
            r = subprocess.run([exe, "--uci-nn", "--weights", path], input=script, text=True, capture_output=True,
                               cwd=os.path.dirname(exe), timeout=120)
            out = r.stdout + r.stderr
            if want_ok:
                check("readyok" in out and "failed to load backend" not in out, "a network with the mlh output loads")
            else:
                check('no output named "mlh"' in out and "failed to load backend" in out,
                      "a network without mlh is refused, and the message names the missing output")


def test_lay_mang_pt_only_release():
    print("\n[9] lay_mang.py against a Release that holds only .pt")
    import functools
    import http.server
    import threading

    net = small_net(5)
    requested = []

    class Handler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            requested.append(self.path.rsplit("/", 1)[-1])
            super().do_GET()

        def log_message(self, *args):
            pass

    with tempfile.TemporaryDirectory() as tmp:
        rel = os.path.join(tmp, "release")
        work = os.path.join(tmp, "work")
        os.makedirs(rel)
        os.makedirs(work)
        torch.save(net.state_dict(), os.path.join(rel, "gen7.pt"))
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=rel))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        url = f"http://127.0.0.1:{server.server_address[1]}"
        env = dict(os.environ, NO_PROXY="127.0.0.1", no_proxy="127.0.0.1", PYTHONUTF8="1")

        def run(*args):
            r = subprocess.run([sys.executable, os.path.join(HERE, "lay_mang.py"), *args], capture_output=True,
                               text=True, env=env, timeout=300)
            return r.returncode, r.stdout + r.stderr

        try:
            onnx_path = os.path.join(work, "gen7.onnx")
            rc, out = run("onnx", onnx_path, "--rel", url)
            check(rc == 0 and os.path.getsize(onnx_path) > 0, "gen7.onnx is made from the Release's gen7.pt")
            check("gen7.onnx" not in requested and "gen7.pt" in requested,
                  f"the Release is asked for the .pt and NOT for the .onnx (requests: {requested})")
            check(not os.path.exists(onnx_path + ".data") and not os.path.exists(onnx_path + ".dang_chuyen"),
                  "no .data / temporary file left behind")
            x = (np.random.default_rng(1).random((3, NUM_PLANES, 10, 10)) < 0.08).astype(np.float32)
            o_pol, o_val, o_mlh = _run_onnx(onnx_path, x)
            with torch.no_grad():
                t_pol, t_val, t_mlh = ExportNet(net)(torch.from_numpy(x))
            check(np.abs(o_pol - t_pol.numpy()).max() < 1e-4 and np.abs(o_val - t_val.numpy()).max() < 1e-5
                  and np.abs(o_mlh - t_mlh.numpy()).max() < 1e-3, "the converted .onnx computes what the .pt does")
            before = len(requested)
            rc2, _ = run("onnx", onnx_path, "--rel", url)
            check(rc2 == 0 and len(requested) == before, "an .onnx that exists is left alone (no request)")
            os.remove(onnx_path)
            os.remove(os.path.join(work, "gen7.pt"))      # a .pt already on the machine is not downloaded again
            requested.clear()
            rc3, _ = run("onnx", onnx_path, "--rel", url, "--thu-release")
            check(rc3 == 0 and requested[:1] == ["gen7.onnx"] and "gen7.pt" in requested,
                  f"--thu-release asks for the .onnx first, then falls back to the .pt (requests: {requested})")
            rc4, _ = run("onnx", os.path.join(work, "gen9.onnx"), "--rel", url)
            check(rc4 == 10, f"a generation the Release does not have: exit code 10 (got {rc4})")
            os.remove(os.path.join(work, "gen7.pt"))
            rc5, _ = run("pt", os.path.join(work, "gen7.pt"), "--rel", url)
            check(rc5 == 0 and os.path.getsize(os.path.join(work, "gen7.pt")) > 0, "lay_mang.py pt downloads the .pt")
        finally:
            server.shutdown()


def test_fused_export():
    print("\n[10] fused graph (2026-11-20): same FP32 function, fewer and bigger kernels; can be switched off; never loses the export")
    import onnx
    net = FairyNet(d_model=48, layers=3, heads=3).eval()
    rng = np.random.default_rng(1)
    x = (rng.random((5, NUM_PLANES, 10, 10)) < 0.08).astype(np.float32)
    with tempfile.TemporaryDirectory() as tmp:
        fused, plain = os.path.join(tmp, "fused.onnx"), os.path.join(tmp, "plain.onnx")
        T.export_onnx(net, fused)
        os.environ["FZ_ONNX_KHONG_GOP"] = "1"
        try:
            T.export_onnx(net, plain)
        finally:
            del os.environ["FZ_ONNX_KHONG_GOP"]
        ops_f = [n.op_type for n in onnx.load(fused).graph.node]
        ops_p = [n.op_type for n in onnx.load(plain).graph.node]
        check({"SkipLayerNormalization", "BiasGelu"} & set(ops_f) and len(ops_f) < len(ops_p),
              f"the fused graph has fewer nodes ({len(ops_f)} < {len(ops_p)}) and uses the fused operators")
        check(not ({"SkipLayerNormalization", "BiasGelu", "Gelu"} & set(ops_p)),
              "FZ_ONNX_KHONG_GOP=1 keeps the plain graph")
        of, op = _run_onnx(fused, x), _run_onnx(plain, x)
        check(all(np.abs(a - b).max() <= t for a, b, t in zip(of, op, T.FUSE_TOLERANCE)),
              "fused and plain graphs compute the same numbers (to the tolerance)")
        check(not os.path.exists(fused + ".gop") and not os.path.exists(fused + ".data"), "no temporary file is left behind")
        T.verify_onnx(fused, net)           # I/O contract, runtime, and numbers against PyTorch
        check(True, "verify_onnx accepts the fused file")
        # A fused graph that gives other numbers is dropped and the plain file stays (here: a zero tolerance).
        before = open(plain, "rb").read()
        saved = T.FUSE_TOLERANCE
        T.FUSE_TOLERANCE = (-1.0, -1.0, -1.0)
        try:
            kept = T.fuse_onnx(plain, net)
        finally:
            T.FUSE_TOLERANCE = saved
        check(kept is False and open(plain, "rb").read() == before and not os.path.exists(plain + ".gop"),
              "a fused graph outside the tolerance is refused: the plain file is untouched")
        # A failing optimiser keeps the export.
        import onnxruntime.transformers.optimizer as O
        real = O.optimize_model
        O.optimize_model = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))
        try:
            kept2 = T.fuse_onnx(plain, net)
        finally:
            O.optimize_model = real
        check(kept2 is False and open(plain, "rb").read() == before, "an optimiser error keeps the plain export")


def test_fp16_export_guards():
    print("\n[11] FP16 inference graph (2026-11-20): measured by fp16_differences, refused when it cannot be checked, never loses the FP32 file")
    net = FairyNet(d_model=48, layers=2, heads=3).eval()
    # --- the comparison itself: what the search sees (move probabilities), not the raw logits
    rng = np.random.default_rng(5)
    pol = rng.normal(0, 3, (6, POLICY_SIZE)).astype(np.float32)
    val = rng.dirichlet([1, 1, 1], 6).astype(np.float32)
    mlh = rng.uniform(5, 90, (6, 1)).astype(np.float32)
    same = T.fp16_differences((pol, val, mlh), (pol, val, mlh))
    check(same == (0.0, 0.0, 0.0), "identical outputs: no difference")
    near = T.fp16_differences((pol, val, mlh), (pol + 1e-3, val, mlh + 0.01))
    check(near is not None and near[0] < 1e-3 and all(d <= t for d, t in zip(near, T.FP16_TOLERANCE)),
          f"a 1e-3 shift of every logit is a tiny change of the move probabilities (TV {near[0]:.1e}) and passes")
    far = T.fp16_differences((pol, val, mlh), (rng.normal(0, 3, pol.shape).astype(np.float32), val, mlh))
    check(far is not None and far[0] > T.FP16_TOLERANCE[0], "unrelated policies are far apart (TV above the tolerance)")
    bad = pol.copy()
    bad[2, 7] = np.inf
    nan = mlh.copy()
    nan[0, 0] = np.nan
    check(T.fp16_differences((pol, val, mlh), (bad, val, mlh)) is None and T.fp16_differences((pol, val, mlh), (pol, val, nan)) is None,
          "an infinity or a NaN in any output is refused")
    x = T.check_inputs(5, seed=1)
    check(x.shape == (5, NUM_PLANES, 10, 10) and x.dtype == np.float32, "the synthetic check positions have the net's input shape")
    # --- no GPU here (this test runs on the PC): the FP32 file must come back untouched, with the reason printed
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "n.onnx")
        used = T.export_onnx(net, path, fp16=True)
        import onnx
        m = onnx.load(path)
        fp16_w = any(t.data_type == onnx.TensorProto.FLOAT16 for t in m.graph.initializer)
        import onnxruntime as ort
        has_gpu = "CUDAExecutionProvider" in ort.get_available_providers()
        if has_gpu:
            check(used == fp16_w, "on a GPU machine export_onnx(fp16=True) reports whether the FP16 graph was kept")
        else:
            check(used is False and not fp16_w, "without a CUDA provider the FP32 graph is kept and export_onnx says it did not use FP16")
        check(not os.path.exists(path + ".fp16") and not os.path.exists(path + ".gop"), "no temporary file is left behind")
        T.verify_onnx(path, net)
        check(True, "verify_onnx accepts the file either way")
        before = open(path, "rb").read()
        os.environ["FZ_ONNX_FP16"] = "0"
        try:
            path2 = os.path.join(tmp, "n2.onnx")
            used2 = T.export_onnx(net, path2, fp16=True)
        finally:
            del os.environ["FZ_ONNX_FP16"]
        check(used2 is False and not any(t.data_type == onnx.TensorProto.FLOAT16 for t in onnx.load(path2).graph.initializer),
              "FZ_ONNX_FP16=0 forces FP32 even when fp16=True is asked")
        # a conversion that raises keeps the FP32 file (the GPU branch is not reachable here, so force the error path)
        import onnxruntime.transformers.onnx_model as OM
        real = OM.OnnxModel.convert_float_to_float16
        OM.OnnxModel.convert_float_to_float16 = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))
        try:
            kept = T.fp16_onnx(path, net)
        finally:
            OM.OnnxModel.convert_float_to_float16 = real
        check(kept is False and open(path, "rb").read() == before, "a conversion error keeps the FP32 file")
    # --- the attention scale moved onto q does not change the function
    from model import RelativeAttention
    att = RelativeAttention(24, 3).eval()
    xx = torch.randn(2, 100, 24)
    with torch.no_grad():
        got = att(xx)
        b, t, d = xx.shape
        qkv = att.qkv(xx).reshape(b, t, 3, att.heads, att.dh).permute(2, 0, 3, 1, 4)
        ref = torch.softmax(torch.matmul(qkv[0], qkv[1].transpose(-2, -1)) * att.scale + att.rel_bias[:, att.rel_index].unsqueeze(0), -1)
        ref = att.proj(torch.matmul(ref, qkv[2]).transpose(1, 2).reshape(b, t, d))
    check(torch.allclose(got, ref, atol=1e-6), "scaling q before q.k^T gives the same attention as scaling the scores")


def test_attention_fusion():
    print("\n[12] attention fused into one MultiHeadAttention node per layer (2026-11-20): same function, fewer kernels, safe on a miss")
    import shutil
    import onnx
    import onnxruntime as ort
    torch.manual_seed(2)
    net = FairyNet(d_model=96, layers=3, heads=6).eval()
    with torch.no_grad():                      # strong weights and a non-zero positional bias: attention must matter
        for name, p in net.named_parameters():
            if "rel_bias" in name:
                p.copy_(torch.randn_like(p) * 2.0)
            elif p.dim() >= 2:
                p.copy_(torch.randn_like(p) * 0.25)
    x = T.check_inputs(6)
    with tempfile.TemporaryDirectory() as tmp:
        plain, mha = os.path.join(tmp, "p.onnx"), os.path.join(tmp, "m.onnx")
        T.export_onnx(net, plain)
        shutil.copyfile(plain, mha)
        ok = T.fuse_attention_onnx(mha, net)
        n_p, n_m = onnx.load(plain), onnx.load(mha)
        ops = [n.op_type for n in n_m.graph.node]
        check(ok and ops.count("MultiHeadAttention") == 3 and ops.count("Split") == 3,
              "one Split + one MultiHeadAttention per layer (3 layers)")
        check(len(n_m.graph.node) < len(n_p.graph.node) - 20 and ops.count("Softmax") == 1,
              f"the graph has {len(n_p.graph.node) - len(n_m.graph.node)} fewer nodes; only the WDL softmax is left")
        check(any(o.domain == "com.microsoft" for o in n_m.opset_import), "the com.microsoft opset is imported")
        # the ordinary CPU provider can run the node, which lets us compare numbers without a GPU
        ref = ort.InferenceSession(plain, providers=["CPUExecutionProvider"]).run(["policy", "value", "mlh"], {"input": x})
        try:
            out = ort.InferenceSession(mha, providers=["CPUExecutionProvider"]).run(["policy", "value", "mlh"], {"input": x})
            d = [float(np.abs(a - b).max()) for a, b in zip(ref, out)]
            check(max(np.abs(ref[0]).max(), 1.0) > 3 and d[0] < 1e-3 and d[1] < 1e-4 and d[2] < 1e-2,
                  f"same outputs as the ordinary attention (policy logits up to {np.abs(ref[0]).max():.1f}, differences {d[0]:.1e} / {d[1]:.1e} / {d[2]:.1e})")
            # a wrong bias would show: move one bias entry and the outputs must change
            n_bad = onnx.load(mha)
            for t in n_bad.graph.initializer:
                if t.name == "fz_mha_bias_0":
                    arr = onnx.numpy_helper.to_array(t).copy()
                    arr[0, 0, 0, 1] += 5.0
                    t.CopyFrom(onnx.numpy_helper.from_array(arr, t.name))
            bad = os.path.join(tmp, "bad.onnx")
            onnx.save(n_bad, bad)
            out_bad = ort.InferenceSession(bad, providers=["CPUExecutionProvider"]).run(["policy", "value", "mlh"], {"input": x})
            check(np.abs(out_bad[0] - ref[0]).max() > 10 * d[0], "the relative-position bias reaches the output (a changed bias changes it)")
        except Exception as e:     # noqa: BLE001 - a CPU provider without the node: the GPU job checks it
            print(f"  [skip] this onnxruntime cannot run MultiHeadAttention on the CPU: {type(e).__name__}")
        # a graph that is not the exporter's pattern (here: already fused) is left alone and the function says so
        before = open(mha, "rb").read()
        again = T.fuse_attention_onnx(mha, net)
        check(again is False and open(mha, "rb").read() == before, "a graph without the pattern is left untouched (returns False)")


def test_attention_fusion_layout_b():
    print("\n[13] the attention pattern as onnxruntime 1.32 leaves it on a Colab machine (layout B: Reshape -> Gather(axis 2) -> Transpose, bias already a constant)")
    import onnx
    import onnxruntime as ort
    from onnx import helper, numpy_helper, TensorProto
    D, H, N = 24, 3, 100
    dh = D // H
    torch.manual_seed(4)
    net = FairyNet(d_model=D, layers=1, heads=H).eval()
    with torch.no_grad():
        net.blocks[0].attn.rel_bias.copy_(torch.randn_like(net.blocks[0].attn.rel_bias) * 2.0)
    attn = net.blocks[0].attn
    bias = attn.rel_bias.detach()[:, attn.rel_index].unsqueeze(0).float().numpy()

    def c(name, arr):
        return numpy_helper.from_array(np.asarray(arr), name)

    def build(layout_ok=True):
        nodes = [
            helper.make_node("Reshape", ["lin", "shp"], ["view"]),
            helper.make_node("Gather", ["view", "i0"], ["gq"], axis=2),
            helper.make_node("Transpose", ["gq"], ["q"], perm=[0, 2, 1, 3]),
            helper.make_node("Gather", ["view", "i1"], ["gk"], axis=2),
            helper.make_node("Transpose", ["gk"], ["kt"], perm=[0, 2, 3, 1] if layout_ok else [0, 2, 1, 3]),
            helper.make_node("Gather", ["view", "i2"], ["gv"], axis=2),
            helper.make_node("Transpose", ["gv"], ["v"], perm=[0, 2, 1, 3]),
            helper.make_node("Mul", ["q", "scale"], ["qs"]),
            helper.make_node("MatMul", ["qs", "kt"], ["sc"]),
            helper.make_node("Add", ["sc", "bias"], ["sb"]),
            helper.make_node("Softmax", ["sb"], ["p"], axis=-1),
            helper.make_node("MatMul", ["p", "v"], ["o"]),
            helper.make_node("Transpose", ["o"], ["ot"], perm=[0, 2, 1, 3]),
            helper.make_node("Reshape", ["ot", "shp2"], ["out"]),
        ]
        inits = [c("shp", np.array([-1, N, 3, H, dh], dtype=np.int64)), c("shp2", np.array([-1, N, D], dtype=np.int64)),
                 c("i0", np.array(0, dtype=np.int64)), c("i1", np.array(1, dtype=np.int64)), c("i2", np.array(2, dtype=np.int64)),
                 c("scale", np.array(dh ** -0.5, dtype=np.float32)), c("bias", bias)]
        g = helper.make_graph(nodes, "attn_b", [helper.make_tensor_value_info("lin", TensorProto.FLOAT, ["B", N, 3 * D])],
                              [helper.make_tensor_value_info("out", TensorProto.FLOAT, ["B", N, D])], inits)
        return helper.make_model(g, opset_imports=[helper.make_opsetid("", 18)], ir_version=9)

    x = (np.random.default_rng(0).normal(size=(3, N, 3 * D)) * 1.5).astype(np.float32)
    with tempfile.TemporaryDirectory() as tmp:
        p = os.path.join(tmp, "b.onnx")
        onnx.save(build(), p)
        ref = ort.InferenceSession(p, providers=["CPUExecutionProvider"]).run(None, {"lin": x})[0]
        ok = T.fuse_attention_onnx(p, net)
        ops = [n.op_type for n in onnx.load(p).graph.node]
        check(ok and ops == ["Split", "MultiHeadAttention"], f"layout B is recognised and becomes Split + MultiHeadAttention (got {ops})")
        try:
            out = ort.InferenceSession(p, providers=["CPUExecutionProvider"]).run(None, {"lin": x})[0]
            check(float(np.abs(ref - out).max()) < 1e-4 and float(np.abs(ref).max()) > 0.1,
                  f"same attention output as the unfused nodes (max difference {float(np.abs(ref - out).max()):.1e}, output up to {float(np.abs(ref).max()):.2f})")
        except Exception as e:     # noqa: BLE001
            print(f"  [skip] no MultiHeadAttention on this CPU provider: {type(e).__name__}")
        # a wrong transpose in the k branch is not the pattern: the graph must be left alone
        q = os.path.join(tmp, "wrong.onnx")
        onnx.save(build(layout_ok=False), q)
        before = open(q, "rb").read()
        check(T.fuse_attention_onnx(q, net) is False and open(q, "rb").read() == before,
              "a k branch with the wrong permutation is not fused and the file is untouched")


if __name__ == "__main__":
    for fn in (test_shapes_and_layout, test_relative_index, test_policy_loss_mask, test_mlh_loss,
               test_compute_losses, test_export, test_checkpoint_architecture, test_engine_refuses_net_without_mlh,
               test_lay_mang_pt_only_release, test_fused_export, test_fp16_export_guards, test_attention_fusion,
               test_attention_fusion_layout_b):
        fn()
    print("\nRESULT:", "ALL PASS" if not FAILS else f"{len(FAILS)} FAILED: {FAILS}")
    sys.exit(1 if FAILS else 0)
