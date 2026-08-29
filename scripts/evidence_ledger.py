#!/usr/bin/env python3
"""證據帳本 ＋ 升級引擎（P1-3）。

★ MH-G3 的重新定義（依架構覆核）：
  舊說法「沒有實測回填機制」不精確 —— CONTRIBUTING.md 早就有提交格式。
  真正缺的是「有人回填了，但沒有任何東西會因此改變」。
  一份沒有人讀的回報，跟沒有回報一樣。

這支腳本做三件事：
  ① 從 technique-cards.yaml 產生 evidence-ledger.yaml（每條 claim 的當下狀態）
  ② 讀 verification/*.yaml，比對出「已被接受但技巧卡還沒更新」的漂移
  ③ --apply 把已接受的回填寫回技巧卡的 verification 欄位

★ 刻意不做的事：不自動接受任何回填。
  reviewer 的 decision 必須是人寫的 —— 自己給自己升級，這條線就不存在了。

用法：
    python3 scripts/evidence_ledger.py --all            # 產生／更新帳本
    python3 scripts/evidence_ledger.py --all --check    # 只檢查漂移（CI 用）
    python3 scripts/evidence_ledger.py <case> --apply   # 套用已接受的回填
"""
import sys
from datetime import date
import pathlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

try:
    import yaml
except ImportError:
    print("🔴 缺少 PyYAML。pip install pyyaml")
    print("   ⚠️ 這是 not_configured，不是「帳本沒有漂移」。")
    sys.exit(3)

ORDER = ["V0", "V1", "V2", "V3", "V4"]


def rel(p):
    """安全的相對路徑。case 目錄可能在 ROOT 之外（測試、暫存區），
    而 relative_to 在那時會拋例外 —— 那個例外的 exit code 1 會跟
    「偵測到漂移」長得一模一樣。崩潰不得偽裝成結果。"""
    try:
        return str(pathlib.Path(p).resolve().relative_to(ROOT))
    except ValueError:
        return str(p)


def load(p):
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def claims_of(card):
    for t in card.get("techniques") or []:
        for c in t.get("claims") or []:
            yield t, c


def build(case_dir):
    card_p = case_dir / "technique-cards.yaml"
    if not card_p.exists():
        return None
    card = load(card_p)

    # 讀回填
    accepted, pending = {}, []
    vdir = case_dir / "verification"
    for vp in sorted(vdir.glob("*.yaml")) if vdir.exists() else []:
        v = load(vp) or {}
        rv = v.get("review") or {}
        rec = {"file": rel(vp), "verifier": v.get("verifier"),
               "proposed": (v.get("outcome") or {}).get("proposed_verification")}
        if rv.get("decision") == "ACCEPT" and rv.get("applied_verification"):
            cid = v.get("claim_id")
            cur = accepted.get(cid)
            new = rv["applied_verification"]
            if cur is None or ORDER.index(new) > ORDER.index(cur["level"]):
                accepted[cid] = {"level": new, "reviewer": rv.get("reviewer"), **rec}
        else:
            pending.append({**rec, "claim_id": v.get("claim_id"),
                            "decision": rv.get("decision") or "未覆核"})

    rows, drift = [], []
    counts = {"provenance": {}, "verification": {}}
    for t, c in claims_of(card):
        cur = c.get("verification")
        acc = accepted.get(c.get("id"))
        rows.append({
            "claim_id": c.get("id"), "technique": t.get("id"),
            "claim": c.get("claim"), "claim_type": c.get("claim_type"),
            "provenance": c.get("provenance"), "verification": cur,
            "verified_by": c.get("verified_by") or [],
            "falsifier": c.get("falsifier"),
        })
        counts["provenance"][c.get("provenance")] = counts["provenance"].get(c.get("provenance"), 0) + 1
        counts["verification"][cur] = counts["verification"].get(cur, 0) + 1
        if acc and ORDER.index(acc["level"]) > ORDER.index(cur or "V0"):
            drift.append({"claim_id": c.get("id"), "card_says": cur,
                          "accepted": acc["level"], "source": acc["file"]})

    return {"card_path": card_p, "card": card, "rows": rows, "counts": counts,
            "drift": drift, "pending": pending, "accepted": accepted}


def write_ledger(case_dir, st):
    ledger = {
        "case_id": st["card"].get("case_id"),
        "generated_at": date.today().isoformat(),
        "generated_by": "scripts/evidence_ledger.py",
        "_note": (
            "★ 這份檔案是產物不是原稿。改它沒有用 —— "
            "唯一的事實來源是 technique-cards.yaml 與 verification/*.yaml。"
            "要升級一條 claim，走回填流程，見 CONTRIBUTING.md §實測回填。"
        ),
        "summary": {
            "total_claims": len(st["rows"]),
            "by_provenance": dict(sorted(st["counts"]["provenance"].items())),
            "by_verification": dict(sorted(st["counts"]["verification"].items())),
            "verified_any": sum(v for k, v in st["counts"]["verification"].items() if k != "V0"),
            "pending_verifications": len(st["pending"]),
            "drift": len(st["drift"]),
        },
        "claims": st["rows"],
        "pending_verifications": st["pending"],
        "drift": st["drift"],
    }
    p = case_dir / "evidence-ledger.yaml"
    p.write_text(yaml.safe_dump(ledger, allow_unicode=True, sort_keys=False, width=100),
                 encoding="utf-8")
    return p


def main(argv):
    check_only = "--check" in argv
    do_apply = "--apply" in argv
    dirs = (sorted(d for d in (ROOT / "cases").glob("*") if (d / "technique-cards.yaml").exists())
            if "--all" in argv else
            [Path(a) for a in argv if not a.startswith("-")])
    if not dirs:
        print("找不到任何含 technique-cards.yaml 的 case。")
        print("⚠️ 這不是通過，是還沒有東西可檢。")
        return 2

    total_drift = 0
    for d in dirs:
        try:
            st = build(d)
        except Exception as e:                      # noqa: BLE001
            # ★ 內部錯誤用 exit 4，不用 1。
            #   1 的意思是「有發現」，崩潰的意思是「什麼都沒量到」——
            #   兩者共用一個 exit code，CI 綠不綠就不再代表任何事。
            print(f"🔴 內部錯誤（{d}）：{type(e).__name__}: {e}")
            print("   ⚠️ 這不是「偵測到漂移」，是這支腳本自己壞了。exit 4。")
            return 4
        if st is None:
            print(f"跳過 {d}（無 technique-cards.yaml）")
            continue
        s = st["counts"]
        verified = sum(v for k, v in s["verification"].items() if k != "V0")
        print(f"\n{st['card'].get('case_id')}  ({d.name})")
        print(f"  claims {len(st['rows'])}｜provenance {dict(sorted(s['provenance'].items()))}"
              f"｜verification {dict(sorted(s['verification'].items()))}")
        if verified == 0:
            print("  ⚠️ 已驗證 claim 數 = 0 —— 這不是「都沒問題」，是「一條都沒測過」。"
                  "整案效果宣稱不得對外使用")
        if st["pending"]:
            print(f"  待覆核回填 {len(st['pending'])} 筆：")
            for pv in st["pending"]:
                print(f"    - {pv['claim_id']} {pv['decision']}  {pv['file']}")
        if st["drift"]:
            total_drift += len(st["drift"])
            print(f"  🔴 漂移 {len(st['drift'])} 筆（已被接受，但技巧卡還沒更新）：")
            for dr in st["drift"]:
                print(f"    - {dr['claim_id']}: 卡上 {dr['card_says']} → 已接受 {dr['accepted']}"
                      f"  ({dr['source']})")
            if do_apply:
                card = st["card"]
                for t in card.get("techniques") or []:
                    for c in t.get("claims") or []:
                        acc = st["accepted"].get(c.get("id"))
                        if acc and ORDER.index(acc["level"]) > ORDER.index(c.get("verification") or "V0"):
                            c["verification"] = acc["level"]
                            c.setdefault("verified_by", []).append(acc["file"])
                st["card_path"].write_text(
                    yaml.safe_dump(card, allow_unicode=True, sort_keys=False, width=100),
                    encoding="utf-8")
                print("  ✅ 已套用（⚠️ safe_dump 會重排並移除註解，套用後請人工檢閱 diff）")

        if not check_only:
            print(f"  → {rel(write_ledger(d, st))}")

    if check_only and total_drift:
        print(f"\n🔴 共 {total_drift} 筆漂移。有人回填、有人核可，但技巧卡沒有跟著改 ——")
        print("   這正是 MH-G3 的樣子：回報進來了，卻沒有任何東西因此改變。")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
