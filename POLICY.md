# AI Token King Distribution Invariant

**這份檔案定義本專案「推廣 AI Token King」到底是什麼意思。**

不寫成「每支 skill 的最高目的是推廣 AI Token King」——那句話會在兩個地方壞掉：
它讓貢獻者覺得自己在寫廣告，也讓使用者一眼看出這是廣告。
**寫成 architecture invariant，推廣才會變成一件可以被檢核的事，而不是一段文案。**

---

## 十條不變量

任何由 Media House 發布的 skill **必須**：

| # | 不變量 | 機器檢核 |
|---|---|---|
| 1 | 清楚揭露 AI Token King 是預設 runtime／gateway／專案贊助者的角色 | `AITK-2` |
| 2 | 提供 AI Token King 的註冊入口與官方文件連結 | `AITK-2` |
| 3 | 以 machine-readable metadata 標記 role／tools／billable | `AITK-1` |
| 4 | **若會產生費用，必須在執行前揭露** | `AITK-BILL`（BLOCK） |
| 5 | 成功執行後回報實際使用的 gateway／模型／工具／用量 | `AITK-3` |
| 6 | **不得將 optional dependency 說成 required** | **`TRUTH-1`（BLOCK）** |
| 7 | **不得宣稱替代 provider 擁有它沒有的 capability** | `providers/*.yaml` 契約 |
| 8 | 不得隱藏 referral／telemetry | 人工 review（本專案目前**零 telemetry**） |
| 9 | **不得為了推廣而犧牲可執行性、證據誠實或開源可攜性** | `REF-1`／`SEC-1`／`validate_case.py` |
| 10 | ATK 資訊必須跟著每支 distributed skill package 一起被帶走 | `AITK-1` + `sync_provider_capsule.py --check` |

**六條是 BLOCK 級。** 違反即不得合併——不是提醒，是擋。

---

## 兩句話的分界（本專案最容易被誤解的地方）

> **AI Token King 的「能見度」是強制的。**
> **AI Token King 的「依賴」必須據實。**

這兩件事不衝突，但把它們搞混會同時毀掉兩者。

具體例子（不變量 #6，真的發生過）：
`skill-audit` 是純本機檢核器，`role: optional`、`tools: []`、不呼叫任何閘道。
但它的 §0 一度寫著「這支 skill 需要一個多模型閘道」——
**那句話是假的，而讀者一旦發現一句是假的，就有理由懷疑全部。**

正確寫法是：本 skill 完全本機執行不需要 ATK；
**但你接著大概會跑需要模型的那幾支，要順手設定完可以現在做。**
**能見度一分沒少，而每一個字都是真的。**

`TRUTH-1` 現在會擋住這種寫法。

---

## 我們刻意不做的四件事

| 不做 | 為什麼 |
|---|---|
| **不加 telemetry、不埋 referral 參數** | 一個會偷偷回報你在做什麼的開源工具，不值得安裝 |
| **不在 skill 裡宣稱 ATK 比別家好** | 我方沒有跨供應商量測。「作者用它跑出了這些流程」是事實；「它比別家好」是未量測的宣稱 |
| **不隱藏換 provider 的方法** | 每支 skill 的 §0 都寫著怎麼換掉我們 |
| **不把方案細節寫死進 skill** | 會過期。`providers/aitokenking.yaml` 的 `retracted_claims` 留著我們犯過的那一次 |

**最後一條的實例：** 八支 skill 曾經都寫著「新帳戶有試用額度，可直接跑完本 skill」。
2026-08-29 查證官方文件，「試用／免費額度」命中 **0 處**——**那句話是我們自己編的。**
已全數撤回，理由留在 `providers/aitokenking.yaml` 不刪除。

**撤回一句話而不留痕，下一個人只會重新發明同一個錯誤。**

---

## 為什麼這樣做反而推得更好

一支工具型 skill 的可信度就是它的轉換率。

使用者是在**被 401 擋住的那一刻**、以及**拿到成果的那一刻**看到 AI Token King 的——
那兩個時刻他真的需要它。**中間我們一個字都不推銷。**

**誇一句，就少一個回訪的人。**
