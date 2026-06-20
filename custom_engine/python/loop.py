"""T7 — AlphaZero outer loop: self-play -> train -> new model -> repeat.

Portable across Windows (CPU) and Colab (GPU) via --engine + --provider. Each
generation: (1) self-play with the current model, (2) train (warm-start from the
previous generation's weights) on a ROLLING WINDOW of the last --window-gens
generations of games (8.2.8), producing the next model, (3) optionally an ARENA
of the new model vs the previous one.

Layout under --workdir:
    models/model_gen{N}.onnx + model_gen{N}.pt
    games/gen{N}/game_*.gz

Examples:
  Windows (CPU):
    python python/loop.py --engine build/custom_engine.exe --gens 3 \
        --games-per-gen 40 --visits 64 --window-gens 3 --epochs 8 \
        --provider cpu --parallel 6 --eval-games 10
  Colab (GPU):
    python python/loop.py --engine build-linux/custom_engine --gens 10 \
        --games-per-gen 1000 --visits 200 --window-gens 4 --epochs 20 \
        --provider cuda --fixed-batch 32 --parallel 2 --eval-games 40
"""

import argparse
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def run(cmd):
    print("[loop] $ " + " ".join(str(c) for c in cmd), flush=True)
    # utf-8 stdio so torch/onnx unicode prints never crash on a Windows cp1252 console.
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    subprocess.run([str(c) for c in cmd], check=True, env=env)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", required=True, help="path to custom_engine binary")
    ap.add_argument("--workdir", default="loop_run")
    ap.add_argument("--gens", type=int, default=3)
    ap.add_argument("--start-gen", type=int, default=0)
    ap.add_argument("--games-per-gen", type=int, default=50)
    ap.add_argument("--visits", type=int, default=64)
    ap.add_argument("--max-moves", type=int, default=80)
    ap.add_argument("--temp-cutoff", type=int, default=12)
    ap.add_argument("--window-gens", type=int, default=3,
                    help="train on the last K generations (rolling window, 8.2.8)")
    ap.add_argument("--epochs", type=int, default=8)
    ap.add_argument("--batch", type=int, default=128)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--q-ratio", type=float, default=0.2)
    ap.add_argument("--downsample", type=float, default=1.0)
    ap.add_argument("--diff-focus", action="store_true")
    ap.add_argument("--provider", default="cpu", choices=["cpu", "cuda"])
    ap.add_argument("--parallel", type=int, default=4)
    ap.add_argument("--backend-threads", type=int, default=1)
    ap.add_argument("--fixed-batch", type=int, default=16)
    ap.add_argument("--eval-games", type=int, default=0,
                    help="arena games (new gen vs previous); 0 = skip")
    # Self-play search hyperparameters (passed through to the engine).
    ap.add_argument("--noise-epsilon", type=float, default=None)
    ap.add_argument("--noise-alpha", type=float, default=None)
    ap.add_argument("--cpuct", type=float, default=None)
    ap.add_argument("--policy-temp", type=float, default=None)
    ap.add_argument("--start-fen", default=None, help="FEN or opening-book file (diverse openings)")
    # Early resignation (plan A5; passed through to the engine self-play).
    ap.add_argument("--resign-threshold", type=float, default=None,
                    help="best_q<=this for N moves -> resign; <=-1 disables (default off)")
    ap.add_argument("--resign-consecutive", type=int, default=None)
    ap.add_argument("--no-resign-frac", type=float, default=None,
                    help="fraction of games with resign disabled (learn to defend)")
    # Training hyperparameters (passed through to train.py).
    ap.add_argument("--amp", action="store_true",
                    help="FP16 mixed-precision training (auto-on when --provider cuda)")
    ap.add_argument("--dense-cache", action="store_true",
                    help="use dense (high-RAM) dataset cache instead of the default sparse")
    ap.add_argument("--weight-decay", type=float, default=None)
    ap.add_argument("--value-weight", type=float, default=None)
    ap.add_argument("--df-slope", type=float, default=None)
    ap.add_argument("--df-kld-w", type=float, default=None)
    ap.add_argument("--df-min", type=float, default=None)
    ap.add_argument("--swa-start-frac", type=float, default=None)
    # T8.3 training extras (passed through to train.py).
    ap.add_argument("--optimizer", default=None, choices=[None, "adamw", "sgd", "nadam"])
    ap.add_argument("--grad-clip", type=float, default=None)
    ap.add_argument("--warmup-steps", type=int, default=None)
    ap.add_argument("--lr-values", default=None)
    ap.add_argument("--lr-boundaries", default=None)
    ap.add_argument("--policy-weight", type=float, default=None)
    ap.add_argument("--seed", type=int, default=None)
    args = ap.parse_args()

    models = os.path.join(args.workdir, "models")
    games = os.path.join(args.workdir, "games")
    os.makedirs(models, exist_ok=True)
    os.makedirs(games, exist_ok=True)
    py = sys.executable

    def onnx(n): return os.path.join(models, f"model_gen{n}.onnx")
    def pt(n):   return os.path.join(models, f"model_gen{n}.pt")
    def gdir(n): return os.path.join(games, f"gen{n}")

    g0 = args.start_gen
    # gen-0 bootstrap seed (canonical SE-ResNet) if not present.
    if not os.path.exists(onnx(g0)):
        run([py, os.path.join(HERE, "make_seed.py"), "--out", onnx(g0)])

    for gen in range(g0, g0 + args.gens):
        print(f"\n========================= GENERATION {gen} =========================")

        # 1. self-play with the current model.
        sp = [args.engine, "--selfplay", "--games", args.games_per_gen,
              "--visits", args.visits, "--max-moves", args.max_moves,
              "--temp-cutoff", args.temp_cutoff, "--parallel", args.parallel,
              "--weights", onnx(gen), "--out", gdir(gen)]
        if args.provider == "cuda":
            sp += ["--provider", "cuda", "--fixed-batch", args.fixed_batch]
        else:
            sp += ["--backend-threads", args.backend_threads]
        for flag, val in [("--noise-epsilon", args.noise_epsilon), ("--noise-alpha", args.noise_alpha),
                          ("--cpuct", args.cpuct), ("--policy-temp", args.policy_temp),
                          ("--start-fen", args.start_fen),
                          ("--resign-threshold", args.resign_threshold),
                          ("--resign-consecutive", args.resign_consecutive),
                          ("--no-resign-frac", args.no_resign_frac)]:
            if val is not None:
                sp += [flag, val]
        run(sp)

        # 2. rolling window = the last `window_gens` generation dirs (FIFO).
        lo = max(g0, gen - args.window_gens + 1)
        window = ",".join(gdir(k) for k in range(lo, gen + 1) if os.path.isdir(gdir(k)))
        print(f"[loop] rolling window = generations {lo}..{gen}")

        # 3. train (warm-start from this gen's weights) -> next gen.
        tr = [py, os.path.join(HERE, "train.py"), "--data", window,
              "--epochs", args.epochs, "--batch", args.batch, "--lr", args.lr,
              "--q-ratio", args.q_ratio, "--downsample", args.downsample,
              "--init-from", pt(gen), "--out", onnx(gen + 1)]
        if args.diff_focus:
            tr += ["--diff-focus"]
        if args.dense_cache:
            tr += ["--dense-cache"]
        if args.provider == "cuda":
            tr += ["--pin-memory"]
            # FP16 mixed precision is a GPU-only win (5.3); enable on cuda unless
            # the user already passed --amp explicitly.
            tr += ["--amp"]
        elif args.amp:
            tr += ["--amp"]
        for flag, val in [("--weight-decay", args.weight_decay), ("--value-weight", args.value_weight),
                          ("--df-slope", args.df_slope), ("--df-kld-w", args.df_kld_w),
                          ("--df-min", args.df_min), ("--swa-start-frac", args.swa_start_frac),
                          ("--optimizer", args.optimizer), ("--grad-clip", args.grad_clip),
                          ("--warmup-steps", args.warmup_steps), ("--lr-values", args.lr_values),
                          ("--lr-boundaries", args.lr_boundaries), ("--policy-weight", args.policy_weight),
                          ("--seed", args.seed)]:
            if val is not None:
                tr += [flag, val]
        run(tr)

        # 4. arena: does the new generation beat the previous one?
        if args.eval_games > 0:
            ar = [args.engine, "--arena", "--model-a", onnx(gen + 1),
                  "--model-b", onnx(gen), "--games", args.eval_games,
                  "--visits", args.visits, "--max-moves", args.max_moves, "--temp-cutoff", 6]
            if args.provider == "cuda":
                ar += ["--provider", "cuda", "--fixed-batch", args.fixed_batch]
            run(ar)

    print(f"\n[loop] DONE. Generations {g0}..{g0 + args.gens}. "
          f"Final model: {onnx(g0 + args.gens)}")


if __name__ == "__main__":
    main()
