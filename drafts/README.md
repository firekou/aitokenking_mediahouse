# `drafts/skills/` —— 草稿暫存區（目前是空的）

**空的，而且空得有理由。**

`/catalog-harvest` 與規則萃取產生的 skill 草稿放在這裡，
`status: draft`、`verification: V0`，**不會**被 plugin 安裝的人拿到。

CASE-002 的 73 支草稿已在 2026-08-29 全部處理完畢
（人工逐支重寫並移入 `skills/`，判定過程見
`cases/CASE-002-hedge-sphere-catalog/human-review-log.md`）。

## 這個檔案存在的唯一理由

**git 不追蹤空目錄。**
最後一支草稿被移走的那一刻，`drafts/` 整個從版本庫消失，
而 `skill-dashboard/Dockerfile` 有一行 `COPY drafts/ /app/drafts/` ——
**建置立刻失敗，錯誤訊息是 `"/drafts": not found`。**

失敗的是部署不是程式，而且是在「所有測試都綠、所有檢核都過」之後才炸的：
`validate_skill.py --drafts` 掃到 0 個檔案時已經會明講「這不是通過，是還沒有東西可檢」，
但**沒有任何一支測試在檢查「Dockerfile 要 COPY 的路徑是不是真的存在」**。

已補 `scripts/test_registry.py` 的回歸測試：
**解析 Dockerfile 的每一行 COPY，逐一確認來源路徑在 repo 裡存在。**
下次有人刪掉最後一個檔案，測試會先紅，不會等到部署才發現。

## 晉升規則沒有變

草稿要進 `skills/` 必須人做四件事，不是腳本做：

1. 人工重讀逐字稿（ASR 對專有名詞與否定詞系統性不可靠）
2. 抽幀讀圖把工具名從 E5 升到 E1
3. 補 `boundary` 與 `pitfalls`
4. 重寫成正式格式並過 `validate_skill.py`

**晉升是人的動作，不是腳本的動作。**
