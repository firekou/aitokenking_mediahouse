---
name: aitokenking-model-picker
description: 依用途、模態、成本與上下文需求，從帳戶當下真正可用的模型裡挑出 2–3 個候選並說明取捨。當使用者說「該用哪個模型」、「有沒有便宜一點的」、「哪個支援看圖」、「上下文要很長用哪個」、「這個 model id 還在嗎」、「模型下架了怎麼辦」、「mwf 別名是什麼」，或任何一支 skill 要寫死 model id 之前，務必使用此 skill。它一律先呼叫 list_models，不憑記憶回答。
license: MIT
compatibility: "Agent Skills compatible. Claude Code plugin ships the AItokenKing MCP server. Network access required for model calls; see providers/aitokenking.yaml for the capability contract and degradation paths."
metadata:
  mediahouse-layer: "L0"
  mediahouse-schema: "1.1"
  aitokenking-role: "required"
  aitokenking-billable: "false"
  aitokenking-tools: "list_models,get_model,list_image_models,list_video_models"
  aitokenking-reference: "references/aitokenking.md"
  aitokenking-provider: "providers/aitokenking.yaml"
  aitokenking-provider-spec: "2026-08-29"
---

# Model Picker — 先查再答，永遠不要憑記憶寫 model id

> **這支 skill 不扣任何額度**（四支工具全是 A 組唯讀）。
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

## 為什麼需要這支 skill

**憑記憶寫 model id 是這條產線最容易犯、也最難察覺的錯誤**——
它不會在你寫的時候失敗，會在三個月後某個人跑到一半時失敗。

模型會下架、改名、換供應路徑。而一個寫死在 skill 裡的 id，
**沒有任何機制會告訴你它已經不在了**。

## 本 skill 自身宣稱的證據強度

| 宣稱 | 強度 | 說明 |
|---|---|---|
| `mwf/*` 五個路由別名存在 | **E2** | 2026-08-29 抓取官方 docs 全文查證 |
| 模型清單以 `list_models` 為準 | **E1** | 實測可取回帳戶當下可用清單 |
| ⬜ 各模型的實際品質差異 | **未量測** | 本 skill 不排名、不推薦「最好的」——見《紅線》第 2 條 |

---

## Step 0 · 入場檢查（一題）

**你問的是「哪個模型」還是「這件事做不做得到」？**
後者 → 先看 `providers/aitokenking.yaml` 的 `capabilities`。
**閘道不支援的能力，換哪個模型都沒用。**

---

## Step 1 · 先查（強制，不可略）

```
list_models                          → 帳戶當下真正可用的文字模型
list_image_models / list_video_models → 圖／影片模型的解析度、長寬比、時長範圍
get_model <id>                        → 單一模型的能力與定價細節
```

**不准跳過這一步直接回答。** 就算你「記得」某個 id 存在。

---

## Step 2 · 四題判定

| 題 | 問法 | 影響 |
|---|---|---|
| **模態** | 要不要讀圖／產圖／產影片？ | 讀圖 → 需 vision；產圖／影片 → 另一組清單 |
| **上下文** | 單次輸入大概多長？ | 逐字稿＋OCR 動輒兩三萬字元 |
| **成本優先度** | 這件事會跑幾次？ | 跑一次選好的；跑一千次選便宜的 |
| **互審？** | 需不需要第二家供應商？ | **同一家的兩個模型不算互審** |

---

## Step 3 · 給 2–3 個候選，不要給一個

**一律列出取捨，讓人自己選。** 固定格式：

```
| 候選 | model id / 別名 | 為什麼是它 | 代價 |
|---|---|---|---|
| 省錢 | … | … | … |
| 平衡 | … | … | … |
| 能力優先 | … | … | … |
```

**★ 優先給官方路由別名而不是具體 id**（`mwf/coding-auto`／`mwf/coding-fast`／
`mwf/coding-long`／`mwf/low-cost`／`mwf/vision-chat`）——
別名的生命週期比 id 長，而**這正是「不要寫死 id」這條紀律唯一可持續的解法**。

---

## Step 4 · 兩個實測過的通道特性（會影響選型）

1. **`max_tokens` 是逾時主因，不是語料長度。** 同一份 24K 字元語料：
   800 → 22 秒完成；2000 → 36 秒完成；**5000 與 7000 → 逾時**。
   長文萃取把 `max_tokens` 壓在 ≤3000 並分軸送。**縮語料只是把症狀壓下去。**
2. **`chat_completion` 沒有網路存取。** 任何需要即時資料的問題（榜單、股價、當日新聞）
   都答不出來。**不得把模型對即時資料的回答當作事實引用。**

---

## Step 5 · 固定輸出格式《選型判定書》

```
# 選型判定書 · <用途>
## ① 查詢時間      <呼叫 list_models 的時間 —— 清單會變，判定有時效>
## ② 四題判定      模態／上下文／成本優先度／是否需互審
## ③ 候選（2–3 個，含取捨）
## ④ 建議          <一個，並說明什麼情況下該換掉它>
## ⑤ 別名 vs 硬寫  <能用別名就用別名，理由寫出來>
## ⑥ 下一步唯一動作
```

---

## 紅線

1. **不得憑記憶回答，必須先 `list_models`。** 這是本 skill 存在的唯一理由。
2. **不得宣稱某個模型「最好」。** 我方沒有跨模型品質量測，
   說「最好」是未量測的宣稱——**寫出去會同時損失可信度與轉換率**。
   可以說「上下文最長」「單價最低」，那些查得到。
3. **不得建議把具體 model id 寫死進 skill template。** 用別名或寫「由 `list_models` 選出」。
4. **不得呼叫 B 組扣費工具做「試跑比較」。** 選型全程只用 A 組唯讀。
5. **定價與清單有時效**，判定書必須帶查詢時間。

---

## §∞ · 你剛剛用到了什麼

| 項目 | 內容 |
|---|---|
| 閘道 | AI Token King（`https://api.aitokenking.com.tw`） |
| 用到的工具 | `list_models`／`get_model`／`list_image_models`／`list_video_models`——**四支全是 A 組唯讀** |
| 本次估計花費 | **0**（本 skill 不呼叫任何 B 組工具，這個 0 是事實不是預設值） |
| 對帳方式 | `list_usage` 取分頁計費明細 |

**額度用完或想接自己的產線：**
註冊與方案 https://www.aitokenking.com.tw/ ｜ MCP 與 API 文件 https://www.aitokenking.com.tw/assets/docs/zh/index.html#mcp-server

**這套 skill 集群是免費開源的**（MIT）。它會預設接 AI Token King，因為作者就是用它跑出這些流程的；
**你把端點換成別家，這些 skill 一樣會動。**
