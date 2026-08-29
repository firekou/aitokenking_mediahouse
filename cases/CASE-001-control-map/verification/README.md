# CASE-001 · 實測回填

**目前這個資料夾是空的，而空不等於「都沒問題」——是「一條都沒測過」。**

CASE-001 有 **13 條 claim**，其中 6 條 provenance 是 E1（我方確實觀察到），
但 **verification 全部是 V0**（效果一次都沒重現過）。
**這兩件事同時成立，而且都是真的。**

## 怎麼回填

1. 複製 [`templates/verification.example.yaml`](../../../templates/verification.example.yaml)
2. 改名為 `verification-<你的代號>-<YYYY-MM-DD>.yaml`
3. 挑一條 claim 驗（清單見 [`../evidence-ledger.yaml`](../evidence-ledger.yaml)）
4. 開 PR

## 最有價值的兩條（挑一條就好）

| claim | 為什麼是它 |
|---|---|
| **CM-G2 深度圖黑白方向** | OCR 兩處互相矛盾。**這是一個位元，但它決定整條路線成不成立。** 跑一次就能關掉一個缺口 |
| **T01-C03 側移邊界** | 目前只有定性（「超過一定角度會露餡」），沒有定量。測出「超過幾度」就能把它推到 V4 |

## 三件會讓回填被退回的事

1. **只記成功的次數。** 失敗的那幾次比成功的更有價值——`runs` 要全記。
2. **沒有 `environment`。** 沒有環境就無法重現，無法重現的回報不是證據是感想。
3. **自己填 `review`。** 那是 reviewer 的欄位。**自己給自己升級，這條線就不存在了。**
