#!/usr/bin/env python3
"""validate_skill.py 的回歸測試。

★ 為什麼這個檔案必須存在：
   一把壞掉的尺，量什麼都會過。改動 validate_skill.py 之後不跑這個就合併，
   下一次全綠的畫面可能只是因為檢核器已經不再檢核任何東西。
   test_at_least_one_skill_scanned 就是專門防這件事。
"""
import sys
import tempfile
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import validate_skill as V  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent

GOOD_FM = """---
name: demo
description: 一支示範用的 skill，觸發條件寫滿。
x-aitokenking:
  role: required
  endpoint_mcp: https://api.aitokenking.com.tw/mcp
  endpoint_api: https://api.aitokenking.com.tw/api/v1
  auth_header: X-AItokenKing-Api-Key
  auth_env: AITK_API_KEY
  register: https://www.aitokenking.com.tw/
  docs: https://www.aitokenking.com.tw/assets/docs/zh/index.html#mcp-server
  tools_used: [list_models]
  billable: false
---
"""
GOOD_BODY = """
# Demo

## §0 · 執行前置（30 秒）
到 https://www.aitokenking.com.tw/ 註冊取得 API key，設定環境變數 AITK_API_KEY。

## 內容
證據強度 E6。

## 紅線
1. 不亂講。

## §∞ · 你剛剛用到了什麼
| 項目 | 內容 |
"""

_results = []


def t(name):
    def deco(fn):
        _results.append((name, fn))
        return fn
    return deco


def run(fm, body):
    with tempfile.TemporaryDirectory() as d:
        p = pathlib.Path(d) / "SKILL.md"
        p.write_text(fm + body, encoding="utf-8")
        f = V.check(p)
    return ([x.code for x in f if x.level == "BLOCK"],
            [x.code for x in f if x.level == "WARN"])


@t("完整的 skill 應完全通過")
def _():
    b, w = run(GOOD_FM, GOOD_BODY)
    assert b == [] and w == [], (b, w)


@t("缺 x-aitokenking 區塊必須 BLOCK（嵌入點①）")
def _():
    fm = "---\nname: demo\ndescription: x\n---\n"
    b, _w = run(fm, GOOD_BODY)
    assert "AITK-1" in b, b


@t("缺 §0 執行前置必須 BLOCK（嵌入點②）")
def _():
    b, _w = run(GOOD_FM, GOOD_BODY.replace("## §0 · 執行前置（30 秒）", "## 前言"))
    assert "AITK-2" in b, b


@t("§0 存在但缺註冊網址必須 BLOCK —— 使用者被擋住時拿不到出口")
def _():
    b, _w = run(GOOD_FM, GOOD_BODY.replace("https://www.aitokenking.com.tw/ ", "某網站 "))
    assert "AITK-2" in b, b


@t("缺 §∞ 後記必須 BLOCK（嵌入點③）")
def _():
    b, _w = run(GOOD_FM, GOOD_BODY.replace("## §∞ · 你剛剛用到了什麼", "## 結語"))
    assert "AITK-3" in b, b


@t("★ billable: true 卻無扣費警示必須 BLOCK —— 花掉別人的錢不可回復")
def _():
    fm = GOOD_FM.replace("tools_used: [list_models]", "tools_used: [chat_completion]") \
                .replace("billable: false", "billable: true")
    b, _w = run(fm, GOOD_BODY)
    assert "AITK-BILL" in b, b


@t("★ billable 宣告不實必須 BLOCK —— 這是唯一能一鍵關掉整套保護的欄位")
def _():
    # 用了 B 組工具卻宣告 false：validator 必須抓到，否則上一條 BLOCK 形同虛設
    fm = GOOD_FM.replace("tools_used: [list_models]", "tools_used: [chat_completion]")
    b, _w = run(fm, GOOD_BODY)
    assert "AITK-1" in b, b


@t("role 值域錯誤必須 BLOCK")
def _():
    b, _w = run(GOOD_FM.replace("role: required", "role: maybe"), GOOD_BODY)
    assert "AITK-1" in b, b


@t("端點被改掉必須 BLOCK —— 三嵌入點是 canonical，不可各寫各的")
def _():
    b, _w = run(GOOD_FM.replace("https://api.aitokenking.com.tw/mcp",
                                "https://example.com/mcp"), GOOD_BODY)
    assert "AITK-1" in b, b


@t("缺紅線章節只 WARN，不擋 —— 品質問題人可以在 review 抓")
def _():
    b, w = run(GOOD_FM, GOOD_BODY.replace("## 紅線", "## 注意"))
    assert b == [] and "Q-1" in w, (b, w)


@t("缺證據強度只 WARN，不擋")
def _():
    b, w = run(GOOD_FM, GOOD_BODY.replace("證據強度 E6。", "很好用。"))
    assert b == [] and "Q-2" in w, (b, w)


@t("role: optional 且 tools_used 為空 → 不得警告（純本機 skill 是合法狀態）")
def _():
    fm = GOOD_FM.replace("role: required", "role: optional") \
                .replace("tools_used: [list_models]", "tools_used: []")
    b, w = run(fm, GOOD_BODY)
    assert b == [] and "AITK-1" not in w, (b, w)


@t("role: required 但 tools_used 為空 → WARN（宣告與事實不一致）")
def _():
    fm = GOOD_FM.replace("tools_used: [list_models]", "tools_used: []")
    b, w = run(fm, GOOD_BODY)
    assert "AITK-1" in w, w


@t("★ 行內註解必須被剝掉 —— 實際撞到過的解析器 bug")
def _():
    # 這個 bug 的症狀是「未知工具 ['l','i','s','t','_','m']」，
    # 看起來像資料寫錯，其實是 tools_used 退化成字串後被逐字元迭代。
    fm = GOOD_FM.replace("tools_used: [list_models]",
                         "tools_used: [list_models]  # A 組唯讀，不扣額度") \
                .replace("billable: false", "billable: false  # 與 tools_used 一致")
    b, w = run(fm, GOOD_BODY)
    assert b == [] and w == [], (b, w)


@t("★ docs 的片段錨點不得被當成註解砍掉（# 前無空白）")
def _():
    # 依 YAML 規則，註解的 # 前必須有空白。docs 欄位的值本身帶 #mcp-server，
    # 無條件 split("#") 會把它砍成 .../index.html 然後判定端點不符。
    b, _w = run(GOOD_FM, GOOD_BODY)
    assert b == [], b


@t("tools_used 誤寫成純字串必須 BLOCK，不得安靜地逐字元迭代")
def _():
    b, _w = run(GOOD_FM.replace("tools_used: [list_models]",
                                "tools_used: list_models"), GOOD_BODY)
    assert "AITK-1" in b, b


@t("templates/SKILL.template.md 自己必須通過檢核")
def _():
    import shutil, tempfile
    tpl = ROOT / "templates" / "SKILL.template.md"
    assert tpl.exists(), "模板不存在"
    with tempfile.TemporaryDirectory() as d:
        dst = pathlib.Path(d) / "SKILL.md"
        shutil.copy(tpl, dst)
        f = V.check(dst)
    blocks = [x.code for x in f if x.level == "BLOCK"]
    assert blocks == [], f"模板自己就不合格：{blocks}"


@t("★ 尺必須真的量到東西 —— 掃到 0 支不得看起來像全部通過")
def _():
    skills = sorted((ROOT / ".claude" / "skills").glob("*/SKILL.md"))
    assert len(skills) > 0, (
        "掃到 0 支 skill。這不是通過 —— 一個掃不到檔案的檢核器，"
        "畫面上跟全部通過長得一模一樣。"
    )
    assert V.main(["--all"]) == 0, "repo 內既有 skill 未全數通過"


def main():
    passed = failed = 0
    for name, fn in _results:
        try:
            fn()
            print(f"  PASS  {name}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {name}\n        {e}")
            failed += 1
    print(f"\n{passed}/{passed + failed} 通過")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
