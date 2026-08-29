#!/usr/bin/env python3
"""案例檢核器（P1-4）—— 把 technique-card schema 從「有 schema」變成「是 gate」。

覆核的原話：schema 存在，但 CI 只檢查 skill 的嵌入點，沒有人檢查 case。
一份沒有人會讀的 schema，跟沒有 schema 一樣。

★ 這支腳本需要 PyYAML。沒裝時它會明講並以 exit 3 結束，
  **不會靜默跳過** —— 一個「因為沒有解析器所以什麼都沒檢查」的檢核器，
  畫面上跟全部通過長得一模一樣。這是本 repo 反覆在防的同一種錯誤。

用法：
    python3 scripts/validate_case.py --all
    python3 scripts/validate_case.py cases/CASE-001-control-map/technique-cards.yaml
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

try:
    import yaml
except ImportError:
    print("🔴 缺少 PyYAML —— 本檢核器無法執行。")
    print("   pip install pyyaml")
    print("   ⚠️ 這是 not_configured，不是「全部通過」。")
    print("      一個因為沒有解析器而什麼都沒檢查的檢核器，畫面上跟全綠一模一樣。")
    sys.exit(3)

VALID_E = {"E1", "E2", "E3", "E4", "E5", "E6"}
VALID_V = {"V0", "V1", "V2", "V3", "V4"}
CLAIM_TYPES = {"observed", "tool_output_observed", "official_doc",
               "author_claim", "our_measurement", "inference"}
REVIEW_STATUS = {"DUAL_MODEL_CROSS_VENDOR", "SINGLE_MODEL", "NOT_REVIEWED"}
SEC_FIELDS = ["prompt_injection_detected", "suspicious_commands",
              "suspicious_urls", "credential_requests"]


class F:
    def __init__(self, level, code, msg):
        self.level, self.code, self.msg = level, code, msg

    def __str__(self):
        return f"  [{'BLOCK' if self.level == 'BLOCK' else 'WARN '}] {self.code}  {self.msg}"


def check(path):
    o = []
    try:
        d = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        return [F("BLOCK", "CASE-0", f"YAML 解析失敗：{str(e)[:200]}")]
    if not isinstance(d, dict):
        return [F("BLOCK", "CASE-0", "頂層不是 mapping")]

    cid = d.get("case_id")
    if not cid or not re.match(r"^CASE-\d{3}$", str(cid)):
        o.append(F("BLOCK", "CASE-1", f"case_id 格式錯誤：{cid!r}（須為 CASE-NNN）"))

    # 來源檔必須存在 —— 指不到來源的技巧卡不可覆核
    src = d.get("source")
    if not src:
        o.append(F("BLOCK", "CASE-1", "缺 source"))
    elif not (ROOT / src).exists():
        o.append(F("BLOCK", "CASE-2", f"source 指向不存在的檔案：{src}"))

    # ── P0-4 安全欄位：四個一個都不能省 ──
    sec = d.get("security_findings")
    if not isinstance(sec, dict):
        o.append(F("BLOCK", "SEC-1", "缺 security_findings 區塊（MH-G5）"))
    else:
        for f in SEC_FIELDS:
            if f not in sec:
                o.append(F("BLOCK", "SEC-1",
                           f"security_findings 缺 `{f}` —— 「省略」與「掃過但沒發現」"
                           "在檔案裡必須長得不一樣"))
        found = (sec.get("prompt_injection_detected") is True
                 or any(sec.get(f) for f in SEC_FIELDS[1:]))
        if found and not sec.get("reviewed_by"):
            o.append(F("BLOCK", "SEC-2",
                       "有 security finding 但沒有 reviewed_by —— "
                       "「有人看過」必須是一筆紀錄，不能是一種感覺"))

    er = (d.get("extraction_review") or {}).get("status")
    if er not in REVIEW_STATUS:
        o.append(F("BLOCK", "CASE-3", f"extraction_review.status 值域錯誤：{er!r}"))
    elif er != "DUAL_MODEL_CROSS_VENDOR":
        o.append(F("WARN", "CASE-3", f"未跑跨供應商互審（{er}）—— 不一致處不可能被發現"))

    techs = d.get("techniques") or []
    if not techs:
        o.append(F("BLOCK", "CASE-1", "techniques 為空"))

    seen_claims = set()
    for t in techs:
        tid = t.get("id", "?")
        for f in ("name", "problem_solved", "route_when", "steps"):
            if not t.get(f):
                o.append(F("BLOCK", "CASE-4", f"{tid} 缺 `{f}`"))
        if not str(t.get("boundary") or "").strip():
            o.append(F("BLOCK", "CASE-5",
                       f"{tid} 的 boundary 留白 —— 寫不出邊界代表還沒讀懂它，此時不得進 L3"))
        if not (t.get("gaps") or []):
            o.append(F("BLOCK", "CASE-6",
                       f"{tid} 的 gaps 留白 —— 一次萃取不可能沒有缺口；"
                       "寫「無」的那份，是沒去找"))
        for s in (t.get("steps") or []):
            if isinstance(s, dict) and not s.get("output"):
                o.append(F("WARN", "CASE-4", f"{tid} 有步驟未寫 output（做完手上多了什麼）"))

        claims = t.get("claims") or []
        if not claims:
            o.append(F("BLOCK", "CASE-7", f"{tid} 缺 claims —— v1.1 的判定單位是 claim"))
        for c in claims:
            cid_ = c.get("id", "?")
            if cid_ in seen_claims:
                o.append(F("BLOCK", "CASE-8", f"claim id 重複：{cid_}"))
            seen_claims.add(cid_)
            if not re.match(r"^T\d{2}-C\d{2}$", str(cid_)):
                o.append(F("BLOCK", "CASE-8", f"claim id 格式錯誤：{cid_!r}"))
            elif tid.replace("-", "") != cid_.split("-")[0]:
                o.append(F("BLOCK", "CASE-8", f"claim {cid_} 的前綴與所屬 technique {tid} 不符"))
            p, v = c.get("provenance"), c.get("verification")
            if p not in VALID_E:
                o.append(F("BLOCK", "CASE-9", f"{cid_} provenance 值域錯誤：{p!r}"))
            if v not in VALID_V:
                o.append(F("BLOCK", "CASE-9", f"{cid_} verification 值域錯誤：{v!r}"))
            if c.get("claim_type") not in CLAIM_TYPES:
                o.append(F("BLOCK", "CASE-9", f"{cid_} claim_type 值域錯誤：{c.get('claim_type')!r}"))
            if not (c.get("source_refs") or []):
                o.append(F("BLOCK", "CASE-10", f"{cid_} 缺 source_refs —— 指不回來源的宣稱不可覆核"))
            # ★ 升級過的 claim 必須指得出是誰驗的
            if v in {"V1", "V2", "V3", "V4"} and not (c.get("verified_by") or []):
                o.append(F("BLOCK", "CASE-11",
                           f"{cid_} verification={v} 但無 verified_by —— "
                           "自己給自己升級，這條線就不存在了"))
            if not c.get("falsifier"):
                o.append(F("WARN", "CASE-12", f"{cid_} 沒寫 falsifier（什麼結果會推翻它）"))

        # 外部來源的可執行內容必須要求人工覆核
        if t.get("execution_origin") == "untrusted_source" and not t.get("human_review_required"):
            o.append(F("BLOCK", "SEC-3",
                       f"{tid} 標為 untrusted_source 卻未要求 human_review_required"))

    if not (d.get("gaps") or []):
        o.append(F("BLOCK", "CASE-6", "案級 gaps 留白"))
    return o


def main(argv):
    if "--all" in argv:
        targets = sorted(ROOT.glob("cases/*/technique-cards.yaml"))
    else:
        targets = [Path(a) for a in argv if not a.startswith("-")]
    if not targets:
        print("找不到任何 technique-cards.yaml。")
        print("⚠️ 這不是通過，是還沒有東西可檢。")
        return 2

    tb = tw = 0
    for p in targets:
        fs = check(p)
        b = [f for f in fs if f.level == "BLOCK"]
        w = [f for f in fs if f.level == "WARN"]
        tb, tw = tb + len(b), tw + len(w)
        try:
            shown = p.resolve().relative_to(ROOT)
        except ValueError:
            shown = p
        print(f"{'FAIL' if b else ('WARN' if w else 'PASS'):4}  {shown}")
        for f in b + w:
            print(f)
    print(f"\n掃描 {len(targets)} 個 case —— BLOCK {tb} / WARN {tw}")
    return 1 if tb else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
