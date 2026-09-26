"""fz_giu_may.py -- GIU MAY Colab khoi bi thu hoi vi "ngoi khong", chay tren DIEN THOAI.

Do 2026-09-26 (Colab CLI 0.7.4, may CPU, moi cach mot may, xem HUONG_DAN_TERMUX.md muc 10):
  - khong lam gi / tien trinh ghi tep moi phut ............ bi thu hoi ~10 phut sau khi xin
  - GET tun/m/<may>/keep-alive/ moi 60 giay (cach CLI <= 0.7.2 giu may) ... VAN bi thu hoi ~10 phut
  - kernel ban (mot khoi lenh dai) / CPU 100% qua ssh ... bi thu hoi ~12-15 phut
  - `colab status` moi 60 giay ............................ bi thu hoi ~12 phut
  - mot phien ssh luon mo co du lieu / ssh NGAN (`true`) moi 60 giay ... SONG
=> Colab tinh "dang dung" theo KET NOI vao may qua ssh. Tep nay: moi 60 giay mo mot phien ssh ngan
(`true`) vao may, tru khi menu dang co phien ssh toi may do (xem log `l`, khoi dong o -- chinh no da
la hoat dong). Colab chi cho MOT phien ssh moi may, nen trong luc ssh no giu tep khoa
fz_giu_<ten>.ssh; ssh_colab cua menu cho tep do mat roi moi noi (vai giay).

`colab ssh --proxy-mode -s <ten>` TU XIN MAY MOI neu phien <ten> khong con -> truoc moi lan, kiem
phien <ten> van tro dung may <endpoint>; khong thi bo qua (may mat ten: menu `t` -> `n`). Tu dung khi
may khong con trong danh sach cua tai khoan.

  python ~/fz_giu_may.py bat <endpoint> <ten>   # chay nen (neu chua co) -- menu goi sau m / c, khi mo menu, truoc moi o
  python ~/fz_giu_may.py song <endpoint>        # 0 = dang chay
  python ~/fz_giu_may.py tat <endpoint>         # dung (menu goi truoc khi tra may)
  python ~/fz_giu_may.py chay <endpoint> <ten>  # vong lap (tien trinh nen)
  python ~/fz_giu_may.py proxy <ten>            # ProxyCommand cho ssh: `colab ssh --proxy-mode -s <ten>`
                                                # nhung KHONG tu xin may moi khi phien <ten> khong con
Tep: ~/.config/colab-cli/fz_giu_<endpoint>.pid / .log (HOME cua tai khoan -- menu dat HOME rieng).
"""
import os
import signal
import subprocess
import sys
import time

CHU_KY = 60           # giay giua hai lan (da do: ssh ngan moi 60 giay giu duoc may)
THU_DANH_SACH = 10    # moi 10 vong hoi lai danh sach may (may bi thu hoi -> dung)
THU_MUC = os.path.expanduser("~/.config/colab-cli")


def tep(ten_tep):
    return os.path.join(THU_MUC, ten_tep)


def pid_song(endpoint):
    """pid tien trinh giu may <endpoint> dang chay, hoac None."""
    try:
        pid = int(open(tep(f"fz_giu_{endpoint}.pid")).read().strip())
        cmd = open(f"/proc/{pid}/cmdline", "rb").read()
    except (OSError, ValueError):
        return None
    return pid if b"fz_giu_may" in cmd and endpoint.encode() in cmd else None


def ghi_log(endpoint, dong):
    """Giu log ngan: 50 dong cuoi."""
    p = tep(f"fz_giu_{endpoint}.log")
    try:
        cu = open(p).read().splitlines()[-49:]
    except OSError:
        cu = []
    with open(p, "w") as f:
        f.write("\n".join(cu + [time.strftime("%H:%M:%S ") + dong]) + "\n")


def menu_dang_ssh(ten):
    """Co tien trinh ssh (cua menu) toi may <ten> CUA TAI KHOAN NAY dang chay tren dien thoai?
    Moi tai khoan deu mac dinh dat ten may 'fz' -> phan biet bang HOME trong ProxyCommand cua menu
    (`env HOME=<HOME tai khoan> ...`); tien trinh nay chay voi dung HOME do."""
    dich = f"root@colab-{ten}".encode()
    home = f"HOME={os.path.expanduser('~')} ".encode()
    for d in os.listdir("/proc"):
        if not d.isdigit() or int(d) == os.getpid():
            continue
        try:
            a = open(f"/proc/{d}/cmdline", "rb").read().split(b"\0")
        except OSError:
            continue
        if a and os.path.basename(a[0]) == b"ssh" and dich in a and any(home in x for x in a):
            return True
    return False


def proxy(ten):
    """`colab ssh --proxy-mode -s <ten>` cua Colab CLI, CAM tu xin may.

    CLI tu xin may MOI (mac dinh CPU) khi phien <ten> khong co trong sessions.json luc no khoi dong
    -- vd may vua bi tra / thu hoi va mot lenh `colab sessions` da xoa phien (da xay ra 2026-09-26:
    tien trinh giu may kiem phien xong thi phien bi xoa, CLI khoi dong vai giay sau va xin may moi).
    O day thay ham tu xin may cua CLI ngay trong CUNG tien trinh -> khong con khe ho thoi gian."""
    from colab_cli.commands import ssh as m

    def khong_xin(*_a, **_k):
        sys.stderr.write(f"[fz] phien '{ten}' khong con (may da tra / bi thu hoi) -- KHONG tu xin may moi\n")
        raise SystemExit(3)

    m._auto_create_session = khong_xin
    from colab_cli.cli import main
    sys.argv = ["colab", "ssh", "--proxy-mode", "-s", ten]
    return main()


def ping_ssh(ten):
    """Mot phien ssh ngan vao may (qua proxy() -- khong tu xin may). -> ma thoat cua ssh."""
    khoa = tep(f"fz_giu_{ten}.ssh")
    open(khoa, "w").close()
    try:
        return subprocess.run(
            ["ssh", "-o", f"ProxyCommand={sys.executable} {os.path.abspath(__file__)} proxy {ten}",
             "-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null",
             "-o", "LogLevel=ERROR", "-o", "ConnectTimeout=30", "-o", "BatchMode=yes",
             f"root@colab-{ten}", "true"],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            timeout=60).returncode
    except subprocess.TimeoutExpired:
        return -1
    finally:
        try:
            os.remove(khoa)
        except OSError:
            pass


def chay(endpoint, ten):
    from colab_cli.common import state
    # tat (SIGTERM) -> SystemExit: cac khoi finally chay -> xoa tep khoa ssh va tep pid.
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    with open(tep(f"fz_giu_{endpoint}.pid"), "w") as f:
        f.write(str(os.getpid()))
    ghi_log(endpoint, f"bat dau (pid {os.getpid()}, phien '{ten}')")
    try:
        _vong_lap(state, endpoint, ten)
    finally:
        try:
            os.remove(tep(f"fz_giu_{endpoint}.pid"))
        except OSError:
            pass


def _vong_lap(state, endpoint, ten):
    vong = loi = 0
    while True:
        vong += 1
        s = state.store.get(ten)
        if s is None or s.endpoint != endpoint:
            vong = THU_DANH_SACH * (vong // THU_DANH_SACH + 1)   # hoi danh sach may NGAY vong nay
            if vong == THU_DANH_SACH:
                ghi_log(endpoint, f"phien '{ten}' khong con tro may nay -- bo qua (menu t -> n de nhan lai)")
        elif menu_dang_ssh(ten):
            loi = 0                      # menu dang ket noi: da la hoat dong
        else:
            rc = ping_ssh(ten)
            if rc == 0:
                loi = 0
            else:
                loi += 1
                if loi in (1, 5) or loi % 30 == 0:
                    ghi_log(endpoint, f"ssh loi (ma {rc}), lan thu {loi} lien tiep -- thu lai sau {CHU_KY} giay")
        if vong % THU_DANH_SACH == 0:
            try:
                if endpoint not in {a.endpoint for a in state.client.list_assignments()}:
                    ghi_log(endpoint, "dung: may khong con trong danh sach cua tai khoan")
                    break
            except Exception as e:  # noqa: BLE001 -- mat mang: thu lai vong sau
                ghi_log(endpoint, f"khong hoi duoc danh sach may: {str(e)[:120]}")
        time.sleep(CHU_KY)


def bat(endpoint, ten):
    if pid_song(endpoint):
        return 0
    os.makedirs(THU_MUC, exist_ok=True)
    subprocess.Popen([sys.executable, os.path.abspath(__file__), "chay", endpoint, ten],
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, start_new_session=True)
    for _ in range(30):             # doi tep pid (<= 3 giay)
        time.sleep(0.1)
        if pid_song(endpoint):
            return 0
    print(f"[!] Chua bat duoc tien trinh giu may {endpoint} -- xem {tep(f'fz_giu_{endpoint}.log')}")
    return 1


def tat(endpoint):
    pid = pid_song(endpoint)
    if pid:
        os.kill(pid, signal.SIGTERM)
        ghi_log(endpoint, "dung: menu tat (tra may)")
    return 0


if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) == 2 and a[0] == "song":
        sys.exit(0 if pid_song(a[1]) else 1)
    if len(a) == 2 and a[0] == "proxy":
        sys.exit(proxy(a[1]) or 0)
    if len(a) == 2 and a[0] == "tat":
        sys.exit(tat(a[1]))
    if len(a) == 3 and a[0] in ("bat", "chay"):
        sys.exit({"bat": bat, "chay": chay}[a[0]](a[1], a[2]) or 0)
    sys.exit(__doc__)
