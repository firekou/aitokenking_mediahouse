#!/usr/bin/env python3
"""Skill Registry 產生器（架構覆核 §7）。

掃 skills/ 與 drafts/skills/，產出 registry/skills.json。

★ 這份 registry 是**產物不是原稿**。改它沒有用 ——
  唯一的事實來源是那些 SKILL.md 檔案本身。
  一個可以被手動編輯的清單，三個月後會變成一份沒有人相信的清單。

用法：
    python3 scripts/build_registry.py
    python3 scripts/build_registry.py --check    # CI：檢查是否過期
"""
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "registry" / "skills.json"


def fm_scalar(fm, k):
    m = re.search(rf"^{k}\s*:\s*(.+)$", fm, re.M)
    return m.group(1).strip().strip('"\'') if m else None


def fm_meta(fm):
    out, on = {}, False
    for ln in fm.splitlines():
        if re.match(r"^metadata\s*:\s*$", ln):
            on = True; continue
        if on:
            if not ln.startswith((" ", "\t")):
                break
            m = re.match(r'^\s+([\w-]+)\s*:\s*(.*)$', ln)
            if m:
                out[m.group(1)] = m.group(2).strip().strip('"\'')
    return out


def read(p, status_default):
    t = p.read_text(encoding="utf-8")
    end = t.find("\n---", 3)
    fm, body = t[3:end], t[end + 4:]
    meta = fm_meta(fm)
    desc = fm_scalar(fm, "description") or ""
    return {
        "name": fm_scalar(fm, "name"),
        "path": str(p.relative_to(ROOT)),
        "status": meta.get("mediahouse-status", status_default),
        "layer": meta.get("mediahouse-layer"),
        "case": meta.get("mediahouse-case"),
        "source_shortcode": meta.get("mediahouse-source-shortcode"),
        "role": meta.get("aitokenking-role"),
        "billable": meta.get("aitokenking-billable") == "true",
        "tools": [x.strip() for x in (meta.get("aitokenking-tools") or "").split(",") if x.strip()],
        "description": desc,
        "title": re.sub(r"\s*—.*$", "", (re.search(r"^#\s+(.+)$", body, re.M) or
                                         re.match(r"(.*)", ""))
                        .group(1)).strip() if re.search(r"^#\s+", body, re.M) else None,
        "lines": len(t.splitlines()),
        "has_redline": bool(re.search(r"^##\s*.*紅線", body, re.M)),
        "has_evidence": bool(re.search(r"\bE[1-6]\b|證據強度", body)),
    }


def build():
    pub = [read(p, "published") for p in sorted((ROOT / "skills").glob("*/SKILL.md"))]
    dr = [read(p, "draft") for p in sorted((ROOT / "drafts" / "skills").glob("*/SKILL.md"))]
    skills = pub + dr

    # 案例層的統計（分流結果）
    cases = []
    for c in sorted((ROOT / "cases").glob("*/triage.json")):
        t = json.loads(c.read_text(encoding="utf-8"))
        cases.append({"case": t.get("case_id"), "account": t.get("account"),
                      "dir": c.parent.name, "counts": t.get("counts", {}),
                      "classifier": t.get("classifier"),
                      "classifier_error_rate": t.get("classifier_error_rate")})

    return {
        "generated_at": date.today().isoformat(),
        "generated_by": "scripts/build_registry.py",
        "_note": ("★ 產物不是原稿。改這個檔沒有用 —— 事實來源是 SKILL.md 本身。"
                  "一個可以被手動編輯的清單，三個月後會變成一份沒有人相信的清單。"),
        "summary": {
            "published": len(pub),
            "draft": len(dr),
            "total": len(skills),
            "billable": sum(1 for s in skills if s["billable"]),
            "by_layer": {k: sum(1 for s in skills if s["layer"] == k)
                         for k in sorted({s["layer"] for s in skills if s["layer"]})},
            "by_role": {k: sum(1 for s in skills if s["role"] == k)
                        for k in sorted({s["role"] for s in skills if s["role"]})},
        },
        "cases": cases,
        "skills": skills,
    }


def main(argv):
    data = build()
    body = json.dumps(data, ensure_ascii=False, indent=2)
    if "--check" in argv:
        if not OUT.exists():
            print("🔴 registry/skills.json 不存在 —— 跑 python3 scripts/build_registry.py")
            return 1
        cur = json.loads(OUT.read_text(encoding="utf-8"))
        new = json.loads(body)
        for k in ("summary", "skills", "cases"):
            if cur.get(k) != new.get(k):
                print(f"🔴 registry 已過期（{k} 不同步）—— 跑 python3 scripts/build_registry.py")
                return 1
        print("✅ registry 與 skills/ 同步")
        return 0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(body + "\n", encoding="utf-8")
    s = data["summary"]
    print(f"✅ {OUT.relative_to(ROOT)}")
    print(f"   published {s['published']}｜draft {s['draft']}｜合計 {s['total']}")
    print(f"   by_layer {s['by_layer']}")
    print(f"   by_role  {s['by_role']}｜會扣額度 {s['billable']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
