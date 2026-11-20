"""Build the one-shot GPU benchmark script for `colab run` (see bench_colab_t4_body.py for what it measures).

    python bench_colab_t4_build.py [output.py]        # default: <temp dir>/bench_colab_t4.py
    colab run --gpu T4 <output.py>                    # rents a fresh T4, runs it, releases the VM (Colab CLI 0.7.x)

The output is ONE self-contained file: the python/ files the benchmark needs (model.py, train.py, ...) are zipped and
embedded as base64, so nothing has to be uploaded or cloned first (the Colab machines clone the `main` branch, which
may not have the current python/ files). It measures on whatever torch / onnxruntime the VM has: the dynamo ONNX
export, the .pt -> .onnx conversion time (what lay_mang.py costs each machine each generation), FP32 training steps
by batch size (peak GPU memory too), and ONNX Runtime CUDA inference by batch size (FP32; FP16 only as a reference).
"""
import base64
import io
import os
import subprocess
import sys
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "python")
FILES = ["model.py", "nn_layout.py", "train.py", "dataset.py", "trainingdata_reader.py", "trainingdata_v6.py",
         "run_seed.py", "lay_mang.py", "archive.py"]
FILES = [f for f in FILES if os.path.exists(os.path.join(SRC, f))]


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(tempfile.gettempdir(), "bench_colab_t4.py")
    # the zipped files must import on their own: nothing else from python/ is needed on the VM
    with tempfile.TemporaryDirectory() as tmp:
        for f in FILES:
            with open(os.path.join(SRC, f), "rb") as a, open(os.path.join(tmp, f), "wb") as b:
                b.write(a.read())
        r = subprocess.run([sys.executable, "-c", "import train, lay_mang, model"], cwd=tmp, capture_output=True,
                           text=True, env=dict(os.environ, PYTHONUTF8="1"))
        if r.returncode != 0:
            sys.exit("the embedded python files do not import on their own:\n" + r.stderr[-800:])
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for f in FILES:
            z.write(os.path.join(SRC, f), f)
    with open(os.path.join(HERE, "bench_colab_t4_body.py"), encoding="utf-8") as f:
        body = f.read()
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write('ZIP_B64 = "' + base64.b64encode(buf.getvalue()).decode() + '"\n' + body)
    print(f"wrote {out} ({os.path.getsize(out) / 1024:.0f} KB, files: {', '.join(FILES)})")
    print(f"run it:  colab run --gpu T4 {out}")


if __name__ == "__main__":
    main()
