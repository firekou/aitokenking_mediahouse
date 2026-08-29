# `hedge.sphere.ai` Reels 採集規格 —— ⛔ 已由 Apify 路線取代

> **狀態：SUPERSEDED（2026-08-29，Frank 拍板「使用 Apify 的 API」）**
> **canonical 實作：** [`scripts/ig_harvest.py`](../../../scripts/ig_harvest.py)
> **canonical 規格：** [`skills/catalog-harvest/SKILL.md`](../../../skills/catalog-harvest/SKILL.md)
> **canonical schema：** [`schemas/reel-catalog.sql`](../../../schemas/reel-catalog.sql)
>
> 原本的 instaloader ＋ 本機 whisper 實作（`scripts/collect_instagram_reels.py`）
> **已移除**，內容仍可由 git 歷史取回（commit `1d35ae3`）。

---

## 為什麼改走 Apify

不是因為原方案不好，是因為**同一件事有兩份規格，改一次就會分岔一份**——
而分岔的那一份不會報錯，只會在某個人照著做的時候壞掉。

兩條路線的實質差異：

| | Apify（採用） | instaloader ＋ 本機 whisper（退役） |
|---|---|---|
| 取數 | 第三方平台代取 | 使用者本機**已登入的 IG session** |
| 逐字稿 | actor 的 `includeTranscript` 加購 | 本機 faster-whisper |
| 在 CI／遠端可跑 | ✅ | ❌ 需要人在自己機器上、且已登入 |
| 前置安裝 | 無 | instaloader ＋ ffmpeg ＋ whisper 模型 |
| 成本 | 逐支計費（129 支含逐字稿實測 US$8.8） | 免費，但要自己的機器與時間 |

**決定性的一點：本集群是要給陌生創作者下載使用的。**
一條需要「先安裝三個套件、再登入自己的 IG、還要有一台跑得動 whisper 的機器」的路徑，
大多數人會停在第一步。**能被執行的路徑，勝過理論上更好的路徑。**

---

## ★ 這份規格裡被保留下來的東西

退役的是實作，不是想法。以下三項**優於**我方原設計，已併入 `schemas/reel-catalog.sql`：

### 1. `transcript_sha256` / `caption_sha256` —— 存指紋不存內容

**這是本規格最好的一個想法。** 它同時解決兩件事：

- 可以證明「我分析的是**哪一版**逐字稿」——三個月後有人質疑結論，你拿得出對照依據
- **而且不必把逐字稿本身發布出去**，直接服務 `CONTRIBUTING.md` §來源紀律

逐字稿本體留在 `ig_reel_transcript`（不進 git），雜湊留在 `ig_reel`（可公開）。

### 2. `transcript_excerpt` —— 短節錄（≤120 字）

§來源紀律允許「節錄支撐判定所必需的原話」。有節錄，目錄本身就有最低限度的可讀性，
不必每次都去翻不在 git 裡的檔案。

### 3. `transcript_status` 四態

`ok` ／ `unknown`（我們沒拿到）／ `fail`（這支確實沒有）／ `not_requested`。

⚠️ **目前 `fail` 不會被填**——Apify 的回應無法區分「這支沒有語音」與「ASR 失敗」，
所以一律留在 `unknown`。**寧可留在 unknown，也不要宣稱一件我們分不出來的事。**

---

## 未採用、但值得記下來的一條

原規格建議「完整列舉應在使用者自己的電腦、用已登入的 session 執行」，
並明確要求不要把 cookie／session file 上傳。**這個安全姿態是對的。**

我方選擇的是更保守的版本：`catalog-harvest` 的紅線第 1 條寫的是
**「不接受任何登入憑證、不偽造 session」**——
把憑證這件事整個移出我們的責任範圍，而不是「小心地處理它」。

**兩者都合規，差別在於一個是紀律，一個是結構。結構比紀律可靠。**
