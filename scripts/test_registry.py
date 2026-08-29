#!/usr/bin/env python3
"""registry ＋ dashboard 的回歸測試。"""
import json
import pathlib
import re
import subprocess
import sys
import tempfile
import urllib.request
import time
import socket

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import build_registry as BR  # noqa: E402

_r = []
def t(n):
    def d(f):
        _r.append((n, f)); return f
    return d


@t("registry 與磁碟上的 SKILL.md 數量必須一致")
def _():
    d = BR.build()
    disk_pub = len(list((ROOT / "skills").glob("*/SKILL.md")))
    disk_dft = len(list((ROOT / "drafts" / "skills").glob("*/SKILL.md")))
    assert d["summary"]["published"] == disk_pub, (d["summary"]["published"], disk_pub)
    assert d["summary"]["draft"] == disk_dft, (d["summary"]["draft"], disk_dft)


@t("★ 已提交的 registry 不得過期（--check）")
def _():
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "build_registry.py"), "--check"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout[-300:]


@t("★ 草稿一律 status=draft，且不得混進 skills/")
def _():
    d = BR.build()
    for s in d["skills"]:
        if s["path"].startswith("drafts/"):
            assert s["status"] == "draft", s["name"]
        else:
            assert s["status"] != "draft", f"{s['name']} 是 draft 卻在 skills/ —— 晉升是人的動作"


@t("★ 草稿不得宣稱會扣額度 —— 它根本不執行任何東西")
def _():
    d = BR.build()
    bad = [s["name"] for s in d["skills"] if s["status"] == "draft" and s["billable"]]
    assert not bad, bad


@t("★ 草稿不得把 optional 說成 required（Invariant #6）")
def _():
    d = BR.build()
    bad = [s["name"] for s in d["skills"] if s["status"] == "draft" and s["role"] != "optional"]
    assert not bad, f"草稿階段不執行任何東西，role 應為 optional：{bad[:5]}"


@t("★ 已晉升的來源不得同時留在 drafts/ —— 晉升是搬移不是複製")
def _():
    import re
    def srcs(base):
        out = {}
        for q in pathlib.Path(base).glob("*/SKILL.md"):
            m = re.search(r'mediahouse-source-shortcode:\s*"([^"]+)"', q.read_text(encoding="utf-8"))
            if m:
                out[m.group(1)] = q.parent.name
        return out
    pub, dft = srcs(ROOT / "skills"), srcs(ROOT / "drafts" / "skills")
    dup = set(pub) & set(dft)
    assert not dup, (
        f"同一支影片同時有正式 skill 與草稿：{ {k: (pub[k], dft[k]) for k in dup} }。"
        "晉升是搬移不是複製 —— 留著的那份草稿會被下一個人重做一次")


@t("每支 skill 都指得回 provider capsule")
def _():
    for p in list((ROOT / "skills").glob("*/")) + list((ROOT / "drafts" / "skills").glob("*/")):
        if (p / "SKILL.md").exists():
            assert (p / "references" / "aitokenking.md").exists(), f"{p.name} 缺 capsule"


@t("分流結果必須帶 classifier_error_rate，且不得謊報為數字")
def _():
    for c in sorted((ROOT / "cases").glob("*/triage.json")):
        d = json.loads(c.read_text(encoding="utf-8"))
        v = d.get("classifier_error_rate")
        assert v == "UNMEASURED", (
            f"{c.parent.name} 的 classifier_error_rate = {v!r}。"
            "沒有人工標註就只有『分佈』沒有『錯誤率』，不得填數字")


@t("★ dashboard 不得有任何寫入路徑（唯讀）")
def _():
    src = (ROOT / "skill-dashboard" / "server.py").read_text(encoding="utf-8")
    for bad in ("do_POST", "do_PUT", "do_DELETE", "write_text(", "open(", "os.remove"):
        assert bad not in src, f"dashboard 出現寫入跡象：{bad}"


@t("★ dashboard 起得來，且五條路由都回得了")
def _():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
    p = subprocess.Popen([sys.executable, str(ROOT / "skill-dashboard" / "server.py")],
                         env={**dict(__import__("os").environ), "PORT": str(port),
                              "MEDIAHOUSE_ROOT": str(ROOT)},
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(40):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{port}/healthz", timeout=1); break
            except Exception:
                time.sleep(0.25)
        else:
            raise AssertionError("dashboard 起不來")
        for path in ("/", "/api/state", "/healthz"):
            with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=8) as r:
                assert r.status == 200, path
        d = BR.build()
        name = d["skills"][0]["name"]
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/s/{name}", timeout=8) as r:
            assert r.status == 200
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/nope", timeout=8)
            raise AssertionError("不存在的路由應回 404")
        except urllib.error.HTTPError as e:
            assert e.code == 404
    finally:
        p.terminate(); p.wait(timeout=10)


@t("★ Dockerfile 必須從 repo 根建置 —— context 設錯會得到一個看起來像「沒有 skill」的服務")
def _():
    rj = json.loads((ROOT / "skill-dashboard" / "railway.json").read_text())
    assert rj["build"]["dockerfilePath"] == "skill-dashboard/Dockerfile", rj
    df = (ROOT / "skill-dashboard" / "Dockerfile").read_text()
    for need in ("COPY registry/", "COPY skills/", "COPY drafts/"):
        assert need in df, need


@t("★ Dockerfile 每一行 COPY 的來源路徑都必須真的存在 —— git 不追蹤空目錄")
def _():
    """2026-08-29 真的炸過一次：最後一支草稿被移進 skills/ 之後，
    drafts/ 整個從版本庫消失，Railway 建置死在 `\"/drafts\": not found`。

    ★ 那次所有測試都是綠的、所有檢核都是 0 BLOCK 0 WARN ——
      因為沒有任何一支測試在檢查「建置需要的東西還在不在」。
      檢核器量的是內容對不對，量不到檔案還在不在。"""
    df = (ROOT / "skill-dashboard" / "Dockerfile").read_text()
    srcs = re.findall(r"^COPY\s+(\S+)\s+\S+\s*$", df, re.M)
    assert srcs, "解析不到任何 COPY —— 這個測試自己壞掉了，不是 Dockerfile 沒問題"
    missing = [s for s in srcs if not (ROOT / s.rstrip("/")).exists()]
    assert not missing, f"Dockerfile COPY 的來源不存在：{missing}（空目錄請放一個檔案佔位）"


@t("★ drafts/skills/ 必須存在（可以是空的）—— 空目錄要有檔案佔位才活得過 git")
def _():
    d = ROOT / "drafts"
    assert d.is_dir(), "drafts/ 不存在 —— Dockerfile 會建置失敗"
    assert any(d.rglob("*")), "drafts/ 是完全空的 —— git 不會追蹤它，下次 clone 就沒了"


def main():
    p = f_ = 0
    for n, f in _r:
        try:
            f(); print(f"  PASS  {n}"); p += 1
        except AssertionError as e:
            print(f"  FAIL  {n}\n        {e}"); f_ += 1
    print(f"\n{p}/{p+f_} 通過")
    return 1 if f_ else 0


if __name__ == "__main__":
    sys.exit(main())
