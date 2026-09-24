"""fz_nhan_may.py -- giu / NHAN LAI may Colab cua phien menu fz (chay tren DIEN THOAI).

Van de: Colab CLI XOA phien khoi sessions.json va TAT tien trinh giu may (keep-alive) moi khi
`colab exec` gap loi co chu "404"/"401" (colab_cli/utils.py is_terminal_error -> prune_session).
Loi do xay ra ca khi MAY VAN SONG, vd kernel Jupyter cua may chet / khoi dong lai: kernel_id luu
trong sessions.json tra 404. O chay nen cua menu la tien trinh rieng nen van chay, nhung khong
con ai giu may -> Colab thu hoi may vi idle -> mat /content (van, zip).

Tep nay dung lai phien tu danh sach may cua tai khoan (tun/m/assignments: endpoint + url + token
MOI), khong gan kernel cu (lan exec sau tu mo kernel moi), roi bat lai keep-alive -- dung nhu
`colab new` lam, chi khong xin may moi. Moi lan `kiem`, ghi endpoint cua phien vao
~/.config/colab-cli/fz_may_<ten>.txt de `cuu` biet dung may nao (khong nhan nham may khac).

  python ~/fz_nhan_may.py kiem <ten>     # phien con? keep-alive chet -> bat lai; lam moi token
  python ~/fz_nhan_may.py cuu <ten>      # phien bi xoa ma may (endpoint da ghi) con -> nhan lai
  python ~/fz_nhan_may.py nhan <ten> <endpoint>   # nhan may <endpoint> lam phien <ten>
  python ~/fz_nhan_may.py liet_ke        # may dang giu: endpoint, GPU, ten tren dien thoai
Ma thoat: 0 = phien dung duoc, 1 = khong (may mat / khong co), 2 = loi mang / dang nhap.
"""
import inspect
import os
import sys

try:
    from colab_cli.common import state
    from colab_cli.state import SessionState
    from colab_cli.commands.session import spawn_keep_alive
except ImportError as e:
    sys.exit(f"[!] Colab CLI thieu thanh phan: {e}")

LUU = os.path.expanduser("~/.config/colab-cli/fz_may_{}.txt")


def may_dang_giu():
    """{endpoint: ListedAssignment} -- None neu khong hoi duoc (mang / dang nhap)."""
    try:
        return {a.endpoint: a for a in state.client.list_assignments()}
    except Exception as e:  # noqa: BLE001
        print(f"[!] Khong hoi duoc danh sach may: {e}")
        return None


def keep_alive_song(s):
    pid = s.keep_alive_pid
    if not pid:
        return False
    try:
        return b"keep-alive" in open(f"/proc/{pid}/cmdline", "rb").read()
    except OSError:
        return False


def bat_keep_alive(s):
    try:
        state.client.keep_alive_assignment(s.endpoint)  # bao ngay mot lan
    except Exception as e:  # noqa: BLE001 -- tien trinh nen se thu lai
        print(f"[!] keep-alive lan dau loi (tien trinh nen se thu lai): {e}")
    kw = {}
    ts = inspect.signature(spawn_keep_alive).parameters
    if "auth_provider" in ts:
        kw["auth_provider"] = state.auth_provider
    if "config_path" in ts:
        kw["config_path"] = state.config_path
    s.keep_alive_pid = spawn_keep_alive(s.endpoint, s.name, **kw)
    state.store.add(s)


def ghi_endpoint(ten, endpoint):
    with open(LUU.format(ten), "w") as f:
        f.write(endpoint + "\n")


def nhan(ten, endpoint, ds=None):
    ds = may_dang_giu() if ds is None else ds
    if ds is None:
        return 2
    a = ds.get(endpoint)
    if a is None:
        print(f"[!] Tai khoan khong con giu may {endpoint} (da bi thu hoi).")
        return 1
    s = SessionState(
        name=ten,
        token=a.runtime_proxy_info.token,
        url=a.runtime_proxy_info.url,
        endpoint=a.endpoint,
        variant=a.variant.name,
        accelerator=getattr(a.accelerator, "value", str(a.accelerator)),
        machine_shape=a.machine_shape.name,
    )
    state.store.add(s)          # truoc khi bat keep-alive (no kiem phien ton tai)
    bat_keep_alive(s)
    ghi_endpoint(ten, endpoint)
    state.history.log_event(ten, "session_created", {"endpoint": endpoint, "fz": "nhan_lai"})
    print(f"[da nhan lai] may {endpoint} ({s.accelerator}) = phien '{ten}', keep-alive pid {s.keep_alive_pid}")
    return 0


def kiem(ten):
    s = state.store.get(ten)
    if s is None:
        return cuu(ten)
    ds = may_dang_giu()
    if ds is None:
        return 2
    a = ds.get(s.endpoint)
    if a is None:
        print(f"[!] May cua phien '{ten}' ({s.endpoint}) khong con -- Colab da thu hoi.")
        return 1
    ghi_endpoint(ten, s.endpoint)
    doi = False
    if a.runtime_proxy_info.token != s.token or a.runtime_proxy_info.url != s.url:
        s.token, s.url, doi = a.runtime_proxy_info.token, a.runtime_proxy_info.url, True
        state.store.add(s)
    if not keep_alive_song(s):
        bat_keep_alive(s)
        print(f"[!] keep-alive cua phien '{ten}' da chet -> bat lai (pid {s.keep_alive_pid})")
    elif doi:
        print(f"[lam moi] token phien '{ten}'")
    return 0


def cuu(ten):
    """Phien <ten> bi xoa: may da ghi (fz_may_<ten>.txt) con giu -> nhan lai."""
    if state.store.get(ten) is not None:
        return kiem(ten)
    try:
        endpoint = open(LUU.format(ten)).read().strip()
    except FileNotFoundError:
        print(f"[!] Khong co phien '{ten}' va chua ghi may nao cua no.")
        return 1
    ds = may_dang_giu()
    if ds is None:
        return 2
    if endpoint not in ds:
        print(f"[!] Phien '{ten}' da mat va may {endpoint} cung khong con.")
        return 1
    print(f"[!] Colab CLI da xoa phien '{ten}' (tat keep-alive) nhung may {endpoint} VAN SONG -- nhan lai.")
    return nhan(ten, endpoint, ds)


def liet_ke():
    ds = may_dang_giu()
    if ds is None:
        return 2
    ten = {}
    for t in ("fz",) + tuple(sys.argv[2:]):
        s = state.store.get(t)
        if s:
            ten[s.endpoint] = t
    for e, a in ds.items():
        print(f"{e} {getattr(a.accelerator, 'value', a.accelerator)} {ten.get(e, '?')}")
    return 0


if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) == 2 and a[0] in ("kiem", "cuu"):
        sys.exit({"kiem": kiem, "cuu": cuu}[a[0]](a[1]))
    if len(a) == 3 and a[0] == "nhan":
        sys.exit(nhan(a[1], a[2]))
    if a and a[0] == "liet_ke":
        sys.exit(liet_ke())
    sys.exit(__doc__)
