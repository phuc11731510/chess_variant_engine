"""colab_cli.common GIA: chi du cho `tra_mot` (menu.sh) tra may KHONG TEN: state.client.unassign(endpoint)."""
import json
import os
import sys


class _Client:
    def unassign(self, endpoint):
        f = os.environ["HOME"] + "/.config/colab-cli/fake_sessions.json"
        r = json.load(open(f))
        r = {k: v for k, v in r.items() if v["ep"] != endpoint}
        json.dump(r, open(f, "w"))


class _State:
    client = _Client()


state = _State()
