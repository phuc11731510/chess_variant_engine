"""Bundle self-play games into one .zip (Store) for fast Drive transfer (plan 5.3).

Self-play writes thousands of tiny .gz files; uploading them one-by-one makes
Google Drive throttle the transfer. This packs them into a SINGLE .zip using
ZIP_STORED (no extra compression — the .gz payloads are already compressed, so
re-deflating only wastes CPU and barely shrinks anything) and can unpack it back.

The training side can read a bundle directly (no unpack needed): train.py
accepts a .zip path or a dir containing .zip via dataset.FairyDataset.

Examples:
  # pack every game under a generation dir into one bundle
  python archive.py pack games_gen0 --out games_gen0.zip
  # pack a rolling window of several generations
  python archive.py pack games_gen0 games_gen1 --out g0_1.zip
  # inspect / restore
  python archive.py list games_gen0.zip
  python archive.py unpack games_gen0.zip --dest restored/
  # then either train directly on the bundle, or on the restored dir:
  python train.py --data games_gen0.zip --epochs 10 --out model.onnx
"""

import argparse
import glob
import os
import zipfile


def _gather(sources, exts=(".gz", ".bin")):
    """Expand `sources` (dirs and/or globs) to a sorted, de-duplicated file list."""
    files = []
    for s in sources:
        if os.path.isdir(s):
            for root, _dirs, names in os.walk(s):
                for n in names:
                    if n.endswith(exts):
                        files.append(os.path.join(root, n))
        else:
            files += [g for g in glob.glob(s) if g.endswith(exts)]
    return sorted(set(os.path.normpath(f) for f in files))


def _human(n):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.1f}{unit}"
        n /= 1024


def pack(args):
    files = _gather(args.sources)
    if not files:
        raise SystemExit(f"[archive] no .gz/.bin files under: {args.sources}")
    # arcnames relative to a common base so the gen-dir structure is preserved
    # (e.g. gen0/game_3.gz) and `unpack` restores the same layout.
    base = args.base or (os.path.dirname(os.path.commonpath(files)) if len(files) > 1
                         else os.path.dirname(files[0]))
    total_in = 0
    with zipfile.ZipFile(args.out, "w", compression=zipfile.ZIP_STORED,
                         allowZip64=True) as zf:
        for f in files:
            arc = os.path.relpath(f, base)
            zf.write(f, arcname=arc)
            total_in += os.path.getsize(f)
    out_size = os.path.getsize(args.out)
    print(f"[archive] packed {len(files)} files ({_human(total_in)}) -> "
          f"{args.out} ({_human(out_size)}, STORE)")


def unpack(args):
    os.makedirs(args.dest, exist_ok=True)
    with zipfile.ZipFile(args.zip) as zf:
        members = [m for m in zf.namelist() if not m.endswith("/")]
        zf.extractall(args.dest)
    print(f"[archive] unpacked {len(members)} files from {args.zip} -> {args.dest}")


def list_cmd(args):
    with zipfile.ZipFile(args.zip) as zf:
        infos = [i for i in zf.infolist() if not i.is_dir()]
        total = sum(i.file_size for i in infos)
        for i in infos[: args.limit]:
            print(f"  {i.filename:40s} {_human(i.file_size):>9s}")
        if len(infos) > args.limit:
            print(f"  ... and {len(infos) - args.limit} more")
        comp = {i.compress_type for i in infos}
        kind = "STORE" if comp == {zipfile.ZIP_STORED} else f"mixed{comp}"
        print(f"[archive] {len(infos)} files, {_human(total)} uncompressed, {kind}")


def main():
    ap = argparse.ArgumentParser(description="Bundle/unbundle self-play .gz games (5.3).")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("pack", help="bundle .gz/.bin files into one .zip (Store)")
    p.add_argument("sources", nargs="+", help="dirs and/or globs to bundle")
    p.add_argument("--out", required=True, help="output .zip path")
    p.add_argument("--base", default=None,
                   help="root for arcnames (default: common parent of inputs)")
    p.set_defaults(func=pack)

    p = sub.add_parser("unpack", help="extract a bundle back to a directory")
    p.add_argument("zip")
    p.add_argument("--dest", required=True, help="destination directory")
    p.set_defaults(func=unpack)

    p = sub.add_parser("list", help="show bundle contents")
    p.add_argument("zip")
    p.add_argument("--limit", type=int, default=20)
    p.set_defaults(func=list_cmd)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
