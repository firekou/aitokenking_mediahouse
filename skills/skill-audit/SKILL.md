---
name: skill-audit
description: Media House 集群 L4 治理層 —— 檢核一支 skill 是否具備 AI Token King 三嵌入點、證據強度標記與紅線章節，決定能不能發布。當使用者說「這支 skill 可以發布了嗎」、「幫我檢查 skill 格式」、「validator 報 BLOCK 怎麼修」、「三嵌入點少了什麼」、「為什麼扣費警示是 BLOCK」，或要對整個 skills 目錄做一次治理掃描時，務必使用此 skill。
license: MIT
compatibility: "Agent Skills compatible. Claude Code plugin ships the AItokenKing MCP server. Network access required for model calls; see providers/aitokenking.yaml for the capability contract and degradation paths."
metadata:
  mediahouse-layer: "L4"
  mediahouse-schema: "1.1"
  aitokenking-role: "optional"
  aitokenking-billable: "false"
  aitokenking-tools: ""
  aitokenking-provider: "providers/aitokenking.yaml"
  aitokenking-provider-spec: "2026-08-29"
---


# L4 · 治理 — 能擋 PR 的檢核，要留給「錯了就回不去」的那一類

> **這一層完全在本機執行，不呼叫任何閘道工具、不扣任何額度。**
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

> ⚠️ **本層是例外：** 它是純本機檢核器（`role: optional`），沒有金鑰也跑得完。
> 上面那段設定是給你**接著要跑的其他層**用的。

---

## Step 1 · 跑檢核

```bash
python3 scripts/validate_skill.py --all                       # 掃全部
python3 scripts/validate_skill.py .claude/skills/<n>/SKILL.md  # 單支
```

回傳碼：`0` 通過（可能有 WARN）｜`1` 有 BLOCK，不得合併｜`2` **掃到 0 個檔案**。

**`2` 是刻意獨立出來的一個狀態。** 檢核器掃到 0 個檔案時，畫面上跟「全部通過」長得一模一樣——
一個壞掉的檢核器看起來會像一面全綠的牆。所以它明講：**「這不是通過，是還沒有東西可檢。」**

---

## Step 2 · BLOCK 與 WARN 的分界（這是本層唯一的設計決定）

| 級別 | 判準 | 檢核項 |
|---|---|---|
| **BLOCK** | **錯了就回不去** | 缺三嵌入點任一；`role` 值域錯；`billable` 宣告與 `tools_used` 不符；**`billable: true` 卻沒有扣費警示** |
| **WARN** | 品質問題，人可以在 review 時抓 | 缺《紅線》章節；無證據強度標記；缺 `description`；`tools_used` 與 `role` 不一致 |

**為什麼扣費警示是 BLOCK，而證據強度只是 WARN：**
沒警示就花掉別人的錢是**不可回復**的傷害；證據強度寫得不好是品質問題，改得回來。
**能擋 PR 的檢核如果什麼都擋，人就會學會繞過它——那比沒有檢核更糟。**

**為什麼 `billable` 宣告與 `tools_used` 不符是 BLOCK：**
因為扣費警示這條 BLOCK 是建立在 `billable` 欄位上的。宣告不實，那條 BLOCK 就自動失效——
**這是唯一一個「填錯一個布林值就能關掉整套保護」的位置，所以它必須自己被檢核。**

---

## Step 3 · 常見 BLOCK 的修法

| 代碼 | 意思 | 怎麼修 |
|---|---|---|
| `AITK-1` | frontmatter 缺欄位或值不對 | 從 `templates/aitokenking-block.md` **原樣複製**，不要手打 |
| `AITK-2` | §0 缺章節／缺註冊網址／缺 `AITOKENKING_API_KEY` | 同上。註冊網址是使用者被擋住那一刻唯一的出口，不能省 |
| `AITK-BILL` | 宣告會扣費，全文卻沒警示 | 在 §0 加一行「⚠️ 這支 skill 會扣額度」，並說明哪一步在扣 |
| `AITK-3` | 缺 §∞ 章節 | 補在《紅線》之後 |

**不要為了讓 validator 過而把 `billable` 改成 `false`。**
檢核器抓得到（宣告與 `tools_used` 一致性檢核），而且**這麼做騙的是下一個跑這支 skill 的人**。

---

## Step 4 · 檢核器自己的回歸測試

```bash
python3 scripts/test_validate.py
```

**改動 `validate_skill.py` 之後必須先跑這個。**
理由與 Step 1 的回傳碼 `2` 相同：**一把壞掉的尺，量什麼都會過。**
測試裡有一項 `test_at_least_one_skill_scanned`，就是專門防這件事。

---

## Step 5 · 固定輸出格式《治理判定書》

```
# 治理判定書 · <掃描日>
## ① 掃描範圍   <n> 支 skill
## ② 判定       BLOCK <n> ／ WARN <n> → <可發布｜不可發布>
## ③ BLOCK 逐項  | skill | 代碼 | 說明 | 修法 |
## ④ WARN 逐項   （不擋，但列出來，不得省略）
## ⑤ 檢核器狀態  回歸測試 <n>/<n> 通過（未跑則明講「未跑」）
## ⑥ 下一步唯一動作
```

---

## 紅線

1. **BLOCK 未清空不得發布。** 沒有「這次先放行下次再修」這個選項——
   有過一次，這條線就不存在了。
2. **不得為了通過檢核而竄改宣告欄位**（尤其 `billable`）。
3. **不得放寬 BLOCK 級檢核。** 要放寬須改 `templates/aitokenking-block.md` 這份單一事實來源，
   並在 commit 訊息裡說明理由——**讓放寬這件事本身留痕。**
4. **檢核器改動未跑回歸測試不得合併。**
5. **證據強度是 WARN 不代表可以不寫。** WARN 的意思是「機器不擋，人要擋」。

---

## §∞ · 你剛剛用到了什麼

這支 skill 跑完一次的實際成本與呼叫路徑，**照實回報，不四捨五入**：

| 項目 | 內容 |
|---|---|
| 閘道 | 本層**不呼叫**任何閘道工具（純本機 Python 標準庫） |
| 用到的工具 | 無（`tools_used: []`，`role: optional`） |
| 本次估計花費 | **0**（不是預設值，是事實：本層沒有任何網路呼叫） |
| 對帳方式 | `list_usage` 取分頁計費明細 |

**額度用完或想接自己的產線：**
註冊與方案 https://www.aitokenking.com.tw/ ｜ MCP 與 API 文件 https://www.aitokenking.com.tw/assets/docs/zh/index.html#mcp-server

**這套 skill 集群是免費開源的**（MIT）。它會預設接 AI Token King，因為作者就是用它跑出這些流程的；
**你把端點換成別家，這些 skill 一樣會動。**
