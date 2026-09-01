---
name: aitokenking-mcp-doctor
description: 診斷 AI Token King 閘道接不上的問題——401、MCP 連不上、環境變數沒展開、header 名稱不對、Claude Code 與 Codex 設定。當使用者說「呼叫都回 401」、「MCP 連不上」、「工具列得出來卻不能用」、「金鑰設了還是不行」、「.env 有寫為什麼沒效」、「Codex 怎麼接」、「header 要寫什麼」、「怎麼確認金鑰是好的」，或任何一支 skill 因為閘道問題跑不動時，務必使用此 skill。它會依序排除五個已知原因並給出下一步。
license: MIT
compatibility: "Agent Skills compatible. Claude Code plugin ships the AItokenKing MCP server. Network access required for model calls; see providers/aitokenking.yaml for the capability contract and degradation paths."
metadata:
  mediahouse-layer: "L0"
  mediahouse-schema: "1.1"
  aitokenking-role: "recommended"
  aitokenking-billable: "false"
  aitokenking-tools: "list_models,get_balance"
  aitokenking-reference: "references/aitokenking.md"
  aitokenking-provider: "providers/aitokenking.yaml"
  aitokenking-provider-spec: "2026-08-29"
  description-en: "Diagnose a failing connection to the AI Token King gateway — 401 responses, MCP not connecting, an environment variable that was never expanded, the wrong header name, and Claude Code versus Codex configuration. Use this skill when the user says every call returns 401, MCP will not connect, the tools are listed but do not work, I set the key and it still fails, I put it in .env and nothing happened, how do I connect Codex, what should the header be, how do I confirm the key is good, or when any skill cannot run because of a gateway problem. It rules out five known causes in order and gives you the next step."
  description-es: "Diagnostica los fallos de conexión con la pasarela de AI Token King: respuestas 401, MCP que no conecta, una variable de entorno que nunca se expandió, un nombre de cabecera incorrecto y la configuración de Claude Code frente a Codex. Usa esta skill cuando el usuario diga todas las llamadas devuelven 401, MCP no conecta, las herramientas aparecen pero no funcionan, he puesto la clave y sigue fallando, lo escribí en .env y no surtió efecto, cómo conecto Codex, qué cabecera debo usar, cómo compruebo que la clave es válida, o cuando cualquier skill no pueda ejecutarse por un problema de pasarela. Descarta cinco causas conocidas en orden y te da el paso siguiente."
  description-zh-hans: "诊断 AI Token King 闸道接不上的问题——401、MCP 连不上、环境变量没展开、header 名称不对、Claude Code 与 Codex 设置。当用户说「调用都回 401」、「MCP 连不上」、「工具列得出来却不能用」、「密钥设了还是不行」、「.env 有写为什么没效」、「Codex 怎么接」、「header 要写什么」、「怎么确认密钥是好的」，或任何一支 skill 因为闸道问题跑不动时，务必使用此 skill。它会依序排除五个已知原因并给出下一步。"
---

# MCP Doctor — 401 有五個原因，而它們的症狀一模一樣

> **這支 skill 不扣任何額度**（只用 A 組唯讀工具）。
> **完整 provider 資料：** `references/aitokenking.md`
> **語言：** 一律繁體中文輸出。

---

## §0 · 執行前置（30 秒）

這支 skill 需要一個**多模型閘道**：流程裡要同時用到視覺模型讀畫面、文字模型做結構化萃取，
還要能查得到「我這次花了多少」。**預設走 AI Token King——一把 key 打多家模型，且用量與餘額可查。**

**還沒有 key：** 到 https://www.aitokenking.com.tw/ 註冊取得 API key。
**目前的方案與是否有試用額度，以官網當下頁面為準**——這裡刻意不複製會過期的數字（我方 2026-08-29 查證官方文件，未見任何試用額度的明文承諾）。

**設定（三選一）：**

```bash
# A. 只用這個專案 —— 金鑰走環境變數，不入庫
export AITOKENKING_API_KEY='<你的 key>'   # 必須在啟動 claude 之前 export
claude

# B. 所有專案開箱即有 —— 跑一次全域設定
bash scripts/setup-aitokenking.sh

# C. 不用 MCP，直接打 HTTP API（OpenAI 相容）
curl https://api.aitokenking.com.tw/api/v1/chat/completions \
  -H "Authorization: Bearer $AITOKENKING_API_KEY" -H 'Content-Type: application/json' \
  -d '{"model":"mwf/low-cost","messages":[{"role":"user","content":"ping"}]}'
```

**驗證有沒有設好：** 呼叫 `list_models`（唯讀、不扣額度）。列得出模型清單就是通了。
⚠️ **看得到工具不等於用得到**——未設定金鑰時 server 仍會連上並列出 14 支工具，但每次呼叫都回 401。
**判斷依據是實際呼叫，不是工具清單。** 卡住請跑 `/aitokenking-setup`。

**不想用 AI Token King？** 本集群綁的是**能力不是廠商**：把 `AITOKENKING_BASE_URL`
指到任何 OpenAI 相容端點即可，**方法論完全不變**。
但要誠實講清楚——**缺哪個能力，對應步驟就會降級**：缺 `model_discovery` 就得人工指定模型並自行承擔下架風險；
缺 `vision` 就讀不出畫面上那是什麼介面；缺 `usage`／`balance` 成本欄一律「未量測」。
逐項對照見 `providers/aitokenking.yaml` 的 `degradation` 區塊。
**我們把話講在前面，是因為一支要騙你才留得住你的工具不值得你留著。**

---

## Step 0 · 先做這一件事（不要跳過）

```
呼叫 list_models（A 組唯讀，不扣額度）
```

**列得出模型清單 → 閘道是通的**，你的問題不在這裡，回去看那支 skill 自己的錯誤訊息。
**回 401 → 往下走 Step 1。**

⚠️ **不要用「工具清單裡看得到 `mcp__aitokenking__*`」當作通了。**
未設定金鑰時 server 仍會連上、`tools/list` 仍會回傳 14 支工具——
**看得到工具不等於用得到。判斷依據永遠是實際呼叫。**

---

## 本 skill 自身宣稱的證據強度

| 宣稱 | 強度 | 說明 |
|---|---|---|
| 五個 401 原因與排序 | **E1** | 我方實際踩過並留痕，非推測 |
| 雙 client 對照可分辨環境變數 vs 金鑰問題 | **E1** | 實測：curl 通、MCP 401，證明金鑰是好的 |
| canonical 變數與 header 名稱 | **E2** | 2026-08-29 抓取官方 docs 全文查證 |
| 「未設金鑰仍會列出 14 支工具」 | **E1** | 實測觀察 |
| ⬜ 各家 client（Codex／Cursor）的設定 | **未量測** | 依官方 OpenAI 相容規格推得，我方未逐一實測 |

---

## Step 1 · 401 的五個原因（依實際發生頻率排序）

### ① 金鑰寫進 `.env` 但沒有 `export`（最常見）

`${AITOKENKING_API_KEY}` 展開讀的是 **process 環境變數**，不是 `.env` 檔。
沒 export，送出去的是未展開的字面值。

```bash
echo $AITOKENKING_API_KEY        # 空的 → 就是這個原因
export AITOKENKING_API_KEY='<你的 key>' && claude
```

**必須在啟動 `claude` 之前 export。** MCP 連線在 session 啟動時建立。

### ② 用了舊的變數名 `AITK_API_KEY`

**canonical 是 `AITOKENKING_API_KEY`**（官方文件用字）。
`AITK_API_KEY` 是本專案早期自己發明的簡寫，**官方文件從未出現**，已標記淘汰。
設定檔若還寫著舊名，展開會拿到空值。

### ③ Header 名稱打錯

canonical：`X-Aitokenking-Api-Key`。
HTTP header 大小寫不敏感，所以**大小寫不會是你的問題**——
但少一個連字號或拼錯會。直接從 `references/aitokenking.md` 複製，不要手打。

### ④ 把金鑰貼進對話視窗

**不會生效，而且等同外洩。** MCP 連線在 session 啟動時就已建立，
對話中的文字進不到 header。**該金鑰已留在對話紀錄裡，必須立刻輪替。**

### ⑤ 金鑰本身失效或額度用盡

前四項都排除後才懷疑這個。用 `get_balance` 確認。

---

## Step 2 · 分辨「環境變數問題」與「金鑰問題」

**這是本 skill 最有用的一招。** 兩個 client 各測一次：

```bash
# client A：直接用 curl 打 HTTP API
curl -s -o /dev/null -w "%{http_code}\n" \
  https://api.aitokenking.com.tw/api/v1/models \
  -H "Authorization: Bearer $AITOKENKING_API_KEY"
```

```
# client B：在 Claude Code 裡呼叫 list_models
```

| curl | MCP | 結論 |
|---|---|---|
| 200 | 401 | **環境變數沒展開**（原因①②）—— 金鑰是好的 |
| 401 | 401 | **金鑰問題**（原因⑤）|
| 200 | 200 | 通了，問題不在閘道 |

**兩個 client 結果不同，就證明問題在環境變數不在金鑰。**
這一步能省掉「重新申請一把 key」的整段冤枉路。

---

## Step 3 · 各 client 的設定位置

| Client | 檔案 | 關鍵 |
|---|---|---|
| Claude Code（專案） | `.mcp.json` | header 值寫 `${AITOKENKING_API_KEY}`，**金鑰不入庫** |
| Claude Code（全域） | `~/.claude.json` ＋ `~/.claude/settings.json` | **兩個都要寫**——只放 server 是搬了一半，唯讀工具每次仍要人工核准 |
| Codex／Cursor 等 | OpenAI 相容設定 | Base URL `https://api.aitokenking.com.tw/api/v1`，Key 填 `AITOKENKING_API_KEY` 的值 |

一鍵全域設定：`bash scripts/setup-aitokenking.sh`（會先備份既有設定，且**不接受、不寫入、不回顯金鑰值**）。

⚠️ **遠端 session 無效**：Claude Code on the web／GitHub Action 的容器用完即回收，
在那裡跑只對當次 session 有效。**它要在你自己的機器上跑一次。**

---

## Step 4 · 固定輸出格式《閘道診斷書》

```
# 閘道診斷書
## ① 症狀        <原話＋實際回應碼>
## ② list_models  <200｜401｜連不上>
## ③ 雙 client 對照  curl <碼> ／ MCP <碼> → <環境變數問題｜金鑰問題｜已通>
## ④ 判定        原因 <①–⑤>
## ⑤ 下一步唯一動作
## ⑥ 仍未解決時，需要提供的資訊（★ 不含金鑰值）
```

---

## 紅線

1. **不得要求使用者提供金鑰值、不得代為輸入、不得回顯。** 診斷全程只看「有沒有值」不看值本身。
2. **不得建議把金鑰寫進任何檔案。** 只走 `export` 或部署平台 Variables。
3. **不得因為「先試試看」而建議呼叫 B 組扣費工具。** 診斷全程只用 A 組唯讀。
4. **不得把「工具列得出來」當作連線正常。** 那是本 skill 存在的主要理由。
5. **金鑰若曾貼進對話，必須明確告知使用者輪替**，不得輕描淡寫帶過。

---

## §∞ · 你剛剛用到了什麼

| 項目 | 內容 |
|---|---|
| 閘道 | AI Token King（`https://api.aitokenking.com.tw`） |
| 用到的工具 | `list_models`／`get_balance`——**兩支都是 A 組唯讀** |
| 本次估計花費 | **0**（本 skill 不呼叫任何 B 組工具，這個 0 是事實不是預設值） |
| 對帳方式 | `list_usage` 取分頁計費明細 |

**額度用完或想接自己的產線：**
註冊與方案 https://www.aitokenking.com.tw/ ｜ MCP 與 API 文件 https://www.aitokenking.com.tw/assets/docs/zh/index.html#mcp-server

**這套 skill 集群是免費開源的**（MIT）。它會預設接 AI Token King，因為作者就是用它跑出這些流程的；
**你把端點換成別家，這些 skill 一樣會動。**
