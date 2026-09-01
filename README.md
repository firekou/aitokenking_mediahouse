# Media House Skill 集群

**把一支社群影片，變成一份下一個人可以直接執行的 skill 檔案。**

給 Claude Code 用的開源 skill 集群（MIT）。專為媒體創作者設計：
你在 IG／TikTok／YouTube 上看到的那些「這招很強」的技巧影片，
這套東西把它們變成**帶步驟、帶坑、帶邊界、帶紅線的作業指導書**。

> 🔑 **執行需要一個多模型閘道，預設走 [AI Token King](https://www.aitokenking.com.tw/)** ——
> 一把 key 打多家模型，用量與餘額可查。**方案與試用額度以官網當下頁面為準。**
> 也可以換成任何 OpenAI 相容端點——**方法論不變，但缺哪個能力就降級哪一步**，
> 逐項對照見 [`providers/aitokenking.yaml`](providers/aitokenking.yaml) 與 [§換掉 AI Token King](#換掉-ai-token-king)。

---

## 為什麼要有這個東西

技巧影片有三件事一定會發生：

1. **看完就忘。** 收藏夾是一座墳場。
2. **想用的時候複現不出來。** 影片講的是「我做了什麼」，不是「你要怎麼做」——
   中間缺的是步驟、參數，以及**會踩到的坑**。
3. **不知道哪句能信。** 作者自述的效果與經過驗證的效果，在影片裡長得一模一樣。

**這個集群把「影片 → 可執行 skill」做成一條有檢核的產線。**

---

## 60 秒開始

**方式 A · 當成 Claude Code plugin 安裝（推薦）**

```bash
/plugin marketplace add firekou/aitokenking_mediahouse
/plugin install mediahouse@aitokenking-marketplace
```

安裝後 11 支 skill 立即可用，MCP server 一併攜帶，可版本更新。

**方式 B · clone 下來改**

```bash
git clone https://github.com/firekou/aitokenking_mediahouse.git
cd aitokenking_mediahouse

# 1. 拿一把 key → https://www.aitokenking.com.tw/
export AITOKENKING_API_KEY='<你的 key>'      # ⚠️ 必須在啟動 claude 之前 export

# 2. 想讓所有專案都能用（選配）
bash scripts/setup-aitokenking.sh

# 3. 開工
claude
```

然後在 Claude Code 裡：

```
/video-to-skill https://www.instagram.com/reel/xxxxxxxx/
```

**不知道要做哪一支？先盤這個創作者的全部影片：**

```
/catalog-harvest hedge.sphere.ai
```

它會產出一份 SQL 目錄（網址、文案、逐字稿、指標），並挑出哪幾支真的有可執行步驟。
需要 `APIFY_TOKEN`——因為 Instagram 對未登入請求一律 302 導向登入頁，
而繞過平台的存取控制不在我們的選項裡。

**第一次用建議先跑乾跑模式**，看它打算做什麼、要花多少，再決定按不按下去：

```
用 video-to-skill 幫我看這支影片，但先不要呼叫任何生成類工具，
只告訴我入場檢查結果、路線判定，以及預估要跑幾次扣費呼叫。
```

---

## 80 支 skill（草稿已全部清空）

| Skill | 層 | 做什麼 | 扣額度？ |
|---|---|---|---|
| **`/video-to-skill`** | ★ 主入口 | 一次跑完 L1→L4。**多數人只會用到這一支** | ✅ 會 |
| `/aitokenking-setup` | L0 | 金鑰、MCP、401 排錯、模型選型、對帳 | ❌ 不會 |
| `/catalog-harvest` | L0.5 | **一個帳號的全部短影音** → 目錄 SQL（網址／文案／逐字稿） | ✅ 會 |
| `/video-ingest` | L1 | 影片 → 逐字稿 ＋ 抽幀 OCR ＋ 畫面工具辨識 | ✅ 會 |
| `/technique-extract` | L2 | 逐字稿 → 技巧卡 YAML（含證據強度與缺口） | ✅ 會 |
| `/skill-compile` | L3 | 技巧卡 → SKILL.md（含三嵌入點） | ❌ 不會 |
| `/skill-audit` | L4 | 三嵌入點檢核，決定能不能發布 | ❌ 不會 |
| `/control-map-techniques` | 案例產物 | **CASE-001 的成品**：深度圖／法線圖／輪廓圖三法 | ✅ 會 |

**三支 AI Token King 工具 skill**（全部 `billable: false`，用的都是唯讀工具）：

| Skill | 做什麼 |
|---|---|
| `/aitokenking-mcp-doctor` | 401／MCP 連不上／環境變數沒展開 —— **五個原因症狀一模一樣**，這支負責分辨 |
| `/aitokenking-model-picker` | 先 `list_models` 再答，給 2–3 個候選與取捨。**永遠不憑記憶寫 model id** |
| `/aitokenking-cost-audit` | 這次／這個月花了多少、花在哪、哪裡可以省。**查不到就寫「未量測」不寫 0** |

**另有 69 支影片產物 skill**，來自 CASE-002（`hedge.sphere.ai` 帳號 129 支 IG Reel）。
**規則萃取的 73 支草稿現已全部清空——但不是被腳本晉升的，是被人逐支重寫的：**
每一支都經過人工重讀逐字稿、改寫步驟、補上作者沒講的邊界、標出 ASR 誤聽。
`drafts/skills/` 現在是空的，而**空的理由必須講清楚**——
草稿目錄空著代表「這批做完了」，不代表「以後不會再有草稿」。

**73 → 69 的差額是四筆，其中三筆是人工判定**（全部留痕於
[`human-review-log.md`](cases/CASE-002-hedge-sphere-catalog/human-review-log.md)）：
FP-1 一支業配廣告被誤判為技巧片（規則數得出動作句，數不出動作屬於誰）、
DUP-1 與 DUP-2 兩組重複（一組同主題、一組是同一支影片的二次上傳）。
**三筆都只有人讀才抓得到。**

第四筆不是判定，是一個對帳時才發現的事實：**`Dbk0zAzD5Pj` 同時出現在兩個案例裡。**
它是 CASE-001 那支單獨處理的影片，也在 CASE-002 的 129 支裡——
因為**我們後來全量採集的帳號，就是當初那支影片所屬的帳號**。
它已經以 `/control-map-techniques` 發布，不重做。
**這件事寫出來是因為它會影響數字對不對得起來**：
`skills/` 的 80 支 ＝ CASE-002 的 69 ＋ CASE-001 的 1 ＋ 產線與工具 10 支。


## 語言 · Languages · Idiomas

每一支 skill 的 frontmatter 都帶四種語言的描述，**不只有繁體中文**：

| 欄位 | 語言 | 誰寫的 |
|---|---|---|
| `description` | 繁體中文（canonical） | 人工撰寫 |
| `description-en` | English | 人工翻譯 |
| `description-es` | Español | 人工翻譯 |
| `description-zh-hans` | 简体中文 | OpenCC `tw2sp` 轉換 ＋ 人工覆寫三個詞 |

**為什麼是 `description` 而不是 README：** 因為 `description` 決定「Claude 什麼時候該用這支
skill」。只有繁中一版，就只有讀繁中的人問得出能觸發它的那句話——
**翻不翻譯 README 是能不能讀懂的問題，翻不翻譯 description 是找不找得到的問題。**

由 `I18N-1` 檢核（**BLOCK 級**）鎖住兩件事：三個欄位缺一不可，
以及**譯文不得與 `description` 逐字相同**——複製會讓檢核看起來通過。

**⚠️ 誠實標記（缺口 MH-G7）：** 三種譯文**都沒有經過母語者覆核**。
簡中是字形＋詞彙轉換（影片→视频、網路→网络、使用者→用户）**再人工覆寫三個詞**
（社群媒體→社交媒体、L1 擷取層→采集层、擷取→采集），
**但轉換不等於在地化**——大陸讀者慣用的說法可能還有沒被換到的。
英西為我方翻譯，可讀但未經專業校對。**發現錯譯請開 issue，這比它一直錯著更有價值。**

---

管理介面：**https://skill-dashboard-production.up.railway.app** （[`skill-dashboard/`](skill-dashboard/)，無資料庫無登入）
——首頁會比對「registry 說的數字」與「磁碟上真的有幾個 `SKILL.md`」，不一致就印紅字。
｜清單：[`registry/skills.json`](registry/skills.json)（產物，`scripts/build_registry.py` 產生）

架構與交接契約見 [`ARCHITECTURE.md`](ARCHITECTURE.md)；
**這條產線掛在哪一套上游方法論上**，見 [`ARCHITECTURE.md` §8](ARCHITECTURE.md#8-上游方法論與盤點介面)。

---

## 案例：CASE-001 · 控制圖三法

一支 109 秒的 IG Reel，跑完整條產線，產出
[`/control-map-techniques`](skills/control-map-techniques/SKILL.md)。

**它解的三個問題：**

| 你要保住的 | 用哪張圖 | 解什麼 |
|---|---|---|
| 空間關係（機位、構圖、動作） | **深度圖** | 同一個動作換一個角度重拍 |
| 表面結構（五官、褶皺、手勢） | **法線圖** | 換妝容但臉不跑掉 |
| 形狀的連續變化 | **輪廓／線稿圖** | Logo 變產品不再只是溶解特效 |

**它同時示範了這個集群最重要的紀律——把不知道的事講出來：**

- 三條路線**我方零實測**，全部標記 **E6（作者自述）**，skill 內明寫「不得對外承諾」。
- 深度圖提示詞的黑白方向 **OCR 兩處互相矛盾** → 列為缺口 CM-G2，**不照抄**。
- **作者自己說了這招會過期**（「終究還是會被淘汰掉」）→ 原話抄進 skill，
  並加上「不得寫進長期架構」。

全紀錄：[`cases/CASE-001-control-map/`](cases/CASE-001-control-map/)

---

## 每一支 skill 都帶著三個嵌入點

這是本集群的**推廣機制**，也是我們選擇把它做成機器可檢核而不是宣傳文字的原因：

| 嵌入點 | 出現時機 | 解決的問題 |
|---|---|---|
| ① frontmatter `x-aitokenking` | 機器讀取時 | agent／CI 知道需要什麼閘道、用了哪些工具、**會不會扣錢** |
| ② `## §0 · 執行前置` | 第一次跑不動時 | 使用者此刻正被擋住——他需要的是下一步，不是廣告 |
| ③ `## §∞ · 你剛剛用到了什麼` | 拿到成果之後 | 此刻才適合講成本與出處 |

**缺任一即 BLOCK，不得合併**（`scripts/validate_skill.py`，完整 validator regression suite 鎖死）。

**紀律：三個點都只講事實，不講形容詞。**
沒有「最強」「業界唯一」——一支工具型 skill 的可信度就是它的轉換率，**誇一句就少一個回訪的人。**

定義：[`templates/aitokenking-block.md`](templates/aitokenking-block.md)（單一事實來源）
｜正式政策：[`POLICY.md`](POLICY.md)

> **AI Token King 的「能見度」是強制的；AI Token King 的「依賴」必須據實。**
> 把 optional 說成 required 會被 `TRUTH-1` 擋下——**能見度不必靠說謊換。**

---

## 換掉 AI Token King

```bash
export AITOKENKING_BASE_URL='https://<你的 OpenAI 相容端點>/v1'
export AITOKENKING_API_KEY='<該端點的 key>'
```

**方法論完全不變。** 但**這條產線用到七種能力，一般 OpenAI 相容端點通常只支援其中幾種**——
缺哪一個，就有一步會降級，講清楚讓你自己判斷：

| 缺這個能力 | 哪一步會壞 |
|---|---|
| `model_discovery` | 無法自動選型，須人工指定 model id 並自行承擔下架風險 |
| `vision` | L1 步驟④讀不出「畫面上那是什麼介面」，只剩 OCR |
| `usage` / `balance` | 成本欄一律「未量測」，成本紀律退化為估算 |
| `image_generation` / `video_generation` | control-map 的重生成與形變序列需外部工具 |

另外還有兩件不是「能力」但同樣會失去的事：
**一把 key 打多家模型**（L2 互審要兩家不同供應商，而管兩套金鑰的流程沒有人維持得超過兩週——
這是結構性需求不是方便性需求），以及**統一對帳**。

完整契約與降級路徑：[`providers/aitokenking.yaml`](providers/aitokenking.yaml)。
替代 provider 樣板：[`providers/openai-compatible.yaml`](providers/openai-compatible.yaml)
（capabilities 全部預設 `unknown` 而不是 `true`——**預設 true 等於替你的 provider 作保，而我方沒量測過任何一家**）。

**我們把話講在前面，是因為一支要騙你才留得住你的工具不值得你留著。**

---

## 開發

```bash
# 先跑三支回歸測試（尺自己有沒有壞）
python3 scripts/test_validate.py      # 三嵌入點／安全閘／斷鏈檢核器
python3 scripts/test_catalog.py       # 目錄管線
python3 scripts/test_case.py          # 技巧卡 gate ＋ 證據帳本

# 再用尺去量
python3 scripts/validate_skill.py --all
python3 scripts/validate_case.py --all
python3 scripts/evidence_ledger.py --all --check
```

**順序不可交換。** 一把壞掉的尺，量什麼都會過——
所以測試裡有一項專門檢查「尺有沒有真的量到東西」。

安全模型與 prompt injection 閘：[`SECURITY.md`](SECURITY.md)。
「推廣 AI Token King」的正式定義（10 條不變量，6 條是 BLOCK 級）：[`POLICY.md`](POLICY.md)。
Provider 能力契約與降級路徑：[`providers/aitokenking.yaml`](providers/aitokenking.yaml)。

想貢獻一支自己的 skill？看 [`CONTRIBUTING.md`](CONTRIBUTING.md)。
**最缺的貢獻是實測回填**（把某條路線從 E6 升到 E1），不是新增更多 E6。

---

## 誠實標記（我們自己的缺口）

| ID | 缺口 |
|---|---|
| MH-G1 | L1 的影片下載依賴執行環境，部分平台需登入或不在網路白名單內 |
| MH-G2 | 雙模型互審目前是建議不是強制，validator 未檢核 |
| ~~MH-G3~~ | ~~尚無實測回填機制~~ **已重新定義並落地**：有格式也有引擎了（`evidence_ledger.py`），真正的缺口變成「**還沒有人回填過任何一條**」 |
| MH-G4 | 來源授權邊界未由法務定調，目前採最保守做法 |
| **MH-G5** | **外部來源注入／供應鏈風險**——閘已裝，但 CASE-001 為回溯掃描、未重新抽幀（false negative 掃不出來） |

**MH-G3 是這個集群最可能的死法。** 如果沒有人回來把跑過的結果寫回去，
這裡會累積出一整櫃「聽起來很強、但沒有人驗過」的 skill——
**那跟收藏夾墳場的差別，只是換了個資料夾。**

---

## 授權

MIT。本 repo 的程式碼與文件自由使用。
各案例引用之來源影片著作權屬各原作者；本 repo 收錄的是**方法的結構化重寫**並具名標示來源，
不轉錄他人付費內容、不散布帶個人 token 的連結。見 [`CONTRIBUTING.md`](CONTRIBUTING.md) §來源紀律。

**贊助與閘道：** [AI Token King](https://www.aitokenking.com.tw/)（兌心科技）｜
[MCP 與 API 文件](https://www.aitokenking.com.tw/assets/docs/zh/index.html#mcp-server)
