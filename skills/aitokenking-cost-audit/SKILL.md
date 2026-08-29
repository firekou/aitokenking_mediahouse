---
name: aitokenking-cost-audit
description: 查這一次／這個月到底花了多少、花在哪個模型上，並找出可以省下來的地方。當使用者說「這次花了多少」、「餘額剩多少」、「帳單怎麼看」、「為什麼扣這麼多」、「哪個步驟最貴」、「能不能省一點」、「怎麼對帳」、「usage 怎麼查」，或任何一支 skill 的 §∞ 成本欄需要填實際數字時，務必使用此 skill。
license: MIT
compatibility: "Agent Skills compatible. Claude Code plugin ships the AItokenKing MCP server. Network access required for model calls; see providers/aitokenking.yaml for the capability contract and degradation paths."
metadata:
  mediahouse-layer: "L0"
  mediahouse-schema: "1.1"
  aitokenking-role: "required"
  aitokenking-billable: "false"
  aitokenking-tools: "get_balance,list_usage,list_transactions,get_model"
  aitokenking-reference: "references/aitokenking.md"
  aitokenking-provider: "providers/aitokenking.yaml"
  aitokenking-provider-spec: "2026-08-29"
---

# Cost Audit — 「感覺沒用多少」不是對帳

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

## 為什麼這支 skill 存在

**一個免費開源的工具如果會安靜地花掉別人的錢，它造成的傷害比不存在還大。**

Media House 集群每支 skill 的 `§∞` 都要求填實際花費。
這支 skill 就是去把那個數字查出來的——**而不是讓人填一個看起來合理的估算**。

## 本 skill 自身宣稱的證據強度

| 宣稱 | 強度 | 說明 |
|---|---|---|
| `get_balance` 前後相減可得精確扣款 | **E1** | 實測：99.978 → 99.972，粒度到小數第三位 |
| credit ≈ USD | **E1** | 實測一次 283 tokens 呼叫，費率推算與實扣一致 |
| `list_usage` 只含模型用量扣費 | **E1** | 實測；充值與套餐購買在 `list_transactions` |
| ⬜ 跨供應商的成本比較 | **未量測** | 本 skill 不做外部比價 |

---

## Step 0 · 你要問的是哪一個問題

| 你想知道 | 用哪個工具 |
|---|---|
| **這一次**跑掉多少 | `get_balance` 前後各一次，相減 |
| **這個月**花在哪 | `list_usage` 分頁計費明細 |
| 我**充值**過多少 | `list_transactions`（★ 不含扣費明細，別搞混） |
| 某個模型**單價**多少 | `get_model` |

---

## Step 1 · 單次對帳（本集群的強制紀律）

```
① get_balance          → before
② 跑你的流程
③ get_balance          → after
④ before − after       = 本次精確花費
```

**前後各跑一次是強制的，不是選配。** 兩支呼叫都是 A 組唯讀、不扣額度，
**沒有任何理由不做。**

⚠️ **如果你忘了跑 ①，這次就是查不到——那就在 `§∞` 寫「未量測」。**
**不要寫 0。** 0 看起來像量測結果，「未量測」才是事實。
**這兩個字的差別，是這整套東西可不可信的分界。**

---

## Step 2 · 期間對帳

```
list_usage → 分頁計費明細
```

逐項可看到模型、用量、扣費。**對不上時先確認三件事：**

1. `list_usage` **只含模型用量扣費**；充值與套餐購買在 `list_transactions`。
   兩者相加才是完整金流。
2. **非同步任務**（圖片／影片生成）的扣費時間點與送出時間點可能不同。
3. 同一個 `model_id` 在不同**推理力度**下成本可能差數倍——
   若你的呼叫帶了 effort 之類的參數，帳單看起來會「不合理」但其實是對的。

---

## Step 3 · 找可以省的地方（依實際效果排序）

| 順位 | 做法 | 為什麼有效 |
|---|---|---|
| 1 | **檢查有沒有重複呼叫** | 最大的浪費通常不是模型選錯，是同一件事跑了三次 |
| 2 | **關鍵幀只送該送的** | L1 的抽幀讀圖：一支影片抽 50–100 幀，只有 3–8 幀需要視覺模型 |
| 3 | **`max_tokens` 壓低** | 逾時重試是隱形成本；≤3000 反而更快完成 |
| 4 | **用 `mwf/low-cost` 跑不需要品質的步驟** | 分流比換模型有效 |
| 5 | 換更便宜的模型 | ★ 放最後——**它通常是效果最小的一項** |

⚠️ **先量再改。** 沒有 `list_usage` 明細就開始「優化」，
省下來的多半是你本來就沒在花的地方。

---

## Step 4 · 固定輸出格式《成本稽核書》

```
# 成本稽核書 · <期間或單次>
## ① 量測方式    <get_balance 前後相減｜list_usage 期間明細｜★ 未量測>
## ② 總額        <數字；查不到寫「未量測」，不得寫 0>
## ③ 分項        | 模型／工具 | 次數 | 金額 | 占比 |
## ④ 最大單項    <一項，含它為什麼這麼貴>
## ⑤ 可省之處    <依 Step 3 順位，各附預估影響>
## ⑥ 下一步唯一動作
```

---

## 紅線

1. **查不到就寫「未量測」，不得寫 0。** 這是本集群最常被違反的一條，
   而 0 與「未量測」在報表上長得一模一樣、意思完全相反。
2. **不得以估算冒充量測。** 估算要標「估算」，並寫出估法。
3. **不得為了對帳呼叫任何 B 組扣費工具。** 稽核全程只用 A 組唯讀——
   **一支會讓你花錢的成本稽核工具是荒謬的。**
4. **不得建議「關掉成本回報以簡化流程」。**
5. **不得把 `list_transactions`（充值）與 `list_usage`（扣費）混為一談。**

---

## §∞ · 你剛剛用到了什麼

| 項目 | 內容 |
|---|---|
| 閘道 | AI Token King（`https://api.aitokenking.com.tw`） |
| 用到的工具 | `get_balance`／`list_usage`／`list_transactions`／`get_model`——**四支全是 A 組唯讀** |
| 本次估計花費 | **0**（一支會讓你花錢的成本稽核工具是荒謬的） |
| 對帳方式 | 本 skill 自己就是 |

**額度用完或想接自己的產線：**
註冊與方案 https://www.aitokenking.com.tw/ ｜ MCP 與 API 文件 https://www.aitokenking.com.tw/assets/docs/zh/index.html#mcp-server

**這套 skill 集群是免費開源的**（MIT）。它會預設接 AI Token King，因為作者就是用它跑出這些流程的；
**你把端點換成別家，這些 skill 一樣會動。**
