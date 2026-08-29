# CASE-002 · @hedge.sphere.ai 短影音目錄

**帳號：** https://www.instagram.com/hedge.sphere.ai/ （刺蝟星球）
**目標：** 把這個帳號的全部 Reel 盤成可查詢的目錄——網址、文案、逐字稿、指標——並輸出 SQL。
**狀態：** ⏸ **管線已完成並測過，等 `APIFY_TOKEN`。目前尚無任何真實資料。**

> **⚠️ 這個資料夾現在是空的，而空不等於零。**
> 沒有 `raw-reels.json`、沒有 `catalog.sql`，代表**還沒抓**，
> 不代表這個帳號沒有影片。兩者在畫面上長得一模一樣，所以這裡明講。

---

## 為什麼卡住

Instagram 對未登入請求的實測（2026-08-29）：

| 請求 | 結果 |
|---|---|
| `GET instagram.com/hedge.sphere.ai/` | **HTTP 302** → `/accounts/login/?next=...` |
| `GET i.instagram.com/api/v1/users/web_profile_info/` | **HTTP 401** `{"require_login": true}` |
| 對照組 `example.com` | HTTP 200 |
| 對照組 `api.apify.com` | 可達（401 僅表示未帶 token） |

**對照組證明網路沒問題——是 Instagram 自己擋的。**
繞過它（偽造 session、輪換 IP、住宅代理）違反紀律
「對方明確不想要你做的事，不看它用哪一層擋你」。
**所以走 Apify，這是外包不是繞過**，代價已寫進揭露欄位。

---

## 補上 token 之後，三行跑完

```bash
export APIFY_TOKEN='apify_api_...'      # https://console.apify.com/settings/integrations

# ① 估價（不送出、不扣款）——先看要花多少
python3 scripts/ig_harvest.py hedge.sphere.ai --limit 200

# ② 真的抓（網址＋文案＋逐字稿）
python3 scripts/ig_harvest.py hedge.sphere.ai --limit 200 --run \
    --with-transcript --i-understand-transcript-policy \
    --out cases/CASE-002-hedge-sphere-catalog/raw-reels.json

# ③ 產 SQL
python3 scripts/build_catalog_sql.py cases/CASE-002-hedge-sphere-catalog/raw-reels.json
```

產出：

| 檔案 | 內容 | 進 git？ |
|---|---|---|
| `raw-reels.json` | Apify 原始回應（正規化後） | ✅ 是（不含逐字稿以外的敏感內容） |
| `catalog.sql` | `ig_harvest_run` ＋ `ig_reel`：網址／文案／指標 | ✅ **是**——它是指向原片的索引 |
| `transcripts.sql` | `ig_reel_transcript`：完整逐字稿 | ⛔ **否**（`.gitignore`），見下 |

---

## ★ 一個現在就能寫下的驗收條件

**這批資料抓回來時，必須包含 `Dbk0zAzD5Pj`，且 `duration_s` 約 109 秒。**

那是 [CASE-001](../CASE-001-control-map/) 的來源影片，我方已獨立實測過片長（E1）。
它同時驗兩件事：①抓對了帳號 ②Apify 的欄位對得上我方既有量測。

**對不上就停下來查，不要繼續往下跑。**
抓到錯的帳號是這類系統最嚴重的錯——因為它不會報錯，只會給你一份看起來很正常的目錄。

**順帶：** CASE-001 是我方手動處理的第一支。抓回來後把該列的
`case_id` 設為 `CASE-001`、`pipeline_state` 設為 `PUBLISHED`，目錄與產線就接上了。

---

## 為什麼逐字稿分開存

`CONTRIBUTING.md` §來源紀律白紙黑字寫過：**「不整支影片逐字重製發布」**。
CASE-001 就是照這條刻意只收節錄、不收完整逐字稿的。

那條線是這樣畫的：

| | |
|---|---|
| **目錄可以公開** | 它是**指向原片的索引**，會把人帶回去看原作者 |
| **完整逐字稿不行** | 它讓**原片變得沒必要看** |

所以：
- schema 拆三張表，逐字稿獨立（放同一張表，任何 `SELECT *` 匯出都會把它帶走）
- 產生器預設輸出兩個檔，`transcripts.sql` 進 `.gitignore`
- 採集器要抓逐字稿需**兩個**旗標——沿用 `brand-intelligence/connectors/apify.js` 的不對稱開關：
  **新增一項資料源，跟推翻一條已經寫下來的紀律，不該是同一個動作。**

**逐字稿本身抓沒問題**——它是我方分析的原料，是 L2 萃取的輸入。
不能做的是把它整批當成內容發布。

---

## 成本

以 Apify FREE 級價目估（即時查得，as-of 2026-08-29）：

| 支數 | 只要網址＋文案 | 含逐字稿（平均 2 計費分鐘） |
|---|---|---|
| 60 | US$ 0.16 | **US$ 5.92** |
| 200 | US$ 0.52 | **US$ 19.40** |

**逐字稿是成本大宗，且按「開始的分鐘」計費——109 秒＝2 個計費分鐘，不是 1.8 個。**
⚠️ 價目會變（Apify 自 2024-05 已改過六次計價模型）。`PRICING` 常數標了 `measured_at`，**過期重查**。

---

## 已知缺口

| ID | 缺口 | 為什麼重要 |
|---|---|---|
| **C2-G1** | **Apify 逐字稿品質我方零實測**（E6） | 未揭露用哪套 ASR。`video-ingest` 對自家 ASR 列得出誤字表（Control Night＝ControlNet），對 Apify 的**一次都沒對過**。第一批抓回來先人工回看兩三支——`asr_reviewed` 預設 0 就是為此 |
| C2-G2 | 該帳號實際有幾支 Reel 未知 | `--limit 200` 是猜的。第一次跑完才知道要不要調 |
| C2-G3 | `video_url` 是 CDN 簽名網址，數小時後失效 | 別把它當永久連結存。要留影片得另外下載（`--with-video`，本 skill 刻意不開） |
| C2-G4 | Step 4 分流判準未在真實資料上校準 | 「動作句 < 3 句」的門檻沿用 `/technique-extract`，未在本帳號驗過 |

**C2-G1 是最該先關掉的一個。** 如果 Apify 的中文逐字稿誤字率高到不能用，
整條「順便掃字幕」的路線就要改回自己下載跑 ASR（成本結構完全不同）。
**這件事一支影片就驗得出來，不要等抓完 200 支才發現。**
