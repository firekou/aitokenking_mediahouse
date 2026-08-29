# Skill Dashboard

管理 Media House 集群裡所有 skill 的狀態與晉升。

```bash
python3 scripts/build_registry.py        # 先產清單（產物）
python3 skill-dashboard/server.py        # 預設 :8080
```

| 路由 | 內容 |
|---|---|
| `/` | 統計磚 ＋ 案例分流 ＋ 可篩選的 skill 清單 |
| `/s/<name>` | 單支詳情：metadata、晉升條件、SKILL.md 原文 |
| `/api/state` | JSON |
| `/healthz` | 健康檢查 |

## 三條鐵律

1. **打勾是宣稱，檔案是證據。** 沒有「標記完成」按鈕。
   一支 skill 是 draft 還是 published，判定依據是它在 `drafts/` 還是 `skills/`——
   **靠打勾推進的看板，三個月後會變成一面全綠但沒有人相信的牆。**
2. **GitHub 是唯一事實來源。** 本服務不寫入任何東西。
3. **每次請求重讀檔案。** 畫面與 repo 不一致時，錯的一定是畫面。

## 一個刻意加的交叉核對

首頁會比對 **registry 說的數字** 與 **磁碟上真的有幾個 SKILL.md**，
不一致就印紅字。理由：**一份會過期而不自知的清單，比沒有清單更危險。**

## Railway 部署

**★ build context 必須是 repo 根**（`dockerfilePath: skill-dashboard/Dockerfile`）。
服務讀的是 `registry/`、`skills/`、`drafts/`、`cases/`，它們都在根目錄下——
把 context 設成 `skill-dashboard/` 會得到一個「找不到清單」的服務，
**而那個畫面跟「還沒有 skill」長得一模一樣。**

⚠️ **已知部署坑（既有服務踩過）：** `create-deployment` 的第一次部署可能早於
`dockerfilePath` 設定生效，Railway 會 fallback 到自動偵測並失敗。
**那不是 Dockerfile 的問題，是時序問題**——設好後推一個 commit 重新觸發即可。

**無環境變數、無資料庫、無登入、無第三方套件。**
逐字稿原始檔（`raw-transcripts.json`／`transcripts.sql`）被 `.gitignore` 擋在版本庫外，
因此不會進到映像檔——**部署出去的東西裡沒有任何第三方影片的完整逐字稿。**
