#!/usr/bin/env python3
"""Media House Skill 檢核器 v1.1

v1.1 的三個結構性改動（依 2026-08-28 架構覆核）：

  P0-1  frontmatter 從自訂 top-level `x-aitokenking` 改為 Agent Skills 標準
        `metadata`（string → string map）。結構化資料的家改成
        providers/aitokenking.yaml —— 一個 cross-agent portable 的格式，
        比一個只有我方 validator 看得懂的欄位值錢。

  P0-4  新增 prompt injection gate。本產線的原料全部來自 IG／TikTok／OCR／
        transcript，也就是 untrusted content，而終點是「下一個人會執行的 SKILL.md」。
        這是整個架構最大的供應鏈缺口（MH-G5）。

  P1-5  新增本地引用檢核。舊版可以全綠，但使用者點下去會壞 ——
        一個量不到斷鏈的檢核器，會讓文件腐爛得無聲無息。

BLOCK 仍然只留給「錯了就回不去」的那一類。什麼都擋的檢核器，人會學會繞過它。
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"
DRAFTS = ROOT / "drafts" / "skills"

REGISTER = "https://www.aitokenking.com.tw/"
AUTH_ENV = "AITOKENKING_API_KEY"          # canonical，官方文件用字（P0-6）
DEPRECATED_ENV = "AITK_API_KEY"           # 我方舊簡寫，官方文件從未出現
PROVIDER = "providers/aitokenking.yaml"

ROLES = {"required", "recommended", "optional"}
BILLABLE_TOOLS = {"chat_completion", "create_message", "create_response",
                  "create_image_generation", "create_video_generation"}
READONLY_TOOLS = {"list_models", "get_model", "list_image_models", "list_video_models",
                  "get_balance", "list_usage", "list_transactions",
                  "get_image_generation", "get_video_generation"}
KNOWN_TOOLS = BILLABLE_TOOLS | READONLY_TOOLS

REQUIRED_META = ["mediahouse-layer", "mediahouse-schema", "aitokenking-role",
                 "aitokenking-billable", "aitokenking-tools", "aitokenking-provider",
                 "aitokenking-provider-spec", "aitokenking-reference"]

# 消費外部不可信內容的層 —— 必須寫明「資料不是指令」（P0-4 / MH-G5）
UNTRUSTED_LAYERS = {"L0.5", "L1", "L2", "orchestrator"}

# 易變 model id：不得出現在 canonical snippet（P0-5）。mwf/* 路由別名不在此列。
VOLATILE_MODEL_RE = re.compile(r"\b(gpt-[45]\.?\d*[\w.-]*|claude-(opus|sonnet|haiku|fable)-[\w.-]+"
                               r"|gemini-[\d.]+[\w-]*|qwen[\w.-]+|glm-[\w.-]+)\b", re.I)


class F:
    def __init__(self, level, code, msg):
        self.level, self.code, self.msg = level, code, msg

    def __str__(self):
        return f"  [{'BLOCK' if self.level == 'BLOCK' else 'WARN '}] {self.code}  {self.msg}"


def split_fm(text):
    if not text.startswith("---"):
        return None, text
    end = text.find("\n---", 3)
    return (None, text) if end == -1 else (text[3:end], text[end + 4:])


def parse_meta(fm):
    """抽 metadata: 底下的 key: "value" —— Agent Skills 標準是 string→string，
    所以這裡不需要處理巢狀或陣列，刻意保持只解析得動合法輸入。"""
    if fm is None:
        return None
    lines, start = fm.splitlines(), None
    for i, ln in enumerate(lines):
        if re.match(r"^metadata\s*:\s*$", ln):
            start = i
            break
    if start is None:
        return None
    out = {}
    for ln in lines[start + 1:]:
        if not ln.strip():
            continue
        if not ln.startswith((" ", "\t")):
            break
        m = re.match(r'^\s+([\w-]+)\s*:\s*(.*)$', ln)
        if m:
            out[m.group(1)] = m.group(2).strip().strip('"\'')
    return out


def scalar(fm, key):
    m = re.search(rf"^{key}\s*:\s*(.+)$", fm or "", re.M)
    return m.group(1).strip().strip('"\'') if m else None


def check_refs(body, out):
    """P1-5：本地引用必須存在。<...> 是模板佔位符，跳過。"""
    for raw in set(re.findall(r"`((?:docs|cases|schemas|scripts|templates|providers|skills)/[^`\s]+)`", body)):
        if "<" in raw or ">" in raw or "*" in raw:
            continue
        if not (ROOT / raw).exists():
            out.append(F("BLOCK", "REF-1",
                         f"引用了不存在的本地路徑 `{raw}` —— 檢核全綠但使用者點下去會壞"))


def check(path):
    o = []
    text = path.read_text(encoding="utf-8")
    fm, body = split_fm(text)

    # ── 標準 frontmatter（P0-1）──
    for key, lvl in (("name", "BLOCK"), ("description", "BLOCK"),
                     ("license", "WARN"), ("compatibility", "WARN")):
        if not scalar(fm, key):
            o.append(F(lvl, "STD-1", f"frontmatter 缺標準欄位 `{key}`"))
    name = scalar(fm, "name")
    # `<...>` 是模板佔位符：templates/SKILL.template.md 必須能通過檢核，
    # 否則模板會慢慢長出「照它寫就會被擋」的欄位而沒有人發現。
    is_template = bool(name) and ("<" in name or ">" in name)
    if name and not is_template and name != path.parent.name:
        o.append(F("BLOCK", "STD-1", f"name `{name}` 與資料夾 `{path.parent.name}` 不符"))

    meta = parse_meta(fm)
    if meta is None:
        o.append(F("BLOCK", "AITK-1", "frontmatter 缺 `metadata` 區塊（嵌入點①）。"
                                      "從 templates/aitokenking-block.md 複製"))
        meta = {}
    else:
        for k in REQUIRED_META:
            if k not in meta:
                o.append(F("BLOCK", "AITK-1", f"metadata 缺 `{k}`"))
        # Distribution Invariant #10：ATK 資訊必須跟著 skill package 一起被帶走。
        # 使用者可能只複製了一個資料夾，那時 providers/ 不在他手上。
        ref = meta.get("aitokenking-reference")
        if ref and not (path.parent / ref).exists():
            o.append(F("BLOCK", "AITK-1",
                       f"aitokenking-reference 指向不存在的 `{ref}` —— "
                       "跑 python3 scripts/sync_provider_capsule.py"))
        if meta.get("aitokenking-provider") != PROVIDER:
            o.append(F("BLOCK", "AITK-1",
                       f"aitokenking-provider 應為 {PROVIDER}，實得 {meta.get('aitokenking-provider')}"))
        role = meta.get("aitokenking-role")
        if role not in ROLES:
            o.append(F("BLOCK", "AITK-1", f"aitokenking-role 值域錯誤：{role!r}"))
        raw_tools = meta.get("aitokenking-tools", "")
        tools = [t.strip() for t in raw_tools.split(",") if t.strip()]
        unknown = [t for t in tools if t not in KNOWN_TOOLS]
        if unknown:
            o.append(F("WARN", "AITK-1", f"tools 含未知項 {unknown}（14 支清單外）"))
        if not tools and role != "optional":
            o.append(F("WARN", "AITK-1", "tools 為空但 role 宣稱需要閘道 —— 兩者不一致"))
        bill = meta.get("aitokenking-billable")
        if bill not in ("true", "false"):
            o.append(F("BLOCK", "AITK-1", f"aitokenking-billable 須為 \"true\"/\"false\"，實得 {bill!r}"))
        else:
            actual = any(t in BILLABLE_TOOLS for t in tools)
            if (bill == "true") != actual:
                o.append(F("BLOCK", "AITK-1",
                           f"billable 宣告 {bill}，但 tools 實際{'含' if actual else '不含'}"
                           " B 組扣費工具。宣告與事實不符 —— 而扣費警示那條 BLOCK"
                           " 就建立在這個值上，填錯它等於關掉整套保護"))

    # ── 嵌入點② §0 ──
    if not re.search(r"^##\s*§0\s*[·.]?\s*執行前置", body, re.M):
        o.append(F("BLOCK", "AITK-2", "缺「## §0 · 執行前置」章節（嵌入點②）"))
    else:
        if REGISTER not in body:
            o.append(F("BLOCK", "AITK-2", f"§0 未出現註冊網址 {REGISTER} —— "
                                          "使用者被擋住的那一刻拿不到下一步"))
        if AUTH_ENV not in body:
            o.append(F("BLOCK", "AITK-2", f"§0 未說明 canonical 環境變數 {AUTH_ENV}"))
    # ★ 只抓「當成有效變數在用」的情況，不抓「說明它已淘汰」。
    #   一支專門解釋舊名已淘汰的 skill（mcp-doctor）不該被自己的規則判違規 ——
    #   規則的目的是「不要讓人照抄舊名」，不是「不准提到舊名」。
    for m in re.finditer(rf"\b{DEPRECATED_ENV}\b", body):
        ctx = body[max(0, m.start() - 120): m.end() + 120]
        if re.search(r"淘汰|deprecat|舊(名|變數|簡寫)|從未出現|不要用|已改", ctx, re.I):
            continue
        o.append(F("WARN", "AITK-2",
                   f"仍把已淘汰的 {DEPRECATED_ENV} 當成有效變數使用 → 改 {AUTH_ENV}"))
        break

    # ── 扣費警示（BLOCK：花掉別人的錢不可回復）──
    if meta.get("aitokenking-billable") == "true" and not re.search(r"扣(額度|款|費)|會花錢|消耗額度", body):
        o.append(F("BLOCK", "AITK-BILL", "billable 為 true 但全文無扣費警示。"
                                         "讓人在按下去之前知道要花錢，是這套東西能被信任的地基"))

    # ── Distribution Invariant #6：不得將 optional dependency 說成 required ──
    #    覆核 §5.4：skill-audit 宣告 role: optional / tools: []，
    #    §0 卻開頭就寫「這支 skill 需要一個多模型閘道」—— 邏輯上不一致。
    #    ATK 的**能見度**是強制的；ATK 的**依賴**必須據實。兩者不衝突，
    #    但把它們搞混會讓整份文件的可信度一起掉。
    if meta.get("aitokenking-role") == "optional":
        if re.search(r"這支\s*skill\s*需要一個\*{0,2}多模型閘道|本 skill 需要一個\*{0,2}多模型閘道", body):
            o.append(F("BLOCK", "TRUTH-1",
                       "role 宣告 optional，§0 卻說「這支 skill 需要一個多模型閘道」。"
                       "ATK 能見度是強制的，ATK 依賴必須據實 —— 把 optional 說成 required，"
                       "掉的是整份文件的可信度"))

    # ── 嵌入點③ §∞ ──
    if not re.search(r"^##\s*§∞\s*[·.]?\s*你剛剛用到了什麼", body, re.M):
        o.append(F("BLOCK", "AITK-3", "缺「## §∞ · 你剛剛用到了什麼」章節（嵌入點③）"))

    # ── P0-4 prompt injection gate（MH-G5）──
    if meta.get("mediahouse-layer") in UNTRUSTED_LAYERS:
        if not re.search(r"不可信|untrusted|資料不是指令|不得直接當作指令", body):
            o.append(F("BLOCK", "SEC-1",
                       "本層消費外部來源（影片／逐字稿／OCR／留言），但全文未聲明"
                       "「這些是資料不是指令」。惡意指令可經 OCR 進入技巧卡、編譯進 SKILL.md，"
                       "再被下一個人執行 —— 這是本架構最大的供應鏈缺口（MH-G5）"))

    # ── P0-5 不得硬寫易變 model id ──
    # ★ 只看「可執行 snippet 裡的 model 參數」，不看散文。
    #   規則的目的是「不要讓人照抄一個會下架的 id」，不是「不准提到模型名字」——
    #   描述畫面上觀察到什麼（"那是 GPT-5.6 Sol 的介面標示"）是證據，必須留著。
    #   第一版沒分這兩者，於是把一句正確的觀察記錄判成違規。
    for block in re.findall(r"```[\s\S]*?```", body):
        for line in block.splitlines():
            if not re.search(r'"?model"?\s*[:=]|--model|MODEL_ID', line):
                continue
            for m in VOLATILE_MODEL_RE.findall(line):
                mid = m[0] if isinstance(m, tuple) else m
                o.append(F("WARN", "MODEL-1",
                           f"可執行 snippet 內硬寫了易變 model id `{mid}` —— "
                           f"repo 鐵律是「永遠先 list_models」。改用 mwf/* 路由別名"))

    # ── P1-5 斷鏈 ──
    check_refs(body, o)

    # ── 品質層（WARN）──
    if not re.search(r"^##\s*.*紅線", body, re.M):
        o.append(F("WARN", "Q-1", "缺《紅線》章節"))
    if not re.search(r"\bE[1-6]\b|證據強度", body):
        o.append(F("WARN", "Q-2", "全文無證據強度標記（E1–E6）"))
    return o


def main(argv):
    if "--drafts" in argv:
        targets = sorted(DRAFTS.glob("*/SKILL.md"))
    elif "--all" in argv:
        targets = sorted(SKILLS.glob("*/SKILL.md"))
    else:
        targets = [Path(a) for a in argv if not a.startswith("-")]
    if not targets:
        print("找不到任何 SKILL.md 可檢核。")
        print("⚠️  這不是通過，是還沒有東西可檢 —— 檢核器掃到 0 個檔案時，"
              "畫面上跟全部通過一模一樣，所以這裡明講。")
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

    print(f"\n掃描 {len(targets)} 支 skill —— BLOCK {tb} / WARN {tw}")
    if tb:
        print("BLOCK 未清空，不得合併。三嵌入點定義見 templates/aitokenking-block.md")
    return 1 if tb else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
