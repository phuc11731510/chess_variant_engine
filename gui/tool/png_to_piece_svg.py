# -*- coding: utf-8 -*-
"""Đổi ảnh quân cờ PNG (nền trắng, tranh phẳng) thành SVG nhiều màu cho GUI.

Dùng khi có ảnh quân mới dạng PNG/JPG. Kết quả: SVG đã "phẳng" (không <style>/class), nền trong suốt,
nằm trong khung viewBox 0 0 180 180 như mọi ảnh quân khác (cao/rộng tối đa --box, căn giữa, đáy ở y=160).

  pip install vtracer pillow numpy scipy
  python tool/png_to_piece_svg.py cannon-white-C.png fairyzero_piece_svg/white-cannon-C.svg c
  python tool/png_to_piece_svg.py cannon-black-c.png fairyzero_piece_svg/black-cannon-c.svg c
  (rồi chép cả hai tệp vào assets/pieces/ — hoặc chạy `dart run tool/flatten_svgs.dart` rồi xem git status)

Các bước: (1) tách phần nền trắng nối với mép ảnh thành trong suốt (vùng trắng nằm trong viền quân được giữ);
(2) viền răng cưa ngoài cùng lấy màu nét viền bên cạnh để khỏi có quầng sáng; (3) vtracer: tô màu chồng lớp,
đường cong spline, nhiều tông (color_precision 7, layer_difference 8); (4) bọc vào khung 180x180.
Tham số --precision / --layer / --speckle chỉnh độ chi tiết (tăng precision, giảm layer = nhiều tông hơn, tệp to hơn).
"""
import argparse
import re

import numpy as np
import vtracer
from PIL import Image
from scipy import ndimage as ndi


def prepare(src, dst_png):
    """Ghi PNG đã tách nền + làm sạch viền; trả về khung bao (x0, x1, y0, y1) của quân."""
    a = np.array(Image.open(src).convert("RGBA"))
    rgb = a[..., :3].astype(np.int16)
    alpha = a[..., 3]
    candidate = ((rgb.min(axis=2) >= 222) & (alpha > 0)) | (alpha == 0)
    labels, _ = ndi.label(candidate)
    border = np.unique(np.concatenate([labels[0], labels[-1], labels[:, 0], labels[:, -1]]))
    border = border[border != 0]
    background = np.isin(labels, border)
    foreground = ~background

    dist = ndi.distance_transform_edt(foreground)
    interior = foreground & (dist > 4)
    nearest = ndi.distance_transform_edt(~interior, return_distances=False, return_indices=True)
    fixed = a.copy()
    fringe = foreground & ~interior
    fixed[fringe, :3] = a[nearest[0][fringe], nearest[1][fringe], :3]
    fixed[..., 3] = np.where(foreground, 255, 0)
    fixed[background, :3] = 0
    Image.fromarray(fixed, "RGBA").save(dst_png)

    ys, xs = np.where(foreground)
    return xs.min(), xs.max() + 1, ys.min(), ys.max() + 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("png", help="ảnh nguồn")
    ap.add_argument("svg", help="SVG đầu ra, vd fairyzero_piece_svg/white-cannon-C.svg")
    ap.add_argument("title", help="ký tự quân (c, g, ...), ghi vào <title>")
    ap.add_argument("--box", type=float, default=144.0, help="cạnh lớn nhất của quân trong khung 180 (mặc định 144)")
    ap.add_argument("--bottom", type=float, default=160.0, help="toạ độ y của đáy quân (mặc định 160)")
    ap.add_argument("--precision", type=int, default=7, help="vtracer color_precision (mặc định 7)")
    ap.add_argument("--layer", type=int, default=8, help="vtracer layer_difference (mặc định 8)")
    ap.add_argument("--speckle", type=int, default=6, help="vtracer filter_speckle (mặc định 6)")
    args = ap.parse_args()

    prepared = args.svg + ".prep.png"
    raw = args.svg + ".raw.svg"
    x0, x1, y0, y1 = prepare(args.png, prepared)
    vtracer.convert_image_to_svg_py(
        prepared, raw,
        colormode="color", hierarchical="stacked", mode="spline",
        filter_speckle=args.speckle, color_precision=args.precision, layer_difference=args.layer,
        corner_threshold=60, length_threshold=4.0, max_iterations=10,
        splice_threshold=45, path_precision=2,
    )
    paths = re.findall(r"<path .*?/>", open(raw, encoding="utf-8").read(), flags=re.S)
    scale = args.box / max(x1 - x0, y1 - y0)
    tx = 90.0 - scale * (x0 + x1) / 2.0
    ty = args.bottom - scale * y1
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 180 180" width="180" height="180">'
        f"<title>{args.title}</title>"
        f'<g transform="translate({tx:.3f} {ty:.3f}) scale({scale:.6f})">{"".join(paths)}</g></svg>\n'
    )
    open(args.svg, "w", encoding="utf-8").write(svg)
    print(f"{args.svg}: {len(paths)} đường, {len(svg) // 1024} KB (tệp trung gian: {prepared}, {raw} — xoá được)")


if __name__ == "__main__":
    main()
