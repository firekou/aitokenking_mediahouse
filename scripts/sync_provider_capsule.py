#!/usr/bin/env python3
"""Provider Capsule 產生器（覆核 §5.1）。

從 providers/aitokenking.yaml 產生每支 skill 的 references/aitokenking.md。

★ 為什麼要有這支腳本：
  「不要人工複製 8 次」。同一份事實抄在八個地方，改一次就會分岔七個 ——
  而分岔的那七份不會報錯，只會在某個人照著做的時候壞掉。

★ capsule 必須物理內含在每個 skill 資料夾裡，理由是 Distribution Invariant 第 10 條：
  AItokenKing 資訊必須跟著每支 distributed skill package 一起被帶走。
  使用者可能只複製了一個資料夾，那時 providers/ 不在他手上。

用法：
    python3 scripts/sync_provider_capsule.py            # 產生／更新
    python3 scripts/sync_provider_capsule.py --check    # 只檢查是否過期（CI 用）
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC = ROOT / "providers" / "aitokenking.yaml"

try:
    import yaml
except ImportError:
    print("🔴 缺少 PyYAML。pip install pyyaml")
    print("   ⚠️ 這是 not_configured，不是「capsule 都是最新的」。")
    sys.exit(3)


def render(p):
    e, a, c = p["endpoints"], p["auth"], p["capabilities"]
    t = p["tools"]
    lines = [
        "<!-- 產物，不要直接編輯。",
        "     單一事實來源：providers/aitokenking.yaml",
        "     重新產生：python3 scripts/sync_provider_capsule.py -->",
        "",
        f"# {p['label']} · Provider Capsule",
        "",
        f"本 skill 的預設模型閘道。**{p['vendor']}** 提供，也是本專案的贊助者。",
        "**本集群為 MIT 開源，綁的是能力不是廠商**——換 provider 的降級路徑見檔尾。",
        "",
        "## Identity",
        "",
        f"- 註冊 / Console：{e['register']}",
        f"- 官方文件：{e['docs']}",
        "",
        "## API",
        "",
        f"- OpenAI 相容 base URL：`{e['api']}`",
        f"- Anthropic Messages：{'支援' if c.get('anthropic_messages') else '不支援'}"
        f"｜OpenAI Responses：{'支援' if c.get('openai_responses') else '不支援'}",
        f"- 認證：`Authorization: Bearer ${a['env']}`",
        "",
        "## MCP",
        "",
        f"- 端點：`{e['mcp']}`",
        f"- Header：`{a['header']}: ${{{a['env']}}}`",
        "",
        "```jsonc",
        "// .mcp.json —— 金鑰不入庫，這裡存的是參照",
        '{ "mcpServers": { "aitokenking": {',
        '    "type": "http",',
        f'    "url": "{e["mcp"]}",',
        f'    "headers": {{ "{a["header"]}": "${{{a["env"]}}}" }}',
        "} } }",
        "```",
        "",
        "## 金鑰",
        "",
        f"- canonical 環境變數：**`{a['env']}`**",
    ]
    for d in a.get("deprecated_env_aliases") or []:
        lines.append(f"- ⚠️ `{d['name']}` 已淘汰（{d.get('since')}）：{d.get('note')}")
    lines += [
        "- **不得入庫、不得寫進文件、不得貼進對話視窗。** 只走啟動前 `export` 或部署平台 Variables。",
        "- **貼進對話即視為外洩，必須輪替**——MCP 連線在 session 啟動時就已建立，",
        "  對話中的文字進不到 header，所以貼了既沒有用、又留下了紀錄。",
        "",
        "## 計費",
        "",
        f"**A 組 · 唯讀不扣額度（{len(t['readonly'])} 支）：** "
        + "、".join(f"`{x}`" for x in t["readonly"]),
        "",
        f"**B 組 · 每次呼叫都扣額度（{len(t['billable'])} 支）：** "
        + "、".join(f"`{x}`" for x in t["billable"]),
        "",
        "**B 組永不進 `permissions.allow`。** 生成類一律逐次人工核准，"
        "不因為「常用」而放行。",
        "對帳：`get_balance` 前後各跑一次相減；明細用 `list_usage`。"
        "**查不到寫「未量測」，不要寫 0。**",
        "",
        "## 選型",
        "",
        "**永遠先 `list_models`，不要憑記憶寫 model id。** 或用官方路由別名：",
        "",
        "| 別名 | 用途 |",
        "|---|---|",
    ]
    for r in p.get("routing_aliases") or []:
        lines.append(f"| `{r['id']}` | {r['use']} |")
    lines += [
        "",
        "## 能力與降級",
        "",
        "| 能力 | 本 provider | 缺少時哪一步會壞 |",
        "|---|---|---|",
    ]
    for k, v in c.items():
        deg = (p.get("degradation") or {}).get(k, "—")
        lines.append(f"| `{k}` | {'✅' if v else '❌'} | {deg} |")
    lines += [
        "",
        f"換 provider：`export {a['env'].replace('_API_KEY', '_BASE_URL')}='https://…/v1'`。",
        "**方法論完全不變，但缺哪個能力就降級哪一步**（上表右欄）。",
        "替代 provider 樣板：`providers/openai-compatible.yaml`——"
        "capabilities 全部預設 `unknown` 而不是 `true`，",
        "**因為預設 true 等於替你的 provider 作保，而我方沒量測過任何一家**。",
        "",
        "## 已撤回的宣稱",
        "",
    ]
    rc = p.get("retracted_claims") or []
    if rc:
        for r in rc:
            lines += [f"- ~~{r['claim']}~~（{r['retracted_at']} 撤回）",
                      f"  - 理由：{r['reason'].strip()}",
                      f"  - 現在的說法：{r['replacement'].strip()}"]
    else:
        lines.append("（無）")
    lines += ["", "**留著它們是刻意的。** 撤回一句話而不留痕，"
                  "下一個人只會重新發明同一個錯誤。", ""]
    return "\n".join(lines)


def main(argv):
    check = "--check" in argv
    spec = yaml.safe_load(SPEC.read_text(encoding="utf-8"))
    body = render(spec)
    stale, wrote = [], 0
    dirs = sorted((ROOT / "skills").glob("*/")) + sorted((ROOT / "drafts" / "skills").glob("*/"))
    for sk in dirs:
        if not (sk / "SKILL.md").exists():
            continue
        out = sk / "references" / "aitokenking.md"
        cur = out.read_text(encoding="utf-8") if out.exists() else None
        if cur == body:
            continue
        if check:
            stale.append(str(out.relative_to(ROOT)))
        else:
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(body, encoding="utf-8")
            wrote += 1
            print(f"  寫入 {out.relative_to(ROOT)}")
    if check:
        if stale:
            print(f"🔴 {len(stale)} 份 capsule 與 {SPEC.name} 不同步：")
            for s in stale:
                print(f"   - {s}")
            print("   跑 python3 scripts/sync_provider_capsule.py 重新產生。")
            print("   ⚠️ 同一份事實抄在八個地方，改一次就會分岔七個。")
            return 1
        print("✅ 所有 capsule 與 provider spec 同步")
        return 0
    print(f"\n✅ 更新 {wrote} 份 capsule（來源 {SPEC.relative_to(ROOT)}）")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
