# CASE-002 · @hedge.sphere.ai 短影音目錄

**帳號：** https://www.instagram.com/hedge.sphere.ai/ （刺蝟星球）
**目標：** 把這個帳號的全部 Reel 盤成可查詢的目錄——網址、文案、逐字稿、指標——並輸出 SQL。
**狀態：** ✅ **全帳號盤點完成**（2026-08-29）

| | |
|---|---|
| 總支數 | **129 支**（發布期間 2026-02 ~ 2026-08） |
| 逐字稿 | **120 支 `ok`／9 支 `unknown`**（⚠️ unknown 是「我們沒拿到」，不是「這支沒有字幕」） |
| 實際花費 | **US$8.4780**（探底 $0.1802 ＋ 全量 $8.4780） |
| 片長 | 中位數 93s｜最短 6s｜最長 207s｜計費分鐘合計 254 |
| 逐字稿品質 | **已人工回看 5 支** → [`transcript-quality-review.md`](transcript-quality-review.md) |
| 驗收條件 | ✅ **通過**（見下） |

### ★ 「先探底再全量」值得每次都做

| 估法 | 數字 | 誤差 |
|---|---|---|
| 天真估價（`--limit 200` × 平均 2 分） | $13.8810 | +64% |
| **探底後用逐支真實片長算** | **$8.8176** | **+4%** |
| 實際扣款 | $8.4780 | — |

**探底（不含逐字稿）只花 US$0.1802**，換到一個誤差 4% 的估價。
而那 4% 有精確解釋：**9 支沒產出逐字稿，共 10 個計費分鐘 × $0.034 = $0.3400**，
與估實差額 $0.3396 完全吻合——**估價本身是準的。**

> **⚠️ `resultsLimit` 不是「最新 N 支」**，回傳順序不可預期。要特定期間用 `--newer-than`。
> 本次用 `--limit 200` 取回 129 支——**129 是這個帳號當下的全部，不是被截斷的結果**
> （上限給到 200 仍只回 129）。

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
| `raw-reels.json` | 網址／文案／指標／`has_transcript` 標記 | ✅ **是**——**已在來源層剝除逐字稿** |
| `raw-transcripts.json` | 完整逐字稿原始檔 | ⛔ **否**（`.gitignore`） |
| `catalog.sql` | `ig_harvest_run` ＋ `ig_reel` | ✅ **是**——它是指向原片的索引 |
| `transcripts.sql` | `ig_reel_transcript` | ⛔ **否**（`.gitignore`） |

**★ 拆在來源層而不只是 SQL 層，是首次真跑時撞出來的修正。**
原設計只拆了 SQL，但 `raw-reels.json` 仍帶著全部逐字稿而它要進 git——
**等於從後門違反了 §來源紀律。** 現已有回歸測試鎖死。

---

## ✅ 驗收條件（已通過）

**條件：這批資料必須包含 `Dbk0zAzD5Pj`，且 `duration_s` 約 109 秒。**

首批 5 支未含該片（`resultsLimit` 不是取最新），故**另外針對性抓了那一支驗證**（US$0.004）：

```
shortCode  : Dbk0zAzD5Pj
帳號       : hedge.sphere.ai        ✅ 帳號歸屬正確
duration   : 110.333336 s           ✅ 我方 CASE-001 實測 109s，差 1.3s 在容差內
```

**兩件事因此同時被驗證：抓對了帳號，且 Apify 的欄位對得上我方既有量測。**

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

## ✅ 73 支 WORTH_SKILL 全部處理完畢（2026-08-29）

**規則萃取的草稿全部清空，但不是被腳本晉升的——是被人逐支重寫的。**
每一支都經過：人工重讀逐字稿 → 改寫步驟 → 補上作者沒講的邊界 → 標出 ASR 誤聽 → 跨影片交叉比對。

| | 支數 |
|---|---|
| 分類器判 `WORTH_SKILL` | 73 |
| 已在 CASE-001 發布（`Dbk0zAzD5Pj`，同帳號） | −1 |
| FP-1 業配廣告（人工判定不做） | −1 |
| DUP-1／DUP-2 重複（合併進既有 skill） | −2 |
| **本案例產出 skill** | **69** |

**★ 這是分類器第一次有真實的準確率數字，但只有一半：**

| | 數值 | 為什麼 |
|---|---|---|
| **WORTH_SKILL 側的精確率** | **72/73 ＝ 98.6%** | 73 支全部人工讀過，只有 FP-1 一支是誤判 |
| **召回率** | **⛔ 未量測** | **47 支 `OPINION_ONLY` 一支都沒有人讀過**——不知道裡面有沒有被漏掉的技巧片 |

**只報精確率不報召回率，會讓這把尺看起來比實際好。**
`classifier_error_rate` 因此**維持 `UNMEASURED`，不因為跑完一輪就升格**——
量到的是「判 YES 的裡面有幾個對」，不是「該判 YES 的有幾個被判到」。
要補召回率，得把 47 支 `OPINION_ONLY` 也人工讀完，這件事還沒做。

**★ 三筆人工判定全部只有人讀才抓得到**（見 [`human-review-log.md`](human-review-log.md)）：
規則數得出「有沒有動作句」，數不出「這些動作屬於誰」（FP-1），
也數不出「這兩支是不是同一支」（DUP-1／DUP-2）。

**★ 逐字稿品質的結論在 69 支上再次被證實：**
`Seedance` 累積出**十一種**錯拼、`Higgsfield` 四種、
`LTX Studio` 出現 `OTX Studio`／`RTX注定有` 兩種寫法、
`可靈` 出現 `C-Lens`／`可琳Omini`／`可怜的OMINI` 三種。
**否定詞脫落也再次出現**：`DY3IkbwiDon` 把「第一件要做的」寫成「第一不要做的」——
語意完全反轉，而句子讀起來完全通順。
**每一支 skill 都附了 ASR 修正表且刻意不刪除原文**，理由是：
改掉逐字稿而不留痕，下一個人就無法判斷哪幾個字是我們動過的。

---

## 已知缺口

| ID | 缺口 | 為什麼重要 |
|---|---|---|
| ~~C2-G1~~ | ~~逐字稿品質零實測~~ **✅ 已關閉** | 5 支人工回看完成。**結構可用、專有名詞不可用**——`tools_seen` 不得單獨由逐字稿填。詳見 [`transcript-quality-review.md`](transcript-quality-review.md) |
| C2-G2 | 該帳號實際有幾支 Reel 未知 | `--limit 200` 是猜的。**新資訊：`resultsLimit` 不是取最新 N 支，順序不可預期** |
| **C2-G5** | **估價方法會系統性偏低** | 計費是「逐支進位後相加」，估價是「平均 × 支數」。本次實際 11 分鐘、估價用 10。`--tier` 預設 FREE（最貴）抵銷此方向 |
| **C2-G6** | **plan → tier 對照僅驗證一組** | 帳單反推確認 `SCALE = SILVER`（算術完全吻合）。其餘 plan 未驗，**不得類推** |
| C2-G3 | `video_url` 是 CDN 簽名網址，數小時後失效 | 別把它當永久連結存。要留影片得另外下載（`--with-video`，本 skill 刻意不開） |
| **C2-G4** | **分流判準只量到一半** | 73 支 `WORTH_SKILL` 全部人工讀過 → **精確率 72/73**；但 **47 支 `OPINION_ONLY` 一支未讀 → 召回率 `UNMEASURED`**。`classifier_error_rate` 不因跑完一輪而升格 |
| **C2-G7** | **去重完全靠人** | `triage.json` 的 verdict 值域有 `DUPLICATE` 但分類器未實作。兩組重複（DUP-1 同主題／DUP-2 同一支二次上傳）都是人讀抓到的。**不做自動合併是刻意的**——能抓 DUP-2 的相似度門檻抓不到 DUP-1，放寬到能抓 DUP-1 就會誤殺同系列不同集數 |

**C2-G1 是最該先關掉的一個。** 如果 Apify 的中文逐字稿誤字率高到不能用，
整條「順便掃字幕」的路線就要改回自己下載跑 ASR（成本結構完全不同）。
**這件事一支影片就驗得出來，不要等抓完 200 支才發現。**
