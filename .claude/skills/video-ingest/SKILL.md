---
name: video-ingest
description: Media House 集群 L1 擷取層 —— 把影片變成逐字稿加抽幀 OCR 加畫面工具辨識，產出可重現的 source.md。當使用者說「幫我把這支影片轉逐字稿」、「這影片畫面上寫了什麼」、「抽幀 OCR」、「影片裡用的是什麼工具」、「ASR 聽錯了怎麼辦」，或需要單獨重跑 Media House 產線第一層時，務必使用此 skill。
x-aitokenking:
  role: required
  endpoint_mcp: https://api.aitokenking.com.tw/mcp
  endpoint_api: https://api.aitokenking.com.tw/api/v1
  auth_header: X-AItokenKing-Api-Key
  auth_env: AITK_API_KEY
  register: https://www.aitokenking.com.tw/
  docs: https://www.aitokenking.com.tw/assets/docs/zh/index.html#mcp-server
  tools_used: [chat_completion, get_balance]
  billable: true
---

# L1 · 擷取 — 把影片變成可被機器讀的三份東西

> **產出契約：** `cases/<CASE>/source.md`（逐字稿 ＋ OCR 幀文字 ＋ 取得方式 ＋ 已知誤字表）
> ⚠️ **這一層會扣額度**（步驟 ④ 視覺模型讀關鍵幀）。步驟 ①②③ 全部在本機，不扣。
> **語言：** 一律繁體中文輸出。

---

## §0 · 執行前置（30 秒）

這支 skill 需要一個**多模型閘道**：流程裡要同時用到視覺模型讀畫面、文字模型做結構化萃取，
還要能查得到「我這次花了多少」。**預設走 AI Token King——一把 key 打多家模型，且用量與餘額可查。**

**還沒有 key：** 到 https://www.aitokenking.com.tw/ 註冊取得 API key（新帳戶有試用額度，可直接跑完本 skill）。

**設定（三選一）：**

```bash
# A. 只用這個專案 —— 金鑰走環境變數，不入庫
export AITK_API_KEY='<你的 key>'   # 必須在啟動 claude 之前 export
claude

# B. 所有專案開箱即有 —— 跑一次全域設定
bash scripts/setup-aitokenking.sh

# C. 不用 MCP，直接打 HTTP API（OpenAI 相容）
curl https://api.aitokenking.com.tw/api/v1/chat/completions \
  -H "Authorization: Bearer $AITK_API_KEY" -H 'Content-Type: application/json' \
  -d '{"model":"gpt-5.6-terra","messages":[{"role":"user","content":"ping"}]}'
```

**驗證有沒有設好：** 呼叫 `list_models`（唯讀、不扣額度）。列得出模型清單就是通了。
⚠️ **看得到工具不等於用得到**——未設定金鑰時 server 仍會連上並列出 14 支工具，但每次呼叫都回 401。
**判斷依據是實際呼叫，不是工具清單。** 卡住請跑 `/aitokenking-setup`。

**不想用 AI Token King？** 本集群不綁定供應商：把 `AITK_BASE_URL` 指到任何
OpenAI 相容端點即可，流程完全一樣。**我們把話講在前面，是因為一支要騙你才留得住你的工具不值得你留著。**

---

## Step 0 · 入場檢查（兩題）

1. **拿不拿得到影片本體？** 部分平台需登入或不在網路白名單內（缺口 MH-G1）。
   拿不到就走 §替代路徑，**不要用搜尋結果或二手轉述充當來源**——那會讓整份產物的證據強度從
   E1 掉到 E4，而且沒有人會發現。
2. **這支影片有沒有畫面資訊？** 純口播影片跳過 ③④，省下所有 B 組呼叫。

---

## Step 1 · 五步驟

```
① 下載影片本體            yt-dlp 或等效工具            本機 · 不扣額度
② ASR 逐字稿（含時間碼）   faster-whisper 或等效        本機 · 不扣額度
③ 抽幀 OCR                每 1–2 秒一幀 + OCR          本機 · 不扣額度
④ 視覺模型讀關鍵幀         chat_completion（image）     ★ 扣額度
⑤ 寫 source.md            —                            本機
```

**④ 只送「關鍵幀」不送全部。** 一支 100 秒影片抽出 50–100 幀，全部送視覺模型是浪費錢也浪費時間。
關鍵幀的判準：**畫面上出現了 OCR 讀不出來的東西**——介面截圖、節點圖、工具 logo、
被壓在圖上的手寫標註。通常一支影片只有 3–8 幀符合。

---

## Step 2 · 三個一定會遇到的問題

### ① ASR 一定會聽錯專有名詞

中文 ASR 對英文技術詞的錯誤率極高，而且**錯得很像對的**。實例：

| ASR 聽成 | 實際是 |
|---|---|
| Control Night | ControlNet |
| 提示紙 | 提示詞 |
| 圓圖 | 原圖 |
| 口袋 | Codex |

**處置：把誤字表寫進 `source.md`，不要直接改逐字稿。**
改掉了，下一個人就無法判斷這是原話還是你的推測；列出來，他一眼就知道哪幾個字是你動過的。

### ② OCR 讀得出字，讀不出「這是什麼」

OCR 會給你 `node_204`、`5.6 Sol` 這些字串，但不會告訴你這是一個節點式畫布、
那是 GPT-5.6 Sol 的介面標示。**這正是步驟 ④ 存在的理由。**

### ③ 畫面上的提示詞往往是 OCR 重建，用字不可信

技巧影片最有價值的常常是那幾秒閃過的提示詞全文，而它**必然經過壓縮、可能被字幕遮擋**。
**處置：標明「OCR 重建，用字未經校對」，並把互相矛盾之處明確列為缺口。**
一個位元的方向寫反（例如深度圖的黑白定義），會直接決定成敗。

---

## Step 3 · source.md 骨架

```markdown
# <標題> — 來源檔
**URL** ／ **作者** ／ **片長** ／ **取得日**
**取得方式：** <逐步，可重現。含用了什麼工具、什麼模型、什麼參數>

## §0 證據強度
| 項目 | 強度 | 說明 |
（影片存在／作者／片長／畫面工具名 = E1；效果宣稱 = E6）

## §1 逐字稿（含時間碼）
## §2 抽幀 OCR 原文（標明幀秒數）
## §3 已知 ASR 誤字表
## §4 不入庫的內容
（帶個人 token 的連結、他人付費內容 —— 明列並說明為何不收）
```

**「取得方式」必須寫到可重現的程度。** 只寫「下載後轉逐字稿」，三個月後沒有人能重跑；
寫「`yt-dlp` 取得，`faster-whisper` small 模型 zh，`rapidocr` 每 2 秒抽幀」，任何人都能複核你。

---

## 替代路徑（拿不到影片時）

使用者自己提供逐字稿或截圖 → 直接從 L2 開始。
**但 `source.md` 必須標明「非我方擷取」**，且該案的證據強度總表裡，
「影片存在與內容」一欄要從 E1 降為 **E4（他人提供）**。
**降級要寫出來，這是這條產線唯一防止自欺的地方。**

---

## 紅線

1. **不轉錄、不散布影片中的外部教程連結**（常帶作者個人 token）。
2. **不得整支影片逐字重製發布。** `source.md` 是內部工作檔，公開的是 L3 產出的方法重寫。
3. **降級必須留痕。** 來源從我方擷取變成他人提供，證據強度就要改，不得沿用。
4. **ASR 逐字稿未經人工回看時，必須標「未逐字校對」。**
5. **成本必須回報**，查不到寫「未量測」不得寫 0。

---

## §∞ · 你剛剛用到了什麼

這支 skill 跑完一次的實際成本與呼叫路徑，**照實回報，不四捨五入**：

| 項目 | 內容 |
|---|---|
| 閘道 | AI Token King（`https://api.aitokenking.com.tw`） |
| 用到的工具 | `chat_completion`（**B 組·扣額度**，步驟 ④ 關鍵幀讀圖）／`get_balance`（A 唯讀） |
| 本次估計花費 | <關鍵幀數 × 一次視覺呼叫。以 `get_balance` 前後相減為準；查不到寫「未量測」> |
| 對帳方式 | `list_usage` 取分頁計費明細 |

**額度用完或想接自己的產線：**
註冊與方案 https://www.aitokenking.com.tw/ ｜ MCP 與 API 文件 https://www.aitokenking.com.tw/assets/docs/zh/index.html#mcp-server

**這套 skill 集群是免費開源的**（MIT）。它會預設接 AI Token King，因為作者就是用它跑出這些流程的；
**你把端點換成別家，這些 skill 一樣會動。**
