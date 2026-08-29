#!/usr/bin/env python3
"""validate_case.py ＋ evidence_ledger.py 的回歸測試。"""
import copy
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

try:
    import yaml
except ImportError:
    print("🔴 缺少 PyYAML —— 測試無法執行（這不是通過）。pip install pyyaml")
    sys.exit(3)

import validate_case as VC  # noqa: E402

CASE = ROOT / "cases" / "CASE-001-control-map"
_r = []


def t(name):
    def d(fn):
        _r.append((name, fn)); return fn
    return d


def with_card(mutate):
    """複製 CASE-001，改一處，回傳 (BLOCK codes, WARN codes)。"""
    d = pathlib.Path(tempfile.mkdtemp())
    dst = d / "CASE-001-control-map"
    shutil.copytree(CASE, dst)
    p = dst / "technique-cards.yaml"
    card = yaml.safe_load(p.read_text())
    mutate(card)
    p.write_text(yaml.safe_dump(card, allow_unicode=True, sort_keys=False))
    fs = VC.check(p)
    return ([x.code for x in fs if x.level == "BLOCK"],
            [x.code for x in fs if x.level == "WARN"])


@t("CASE-001 現況必須無 BLOCK")
def _():
    fs = VC.check(CASE / "technique-cards.yaml")
    b = [x.code for x in fs if x.level == "BLOCK"]
    assert b == [], b


@t("★ boundary 留白必須 BLOCK —— 寫不出邊界代表還沒讀懂")
def _():
    b, _ = with_card(lambda c: c["techniques"][0].update(boundary="   "))
    assert "CASE-5" in b, b


@t("★ gaps 留白必須 BLOCK —— 寫「無」的那份是沒去找")
def _():
    b, _ = with_card(lambda c: c["techniques"][0].update(gaps=[]))
    assert "CASE-6" in b, b


@t("★ security_findings 缺欄位必須 BLOCK（MH-G5）")
def _():
    b, _ = with_card(lambda c: c["security_findings"].pop("credential_requests"))
    assert "SEC-1" in b, b


@t("★ 有 finding 卻無 reviewed_by 必須 BLOCK —— 「有人看過」要是紀錄不是感覺")
def _():
    def m(c):
        c["security_findings"]["prompt_injection_detected"] = True
        c["security_findings"]["reviewed_by"] = None
    b, _ = with_card(m)
    assert "SEC-2" in b, b


@t("★ verification 升級但無 verified_by 必須 BLOCK —— 不得自己給自己升級")
def _():
    b, _ = with_card(lambda c: c["techniques"][0]["claims"][0].update(verification="V3"))
    assert "CASE-11" in b, b


@t("claim id 與所屬 technique 前綴不符必須 BLOCK")
def _():
    b, _ = with_card(lambda c: c["techniques"][0]["claims"][0].update(id="T99-C01"))
    assert "CASE-8" in b, b


@t("claim id 重複必須 BLOCK")
def _():
    def m(c):
        c["techniques"][0]["claims"][1]["id"] = c["techniques"][0]["claims"][0]["id"]
    b, _ = with_card(m)
    assert "CASE-8" in b, b


@t("provenance / verification 值域錯誤必須 BLOCK")
def _():
    b, _ = with_card(lambda c: c["techniques"][0]["claims"][0].update(provenance="E9"))
    assert "CASE-9" in b, b


@t("缺 source_refs 必須 BLOCK —— 指不回來源的宣稱不可覆核")
def _():
    b, _ = with_card(lambda c: c["techniques"][0]["claims"][0].update(source_refs=[]))
    assert "CASE-10" in b, b


@t("untrusted_source 卻未要求人工覆核必須 BLOCK")
def _():
    b, _ = with_card(lambda c: c["techniques"][0].update(human_review_required=False))
    assert "SEC-3" in b, b


@t("source 指向不存在的檔案必須 BLOCK")
def _():
    b, _ = with_card(lambda c: c.update(source="cases/nope/source.md"))
    assert "CASE-2" in b, b


@t("單模型萃取只 WARN，不擋（誠實標記不得被懲罰）")
def _():
    fs = VC.check(CASE / "technique-cards.yaml")
    assert "CASE-3" in [x.code for x in fs if x.level == "WARN"]


# ── evidence_ledger ──
def ledger_run(setup, *args):
    d = pathlib.Path(tempfile.mkdtemp())
    dst = d / "CASE-001-control-map"
    shutil.copytree(CASE, dst)
    setup(dst)
    return subprocess.run([sys.executable, str(ROOT / "scripts" / "evidence_ledger.py"),
                           str(dst), *args], capture_output=True, text=True)


@t("★ 已接受的回填未寫回技巧卡 → 偵測為漂移（exit 1）")
def _():
    def setup(dst):
        v = yaml.safe_load((ROOT / "templates" / "verification.example.yaml").read_text())
        v["review"] = {"reviewer": "T", "reviewed_at": "2026-09-02",
                       "decision": "ACCEPT", "applied_verification": "V4", "reason": "t"}
        (dst / "verification" / "v-t.yaml").write_text(
            yaml.safe_dump(v, allow_unicode=True, sort_keys=False))
    r = ledger_run(setup, "--check")
    assert r.returncode == 1 and "漂移" in r.stdout, (r.returncode, r.stdout[-300:])


@t("未覆核的回填不得自動升級 —— 只列為待覆核")
def _():
    def setup(dst):
        v = yaml.safe_load((ROOT / "templates" / "verification.example.yaml").read_text())
        (dst / "verification" / "v-p.yaml").write_text(
            yaml.safe_dump(v, allow_unicode=True, sort_keys=False))
    r = ledger_run(setup, "--check")
    assert r.returncode == 0 and "待覆核回填 1 筆" in r.stdout, (r.returncode, r.stdout[-300:])


@t("★ 無回填時不得回報漂移（exit 0）")
def _():
    r = ledger_run(lambda dst: None, "--check")
    assert r.returncode == 0, (r.returncode, r.stdout[-300:])


@t("★ 帳本必須明講「0 條驗證過」不是「都沒問題」")
def _():
    r = ledger_run(lambda dst: None, "--check")
    assert "一條都沒測過" in r.stdout, r.stdout[-300:]


@t("★ ROOT 之外的路徑不得崩潰 —— 崩潰的 exit 1 會偽裝成「偵測到漂移」")
def _():
    r = ledger_run(lambda dst: None, "--check")
    assert "Traceback" not in r.stderr, r.stderr[-400:]


def main():
    p = f_ = 0
    for name, fn in _r:
        try:
            fn(); print(f"  PASS  {name}"); p += 1
        except AssertionError as e:
            print(f"  FAIL  {name}\n        {e}"); f_ += 1
    print(f"\n{p}/{p+f_} 通過")
    return 1 if f_ else 0


if __name__ == "__main__":
    sys.exit(main())
