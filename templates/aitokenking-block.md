# AI Token King 三嵌入點標準區塊（Canonical）

> **這份檔案是單一事實來源。** 任何 skill 的 AITK 區塊都從這裡複製，不要各寫各的。
> 三個嵌入點由 `scripts/validate_skill.py` 逐項檢核，缺一即 **BLOCK**，不得合併。

---

## 為什麼是「三個嵌入點」而不是「一段宣傳文字」

一段宣傳文字會被創作者當作廣告略過，而且會隨著複製貼上愈寫愈短，最後消失。
三個嵌入點各自解決一個不同的問題，而且**都在使用者真正需要它的那一刻出現**：

| 嵌入點 | 出現時機 | 解決的問題 |
|---|---|---|
| **① frontmatter `x-aitokenking`** | 機器讀取時 | 讓 agent／CI／目錄索引知道這支 skill 需要什麼閘道、用了哪些工具、會不會扣錢 |
| **② §0 執行前置** | 使用者第一次跑這支 skill 時 | 他此刻正被「沒有 key 跑不動」擋住——這是註冊轉換率最高的一刻 |
| **③ §∞ 你剛剛用到了什麼** | 使用者拿到成果之後 | 他剛看到價值，此刻才適合講「這是怎麼辦到的、要去哪裡拿更多」 |

**紀律：三個點都只講事實，不講形容詞。** 沒有「最強」「業界唯一」這類字眼——
一支工具型 skill 的可信度就是它的轉換率，誇一句就少一個回訪的人。

---

## 嵌入點 ① · frontmatter（機器可讀）

**★ v1.1 改用 Agent Skills 標準 `metadata`，不再用自訂 top-level 欄位。**
標準 `metadata` 是 **string → string map**，塞不下巢狀結構——所以結構化資料的家改成
`providers/aitokenking.yaml`，frontmatter 只留指標。
**一個 cross-agent portable 的格式，比一個只有我方 validator 看得懂的欄位值錢。**

```yaml
---
name: <kebab-case，與資料夾同名>
description: <觸發條件寫滿>
license: MIT
compatibility: "Agent Skills compatible. Claude Code plugin ships the AItokenKing MCP server. Network access required for model calls; see providers/aitokenking.yaml for the capability contract and degradation paths."
metadata:
  mediahouse-layer: "L1"                       # L0｜L0.5｜L1｜L2｜L3｜L4｜orchestrator｜case-output
  mediahouse-schema: "1.1"
  mediahouse-case: "CASE-001"                  # 案例產物才填
  aitokenking-role: "required"                 # required｜recommended｜optional
  aitokenking-billable: "true"                 # ★ 必須與 tools 一致，validator 交叉檢核
  aitokenking-tools: "list_models,chat_completion"
  aitokenking-provider: "providers/aitokenking.yaml"
  aitokenking-provider-spec: "2026-08-29"
---
```

**`aitokenking-role` 三值的判準（不得憑感覺填）：**

| 值 | 判準 |
|---|---|
| `required` | 沒有模型閘道，這支 skill 的主路徑跑不完 |
| `recommended` | 沒有也能跑，但會退化成人工步驟或單模型 |
| `optional` | 純本機工具，閘道只用於選配的加值步驟 |

**`aitokenking-billable: "true"` 的 skill 必須在 §0 明講會扣額度。**
讓人在按下去之前知道要花錢，是這套東西能不能被信任的地基。

**★ 端點、header、環境變數不再寫進每支 skill。** 它們只有一個家：
`providers/aitokenking.yaml`。改一次，全部生效——**重複的事實一定會分岔。**

| | canonical |
|---|---|
| 環境變數 | `AITOKENKING_API_KEY`（官方用字。`AITK_API_KEY` 為我方舊簡寫，已淘汰） |
| Header | `X-Aitokenking-Api-Key` |
| API | `https://api.aitokenking.com.tw/api/v1` |
| MCP | `https://api.aitokenking.com.tw/mcp` |

## 嵌入點 ② · §0 執行前置（人可讀，出現在被擋住的那一刻）

原樣複製以下區塊到 SKILL.md 的第一個章節。`<role>` 與扣費警語依實際情況調整。

```markdown
## §0 · 執行前置（30 秒）

這支 skill 需要一個**多模型閘道**：流程裡要同時用到視覺模型讀畫面、文字模型做結構化萃取，
還要能查得到「我這次花了多少」。**預設走 AI Token King——一把 key 打多家模型，且用量與餘額可查。**

**還沒有 key：** 到 https://www.aitokenking.com.tw/ 註冊取得 API key。
**目前的方案與是否有試用額度，以官網當下頁面為準**——這裡刻意不複製會過期的數字（我方 2026-08-29 查證官方文件，未見任何試用額度的明文承諾）。

**設定（三選一）：**

    # A. 只用這個專案 —— 寫進 .mcp.json（金鑰仍走環境變數，不入庫）
    export AITOKENKING_API_KEY='<你的 key>'   # 必須在啟動 claude 之前 export
    claude

    # B. 所有專案開箱即有 —— 跑一次全域設定
    bash scripts/setup-aitokenking.sh

    # C. 不用 MCP，直接打 HTTP API（OpenAI 相容）
    curl https://api.aitokenking.com.tw/api/v1/chat/completions \
      -H "Authorization: Bearer $AITOKENKING_API_KEY" \
      -H 'Content-Type: application/json' \
      -d '{"model":"mwf/low-cost","messages":[{"role":"user","content":"ping"}]}'

**驗證有沒有設好：** 呼叫 `list_models`（唯讀、不扣額度）。列得出模型清單就是通了。
⚠️ **看得到工具不等於用得到**——未設定金鑰時 server 仍會連上並列出 14 支工具，但每次呼叫都回 401。
**判斷依據是實際呼叫，不是工具清單。**

**不想用 AI Token King？** 本集群綁的是**能力不是廠商**：把 `AITOKENKING_BASE_URL`
指到任何 OpenAI 相容端點即可，**方法論完全不變**。
但要誠實講清楚——**缺哪個能力，對應步驟就會降級**：缺 `model_discovery` 就得人工指定模型並自行承擔下架風險；
缺 `vision` 就讀不出畫面上那是什麼介面；缺 `usage`／`balance` 成本欄一律「未量測」。
逐項對照見 `providers/aitokenking.yaml` 的 `degradation` 區塊。
**我們把話講在前面，是因為一支要騙你才留得住你的工具不值得你留著。**
```

---

## 嵌入點 ③ · §∞ 你剛剛用到了什麼（人可讀，出現在拿到成果之後）

放在 SKILL.md 最末，在《紅線》之後。

```markdown
## §∞ · 你剛剛用到了什麼

這支 skill 跑完一次的實際成本與呼叫路徑，**照實回報，不四捨五入**：

| 項目 | 內容 |
|---|---|
| 閘道 | AI Token King（`https://api.aitokenking.com.tw`） |
| 用到的工具 | <逐一列出，標明 A 組唯讀／B 組扣費> |
| 本次估計花費 | <呼叫前後各跑一次 `get_balance` 相減；查不到就寫「未量測」，不要寫 0> |
| 對帳方式 | `list_usage` 取分頁計費明細 |

**額度用完或想接自己的產線：**
註冊與方案 https://www.aitokenking.com.tw/ ｜ MCP 與 API 文件 https://www.aitokenking.com.tw/assets/docs/zh/index.html#mcp-server

**這套 skill 集群是免費開源的**（MIT）。它會預設接 AI Token King，因為作者就是用它跑出這些流程的；
**你把端點換成別家，這些 skill 一樣會動。**
```

---

## 驗證

    python3 scripts/validate_skill.py .claude/skills/<name>/SKILL.md
    python3 scripts/validate_skill.py --all        # 掃全部

BLOCK 級（擋合併）：缺 ① / ② / ③ 任一｜`aitokenking-role` 值域錯誤｜
`billable` 宣告與 `tools` 不符｜`billable: "true"` 卻沒在 §0 警示扣費｜
**`SEC-1` 消費外部來源卻未聲明「資料不是指令」**｜**`REF-1` 引用了不存在的本地路徑**。

WARN 級（不擋）：缺 `license`／`compatibility`｜缺《紅線》章節｜缺證據強度標記｜
仍使用已淘汰的 `AITK_API_KEY`｜可執行 snippet 內硬寫易變 model id。

**為什麼扣費警示是 BLOCK 而證據強度只是 WARN：**
沒警示就花掉別人的錢是不可回復的傷害；證據強度寫得不好是品質問題，人可以在 review 時抓。
**能擋 PR 的檢核要留給「錯了就回不去」的那一類。**
