"""ProxyCommand cho ssh tới máy Colab: `colab ssh --proxy-mode -s <tên>`, nhưng CẤM tự xin máy mới.

Colab CLI tự xin máy mới (mặc định CPU) khi phiên <tên> không còn, ví dụ khi máy vừa bị thu hồi. Engine cờ
biến thể từng gặp đúng việc này (custom_engine/scripts/colab_cells/fz_giu_may.py, 2026-09-26). Ở đây thay hàm tự
xin máy của CLI ngay trong cùng tiến trình, nên không còn khe hở thời gian.

Phải chạy bằng trình Python của chính Colab CLI (bộ điều phối tự tìm, xem colab_may.py).
    python proxy_ssh.py <tên phiên>
"""
import sys

from colab_cli.commands import ssh as _ssh


def _khong_xin(*_a, **_k):
    sys.stderr.write(f"[cv] phien '{sys.argv[1]}' khong con (may da tra / bi thu hoi) -- KHONG tu xin may moi\n")
    raise SystemExit(3)


_ssh._auto_create_session = _khong_xin

from colab_cli.cli import main  # noqa: E402

ten = sys.argv[1]
sys.argv = ["colab", "ssh", "--proxy-mode", "-s", ten]
sys.exit(main())
