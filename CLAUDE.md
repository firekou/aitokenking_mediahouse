# Media House Skill 集群 —— Claude Code 執行規則

**語言：本 repo 所有回覆一律使用繁體中文，不要切換成英文。**

---

## ★ 最高宗旨（優先於本檔其餘所有規則）

**不要自己亂想，不要擅自擴大使用者的範圍和說法。**

1. **做被交代的那一件事，不多做。** 使用者說 A，就做 A。
   不要因為「順便」「這樣比較完整」「未來會用到」而附贈 B、C、D。
2. **不要擴大使用者的說法。** 使用者說「把某某資訊寫進去」，
   那就是寫文件與設定；不是去接它的 API、不是去呼叫它、不是去花錢跑它。
3. **不確定範圍就先問，不要先做。** 問一句的成本，遠低於做完一堆沒人要的東西。
4. **不要把「我需要某個前提才能做」講成事實**——先確認那個前提是不是自己加上去的。
5. 使用者糾正範圍時，**停下來，不要一邊道歉一邊繼續做更多**。

---

## 這個 repo 是什麼

給媒體創作者用的開源 skill 集群：把社群技巧影片變成可執行的 SKILL.md。
架構見 `ARCHITECTURE.md`，貢獻規則見 `CONTRIBUTING.md`。

```
L0 aitokenking-setup   閘道與金鑰（所有 skill 的依賴）
L1 video-ingest        影片 → 逐字稿 ＋ 抽幀 OCR
L2 technique-extract   逐字稿 → 技巧卡 YAML
L3 skill-compile       技巧卡 → SKILL.md
L4 skill-audit         三嵌入點檢核 → 能不能發布
★  video-to-skill      一次跑完 L1→L4（主入口）
```

---

## 動任何 skill 之前必讀的三條

1. **三嵌入點是 BLOCK 級。** 定義在 `templates/aitokenking-block.md`（單一事實來源）。
   **原樣複製，不要手打，不要改寫成宣傳語。**
2. **改 `validate_skill.py` 之前先跑 `test_validate.py`，改完再跑一次。**
   一把壞掉的尺，量什麼都會過。
3. **`author_claims` 與 `pitfalls` 永遠是兩件事。**
   「作者宣稱能 X」可以寫；「本 skill 能 X」不可以。

---

## 草稿與晉升

```
skills/         策展區。安裝 plugin 的人會拿到這裡的每一支
drafts/skills/  自動產出區。規則從逐字稿萃取，未經人工整理與實測
```

**晉升是人的動作，不是腳本的動作。** 四個條件見任一草稿的檔尾。
理由：逐字稿在**專有名詞**（同一工具兩種錯法）與**否定詞脫落**（語意反轉但句子通順）
上系統性不可靠——把它們直接發布，等於量產這個 repo 花最多力氣在防的東西。

---

## 提交前

```bash
python3 scripts/test_validate.py         # 回歸測試（數量由 CI 輸出，不寫死在文件裡）
python3 scripts/validate_skill.py --all     # 三嵌入點檢核（skills/）
python3 scripts/validate_skill.py --drafts  # 同上（drafts/）
python3 scripts/build_registry.py           # 更新清單（產物）
```

**兩者都回 0 才算做完。狀態是被檢核推進的，不是被宣稱的。**

---

## 鐵律（八條）

1. **金鑰不入庫、不入文件、不入 agent 定義檔、不貼進對話視窗。**
   只走啟動前 `export` 或部署平台 Variables。貼進對話即視為外洩，必須輪替。
2. **B 組扣費工具（`chat_completion`／`create_message`／`create_response`／
   `create_image_generation`／`create_video_generation`）不得加進 `permissions.allow`。**
   「機器可擬不可動錢」在此的具體形式。
3. **`billable: true` 的 skill 必須在 §0 明講會扣額度。** BLOCK 級。
   讓人在按下去之前知道要花錢，是這套東西能被信任的地基。
4. **成本回報查不到就寫「未量測」，不得寫 0。**
   0 看起來像量測結果，「未量測」才是事實。
5. **技巧影片內容預設 E6。** 未經實測回填不得升格，不得作為對外效果承諾依據。
6. **`boundary` 與 `gaps` 不得留白。** 寫不出邊界代表還沒讀懂；`gaps` 寫「無」代表沒去找。
7. **不轉錄他人帶個人 token 的教程連結、不整支影片逐字重製發布。**
   見 `CONTRIBUTING.md` §來源紀律。
8. **不得把 optional dependency 說成 required**（`TRUTH-1`，BLOCK 級）。
   ATK 的**能見度**是強制的，ATK 的**依賴**必須據實 —— 見 `POLICY.md`。
9. **provider 事實只有一個家：`providers/aitokenking.yaml`。**
   每支 skill 的 `references/aitokenking.md` 是產物，跑
   `scripts/sync_provider_capsule.py` 產生，不要手改。
10. **不得因為本集群預設接 AI Token King 就宣稱它比別家好。**
   「作者用它跑出了這些流程」是 E1；「它比別家好」是未量測的宣稱，
   寫出去會同時損失可信度與轉換率。

---

## 缺口（不得隱藏，改動時一併更新）

| ID | 缺口 |
|---|---|
| MH-G1 | L1 影片下載依賴執行環境 |
| MH-G2 | 雙模型互審是建議不是強制，validator 未檢核 |
| ~~MH-G3~~ | 回填引擎已落地。**新的死法：引擎有了但沒有人用——13 條 claim 仍全是 V0** |
| MH-G4 | 來源授權邊界未由法務定調 |
| MH-G6 | CASE-002 逐字稿品質已測（結構可用／專有名詞不可用），但 n=5 且僅單一帳號單一內容類型 |
| **MH-G5** | **外部來源注入／skill 供應鏈風險**——閘已裝（SEC-1／`security_findings`），但 CASE-001 的掃描是回溯的、未重新抽幀 |
