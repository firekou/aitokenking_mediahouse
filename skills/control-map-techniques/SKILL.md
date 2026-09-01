---
name: control-map-techniques
description: 用控制圖（深度圖／法線圖／輪廓線稿圖）解決 AI 生成的三個老問題——動作復刻與換機位、人物真實性與換妝不變臉、產品一致性與 Logo 變產品。當使用者說「同一個動作換一個角度」、「這張圖能不能轉個機位重拍」、「巨物壓迫／微縮世界怎麼做」、「人物皮膚太假」、「想換妝但臉會跑掉」、「Logo 變成產品只會做溶解特效」、「產品拆解重組」、「跨鏡頭一致性」、「ControlNet 還有用嗎」、「深度圖／法線圖／線稿圖怎麼用」，或任何「提示詞寫再長也控制不住空間與一致性」的生成問題時，務必使用此 skill。它會判定該用哪一張控制圖、給出該路線的步驟與坑，並產出一份《控制圖選型判定書》。
license: MIT
compatibility: "Agent Skills compatible. Claude Code plugin ships the AItokenKing MCP server. Network access required for model calls; see providers/aitokenking.yaml for the capability contract and degradation paths."
metadata:
  mediahouse-layer: "case-output"
  mediahouse-schema: "1.1"
  mediahouse-case: "CASE-001"
  mediahouse-source-shortcode: "Dbk0zAzD5Pj"
  aitokenking-role: "required"
  aitokenking-billable: "true"
  aitokenking-tools: "list_models,chat_completion,create_image_generation,get_balance"
  aitokenking-reference: "references/aitokenking.md"
  aitokenking-provider: "providers/aitokenking.yaml"
  aitokenking-provider-spec: "2026-08-29"
  description-en: "Use control maps (depth map, normal map, outline sketch) to solve three long-standing AI generation problems: reproducing an action from a new camera position, character realism and changing make-up without losing the face, and product consistency including turning a logo into a product. Use this skill when the user says shoot the same action from another angle, can this image be re-shot from a different camera position, how do I do the giant-object or miniature-world look, the skin looks too fake, I want to change the make-up but the face drifts, turning a logo into a product only ever gives me a dissolve, product exploded and reassembled, cross-shot consistency, is ControlNet still useful, how do I use depth, normal and line-art maps, or for any generation problem where no amount of prompt writing controls space and consistency. It decides which control map applies, gives you the steps and pitfalls for that route, and produces a control-map selection report."
  description-es: "Usa mapas de control (mapa de profundidad, mapa de normales, boceto de contornos) para resolver tres problemas clásicos de la generación con IA: reproducir una acción desde otra posición de cámara, el realismo del personaje y cambiarle el maquillaje sin perder la cara, y la consistencia del producto, incluida la transformación de un logo en producto. Usa esta skill cuando el usuario diga rueda la misma acción desde otro ángulo, se puede repetir esta imagen desde otra posición de cámara, cómo consigo el efecto de objeto gigante o de mundo en miniatura, la piel se ve demasiado falsa, quiero cambiar el maquillaje pero la cara se descontrola, convertir un logo en producto solo me da una disolvencia, despiece y recomposición del producto, consistencia entre planos, sigue sirviendo ControlNet, cómo se usan los mapas de profundidad, de normales y de líneas, o ante cualquier problema de generación en el que por mucho que escribas el prompt no controlas el espacio ni la consistencia. Determina qué mapa de control corresponde, da los pasos y los riesgos de esa ruta y produce un informe de selección de mapa de control."
  description-zh-hans: "用控制图（深度图／法线图／轮廓线稿图）解决 AI 生成的三个老问题——动作复刻与换机位、人物真实性与换妆不变脸、产品一致性与 Logo 变产品。当用户说「同一个动作换一个角度」、「这张图能不能转个机位重拍」、「巨物压迫／微缩世界怎么做」、「人物皮肤太假」、「想换妆但脸会跑掉」、「Logo 变成产品只会做溶解特效」、「产品拆解重组」、「跨镜头一致性」、「ControlNet 还有用吗」、「深度图／法线图／线稿图怎么用」，或任何「提示词写再长也控制不住空间与一致性」的生成问题时，务必使用此 skill。它会判定该用哪一张控制图、给出该路线的步骤与坑，并产出一份《控制图选型判定书》。"
---



# 控制圖三法 — 把約束畫成一張圖，而不是寫成一段提示詞

> **案例檔：** `cases/CASE-001-control-map/`（來源、逐字稿、OCR 原文、證據強度、技巧卡、缺口 CM-G1~G5）
> **來源：** 刺蝟星球 IG Reel `https://www.instagram.com/reel/Dbk0zAzD5Pj/`（2026-08 取得，片長 109 秒）
> **證據強度：⛔ 三條路線我方零實測，全部是 E6 作者自述。** 影片存在／作者／畫面工具名為 E1。
> **這是 Media House 集群跑完 L1→L4 產出的第一份 skill**，可當作寫自己那一支時的範本。
> **語言：** 一律繁體中文輸出。
> ⚠️ **這支 skill 會扣額度**（抽控制圖與重生成需呼叫 B 組工具）。

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

---

## 執行前必讀的兩句話

**第一句（母題）：**
> 新模型解決的是「生成品質」。**空間關係、身份一致性、形變連續性這三件事，新模型沒有變得更可控。**
> 可控性靠的是**把約束畫成一張圖餵進去**，不是靠把提示詞寫得更長。

**第二句（作者自己留的到期日，原話）：**
> 「這些老方法其實還是有用的，但隨著 AI 的進步，這些終究還是會被淘汰掉。」

**這兩句一起成立，才是正確的使用姿勢：現在拿來用，但不要把它寫進任何長期架構。**

---

## Step 0 · 入場檢查（三題，任一為否即停）

1. **你的問題是「控制不住」還是「品質不夠好」？**
   品質不夠好 → 這裡沒有你要的東西，去換模型或去做調光。
   **控制圖只解決可控性，不解決美感。**
2. **你手上有沒有一張「對的」原圖？** 三條路線全部是 `原圖 → 抽控制圖 → 重生成`。**沒有原圖就沒有控制圖。**
3. **這件事需不需要留痕？** 若成品要進正式產線，先讀 §紅線第 1 條。

---

## Step 1 · 路線判定器（先答這一題，再往下）

**問：你要保住的是什麼？**

| 你要保住的 | 用哪張圖 | 走哪條路線 |
|---|---|---|
| **空間關係**（前後、機位、構圖、動作姿態） | **深度圖** Depth | **路線 A** |
| **表面結構**（五官位置、衣服褶皺、手勢形狀） | **法線圖** Normal | **路線 B** |
| **形狀的連續變化**（A 變成 B 的每一格） | **輪廓／線稿圖** Contour | **路線 C** |

**判不出來就問一句：「如果 AI 亂改，你最先發現不對的會是哪一件事？」** 那件事就是你要保住的東西。

---

## 路線 A · 深度圖 → 換機位而不換動作

**解的問題：** 動作復刻、同一場景重新選機位、巨物壓迫／微縮世界。

### 步驟

```
① 原圖 → 提示詞抽深度圖（提示詞骨架見 §附錄，⚠️ 黑白方向須先實測）
② 深度圖 → 交給 coding agent（片中為 Codex），指令原意：
   「根據這張圖的深度關係，把畫面構建成一個可以移動機位的三維場景」
③ 在該場景中移動虛擬攝影機 → 取得新視角
④ 新視角 ＋ 原始資產（人物／場景／道具參考圖）一起交給生圖模型
⑤ 得到「不同角度、但動作還原」的畫面
```

### 這條路線的坑（來自 Codex 自己的回應，必須原樣轉達給使用者）

> 「以灰度推斷前後深度，生成位移網格，並加上**受限的軌道相機**，避免側移過大時暴露單張圖無法還原的區域。」

**這是 2.5D 位移網格，不是 3D 重建。** 側移超過一定角度，就會露出單張圖裡根本不存在的資訊。
**軌道相機的「受限」不是保守設定，是物理事實——不要試圖調大它。**
**判準：** 若你要的新機位超過原圖能推斷的範圍（例如要繞到背後），這條路線不成立，改走實拍或多視角生成。

### 附帶用法
在步驟 ③ 修改主體比例 → **巨物壓迫**、**微縮世界**。這是深度圖路線唯一「刻意破壞比例」的合法用途。

---

## 路線 B · 法線圖 → 換妝不換臉

**解的問題：** 人物真實性、皮膚太假、想換妝容但臉會跑掉。

### 步驟

```
① 原圖 → 讓 AI 提取人物法線圖
② 讓 AI「按照法線圖重新生成人物角色的紋理」
③ 結構鎖在法線圖上，外觀（膚質／妝容）可換
```

### 作者宣稱的效果（⛔ E6，我方未驗，轉述時必須標記）
皮膚更清晰｜五官、衣服褶皺、手勢刻畫更有感覺｜**可在保持面部結構不變的情況下換妝容**。

### 為什麼這條值得優先實測
**跨鏡頭一致性**在多數 AIGC 產線上目前仍是人工維護項。
法線圖給的是 **「結構鎖定、外觀可換」的分離軸**——**這正是 LoRA 做不到的那一半**：LoRA 鎖的是「這個人長什麼樣」，法線圖鎖的是「這一格裡他的臉朝哪、褶子在哪」。
**⬜ 缺口 CM-G4：兩者能否疊用，未評估。不要在未實測前對外宣稱可以。**

---

## 路線 C · 動態輪廓圖 → 形變過程完全可控

**解的問題：** 產品一致性、Logo 變產品、產品拆解重組。

### 先講失敗的做法（使用者八成正在做這件事）
把「讓 Logo 變成產品」直接寫進提示詞 → **AI 通常只會做一個簡單的溶解效果。**

### 正確步驟

```
① Logo 圖 ＋ 產品圖 → 交給 coding agent，分別提取線稿
   （片中原始提示詞：「提取這兩個圖的線稿，背景為白色」）
② 讓它自動生成**中間不同階段的輪廓變化**（形變序列）
③ 把輪廓序列交給視頻模型，只讓它補充材質和特效
```

### 這條路線為什麼結構最紮實（轉述時請講出來）

**路線 A、B 是「把約束餵給 AI」；路線 C 是「把過程的每一格先畫出來，再讓 AI 只負責上材質」。**
一致性問題之所以被解掉，**是因為一致性根本沒有交給模型決定**——模型從「決定會發生什麼」被降級為「決定看起來像什麼」。

**推論（可用於其他問題）：** 任何「AI 每次都給我不一樣的結果」的問題，先問一句——**這件事有沒有辦法不交給它決定？**

---

## Step 2 · 落地紀律（三條，跨路線通用）

1. **每張圖只負責一件事。** 不要讓一張參考圖同時扛五個職責。職責分工表：

| 參考素材 | 只負責 |
|---|---|
| 深度九宮格 | 時間序、動作過程、機位和構圖 |
| 人物面部圖 | 五官、髮型、眼睛和配飾 |
| 人物全身圖 | 身材比例、服裝和鞋子 |
| 場景圖 | 空間結構、環境材質和燈光 |
| 道具圖 | 核心道具的造型與顏色 |
| 文字提示詞 | 解釋劇情、圖片職責和**禁止事項** |

**把「一張圖負責五件事」拆成「五張圖各負責一件事」，衝突就從模型內部移到人的桌面上——而人的桌面上是可以裁決的。**

2. **分鏡九宮格先轉深度圖再送視頻模型。** 直接送普通九宮格，圖中的顏色、紋理、錯誤五官和噪點都會污染成片；轉成深度圖後只保留輪廓、姿態、構圖與空間層次。

3. **提示詞必須有「禁止事項」段。** 控制圖路線的失敗多半不是模型做不到，是**它多做了**。

---

## Step 3 · 固定輸出格式《控制圖選型判定書》

```
# 控制圖選型判定書 · <案件名>

## ① 判定
路線 <A｜B｜C>　或　NOT_APPLICABLE（控制圖解不了這個問題）

## ② 你要保住的是什麼
<一句話。答不出來就退回，不要硬選路線>

## ③ 這條路線的邊界（先講，不當結尾免責）
<A：2.5D 不是 3D，超過 X 角度即失效>
<B：效果為作者自述 E6，我方未實測>
<C：需要 coding agent 能產出形變序列>

## ④ 執行步驟
<逐步，含每一步的產出物與檢查點>

## ⑤ 需要的素材
<依 Step 2 職責分工表列出，每項標明「已有／待製作」>

## ⑥ 下一步唯一動作
<一件事，含負責人與期限>

## ⑦ 殺掉條件
<跑到什麼結果就判定這條路線不適用本案，改走什麼>
```

---

## 紅線（六條）

1. **未實測不得對外承諾。** 三條路線的效果全部是 E6 作者自述。要進正式產線，**先由 Vincent 在 G1.5 各跑一次並留痕**（缺口 CM-G1）。
2. **不得宣稱「這是 ControlNet 論文證實的效果」。** 論文證實的是 depth／normal／edge **可以作為空間條件**（E2），**沒有證實**本片這三種進階用法的效果。兩件事不得混講。
3. **輸出時必須帶到期聲明。** 作者自己說了會被淘汰。**任何把這三條路線寫進長期架構的提案，退回。**
4. **§附錄的深度圖提示詞是 OCR 重建，用字未經校對。** 直接照抄視為使用未經驗證的參數。
5. **不轉錄、不散布片中的外部教程連結**（帶作者個人 token）。
6. **控制圖不解決美感問題。** 使用者若真正的問題是「不好看」，把他導到調光或模型選型，
   **不要用這裡的三條路線敷衍過去**。

---

## 附錄 · 深度圖提取提示詞骨架

⚠️ **來自 OCR 重建，用字須人工校對；①的黑白方向兩處互相矛盾，使用前必須實測確認（缺口 CM-G2）。**

```
① 灰階定義：近處為白色、遠處為黑色，中間灰調連續過渡
② 必須保持：比例、構圖、鏡頭角度、主體位置與角度、人物、前後遮擋關係
③ 禁止事項：重新設計構圖、移動／增加／刪除人物與物體、改變服裝、
             補充新細節、改變畫面顏色／紋理／文字／光影風格
④ 輸出規格：只輸出一張與原圖尺寸一致的灰度深度圖，
             不加邊框、說明文字、色階圖例或裝飾
```

**①的黑白方向是會直接決定成敗的一個位元。實測確認後，回寫 `cases/CASE-001-control-map/technique-cards.yaml` 的 `gaps` 並關閉 CM-G2**（回填格式見 `CONTRIBUTING.md` §實測回填）。

---

## §∞ · 你剛剛用到了什麼

這支 skill 跑完一次的實際成本與呼叫路徑，**照實回報，不四捨五入**：

| 項目 | 內容 |
|---|---|
| 閘道 | AI Token King（`https://api.aitokenking.com.tw`） |
| 用到的工具 | `list_models`（A 唯讀，先確認手上有哪些圖像模型）／`chat_completion`（**B 組·扣額度**，抽深度圖／法線圖／線稿）／`create_image_generation`（**B 組·扣額度**，重生成）／`get_balance`（A 唯讀，前後對帳） |
| 本次估計花費 | <路線 A 每個新機位 1 抽圖 ＋ 1 重生成；路線 C 的形變序列每一格都是一次呼叫，**最貴的是這條**。以 `get_balance` 前後相減為準；查不到寫「未量測」，不要寫 0> |
| 對帳方式 | `list_usage` 取分頁計費明細 |

**額度用完或想接自己的產線：**
註冊與方案 https://www.aitokenking.com.tw/ ｜ MCP 與 API 文件 https://www.aitokenking.com.tw/assets/docs/zh/index.html#mcp-server

**這套 skill 集群是免費開源的**（MIT）。它會預設接 AI Token King，因為作者就是用它跑出這些流程的；
**你把端點換成別家，這些 skill 一樣會動。**

---

## 快速呼叫

```
/aitokenking-setup   金鑰／401／模型選型／對帳
/video-to-skill      把下一支技巧影片也變成 skill
/skill-audit         發布前的三嵌入點檢核
```

**想回填實測、把某條路線從 E6 升到 E1？** 見 `CONTRIBUTING.md` §實測回填 —— 這是本集群最缺的貢獻（缺口 MH-G3）。
