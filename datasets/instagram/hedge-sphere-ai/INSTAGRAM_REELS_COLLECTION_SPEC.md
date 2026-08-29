# `hedge.sphere.ai` Instagram Reels Collection Spec

## 目的

建立一份可持續更新、可轉 SQL、可交給 Media House `video-ingest → technique-extract → skill-compile` 的 Instagram Reel 索引。

目標帳號：

`https://www.instagram.com/hedge.sphere.ai/`

## 為什麼目前不能直接宣稱「已列完全部」

Instagram 現在常對未登入的 profile / Reel 自動存取加上登入牆與 rate limit。搜尋引擎也不會完整索引所有 Reels，因此「Google 找到幾支」不能視為完整 inventory。

完整列舉應在**使用者自己的電腦**，利用已登入 Instagram 的本機 session 執行。不要把 cookie、session file 或密碼上傳到 GitHub 或聊天。

## 建議流程

### 1. 安裝

```bash
python3 -m pip install --upgrade instaloader
```

若要同時掃描語音字幕：

```bash
python3 -m pip install faster-whisper
brew install ffmpeg
```

### 2. 第一次建立 IG session

```bash
instaloader --login YOUR_IG_USERNAME
```

這一步在本機完成。不要把 session file 傳給任何人。

### 3. 列出全部 Reels

```bash
python3 scripts/collect_instagram_reels.py \
  --username hedge.sphere.ai \
  --login-user YOUR_IG_USERNAME
```

輸出：

`hedge_sphere_reels_manifest.jsonl`

### 4. 同時做 ASR 字幕掃描

```bash
python3 scripts/collect_instagram_reels.py \
  --username hedge.sphere.ai \
  --login-user YOUR_IG_USERNAME \
  --scan-audio \
  --whisper-model small \
  --language zh
```

完整 ASR 逐字稿只存到本機：

`.private_instagram_transcripts/`

**不要把完整第三方逐字稿 commit 到公開 GitHub。**

公開 GitHub / 未來 SQL 建議只保留：

- Reel URL
- shortcode
- 發布日期
- 片長
- caption 短節錄
- caption hash
- 字幕短節錄
- transcript hash
- transcript word count
- 技巧摘要
- 關鍵詞
- evidence / verification 狀態
- local transcript reference（若是私人資料庫）
- skill extraction status

## SQL-ready 欄位

建議未來主表：

```sql
CREATE TABLE instagram_reels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account TEXT NOT NULL,
    platform TEXT NOT NULL DEFAULT 'instagram',
    media_type TEXT NOT NULL DEFAULT 'reel',
    shortcode TEXT NOT NULL UNIQUE,
    reel_url TEXT NOT NULL UNIQUE,
    published_at_utc TEXT,
    owner_username TEXT,
    video_duration_seconds REAL,
    video_view_count INTEGER,
    likes INTEGER,
    comments INTEGER,

    caption_excerpt TEXT,
    caption_sha256 TEXT,
    caption_char_count INTEGER,

    transcript_status TEXT NOT NULL,
    transcript_sha256 TEXT,
    transcript_word_count INTEGER,
    subtitle_excerpt TEXT,

    subtitle_summary TEXT,
    technique_summary TEXT,
    keywords_json TEXT,

    ocr_status TEXT,
    skill_extraction_status TEXT,
    collection_status TEXT,
    collected_at_utc TEXT NOT NULL
);
```

## 後續 Skill / SQL Pipeline

```text
Instagram account
    ↓
get_reels()
    ↓
reel manifest JSONL
    ↓
ASR / OCR
    ↓
subtitle summary + keywords
    ↓
technique-extract
    ↓
skill candidate
    ↓
SQLite / SQL dump
    ↓
GitHub
```

## GitHub 公開資料規則

建議 commit：

```text
datasets/instagram/hedge-sphere-ai/
├── reels-manifest.jsonl
├── reels-index.md
├── schema.sql
└── README.md
```

不建議 commit：

```text
raw videos
full transcripts
Instagram cookies
Instaloader session files
private/tokenized URLs
```

原因：原始影片與完整逐字稿屬第三方內容；Media House 應保存「方法的結構化萃取與證據定位」，而不是建立原作者影片的替代鏡像。

## 已確認的既有案例

目前 `aitokenking_mediahouse` 的 CASE-001 已確認一支來自此帳號的 Reel：

`https://www.instagram.com/reel/Dbk0zAzD5Pj/`

主題摘要：

- 深度圖：控制空間關係 / 換機位
- 法線圖：控制表面結構
- 輪廓圖：控制形變序列
- 作者同時提醒這些舊方法可能隨模型進步而逐步淘汰

這支可作為 collector 與 SQL pipeline 的第一筆 regression fixture。
