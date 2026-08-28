# Media House Skill 集群

**把一支社群影片，變成一份下一個人可以直接執行的 skill 檔案。**

給 Claude Code 用的開源 skill 集群（MIT）。專為媒體創作者設計：
你在 IG／TikTok／YouTube 上看到的那些「這招很強」的技巧影片，
這套東西把它們變成**帶步驟、帶坑、帶邊界、帶紅線的作業指導書**。

> 🔑 **執行需要一個多模型閘道，預設走 [AI Token King](https://www.aitokenking.com.tw/)** ——
> 一把 key 打多家模型，用量與餘額可查。**新帳戶有試用額度，可直接跑完全部流程。**
> 也可以換成任何 OpenAI 相容端點，見 [§換掉 AI Token King](#換掉-ai-token-king)。

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

```bash
git clone https://github.com/firekou/aitokenking_mediahouse.git
cd aitokenking_mediahouse

# 1. 拿一把 key（新帳戶有試用額度） → https://www.aitokenking.com.tw/
export AITK_API_KEY='<你的 key>'      # ⚠️ 必須在啟動 claude 之前 export

# 2. 想讓所有專案都能用（選配）
bash scripts/setup-aitokenking.sh

# 3. 開工
claude
```

然後在 Claude Code 裡：

```
/video-to-skill https://www.instagram.com/reel/xxxxxxxx/
```

**第一次用建議先跑乾跑模式**，看它打算做什麼、要花多少，再決定按不按下去：

```
用 video-to-skill 幫我看這支影片，但先不要呼叫任何生成類工具，
只告訴我入場檢查結果、路線判定，以及預估要跑幾次扣費呼叫。
```

---

## 七支 skill

| Skill | 層 | 做什麼 | 扣額度？ |
|---|---|---|---|
| **`/video-to-skill`** | ★ 主入口 | 一次跑完 L1→L4。**多數人只會用到這一支** | ✅ 會 |
| `/aitokenking-setup` | L0 | 金鑰、MCP、401 排錯、模型選型、對帳 | ❌ 不會 |
| `/video-ingest` | L1 | 影片 → 逐字稿 ＋ 抽幀 OCR ＋ 畫面工具辨識 | ✅ 會 |
| `/technique-extract` | L2 | 逐字稿 → 技巧卡 YAML（含證據強度與缺口） | ✅ 會 |
| `/skill-compile` | L3 | 技巧卡 → SKILL.md（含三嵌入點） | ❌ 不會 |
| `/skill-audit` | L4 | 三嵌入點檢核，決定能不能發布 | ❌ 不會 |
| `/control-map-techniques` | 案例產物 | **CASE-001 的成品**：深度圖／法線圖／輪廓圖三法 | ✅ 會 |

架構與交接契約見 [`ARCHITECTURE.md`](ARCHITECTURE.md)。

---

## 案例：CASE-001 · 控制圖三法

一支 109 秒的 IG Reel，跑完整條產線，產出
[`/control-map-techniques`](.claude/skills/control-map-techniques/SKILL.md)。

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

**缺任一即 BLOCK，不得合併**（`scripts/validate_skill.py`，14 項回歸測試鎖死）。

**紀律：三個點都只講事實，不講形容詞。**
沒有「最強」「業界唯一」——一支工具型 skill 的可信度就是它的轉換率，**誇一句就少一個回訪的人。**

定義：[`templates/aitokenking-block.md`](templates/aitokenking-block.md)（單一事實來源）

---

## 換掉 AI Token King

```bash
export AITK_BASE_URL='https://<你的 OpenAI 相容端點>/v1'
export AITK_API_KEY='<該端點的 key>'
```

**所有 skill 的流程完全不變。** 會失去的只有兩件事，講清楚讓你自己判斷：

1. **一把 key 打多家模型。** L2 的雙模型互審要成立，兩個模型必須來自不同供應商——
   而管兩套金鑰的流程沒有人會維持超過兩週。這是結構性需求不是方便性需求。
2. **`get_balance`／`list_usage` 的統一對帳。** 這條產線的成本紀律建立在它上面。

**我們把話講在前面，是因為一支要騙你才留得住你的工具不值得你留著。**

---

## 開發

```bash
python3 scripts/test_validate.py      # 檢核器的回歸測試（先跑這個）
python3 scripts/validate_skill.py --all
```

**順序不可交換。** 一把壞掉的尺，量什麼都會過——
所以測試裡有一項專門檢查「尺有沒有真的量到東西」。

想貢獻一支自己的 skill？看 [`CONTRIBUTING.md`](CONTRIBUTING.md)。
**最缺的貢獻是實測回填**（把某條路線從 E6 升到 E1），不是新增更多 E6。

---

## 誠實標記（我們自己的缺口）

| ID | 缺口 |
|---|---|
| MH-G1 | L1 的影片下載依賴執行環境，部分平台需登入或不在網路白名單內 |
| MH-G2 | 雙模型互審目前是建議不是強制，validator 未檢核 |
| **MH-G3** | **尚無實測回填機制——E6 升 E1 沒有流程入口** |
| MH-G4 | 來源授權邊界未由法務定調，目前採最保守做法 |

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
