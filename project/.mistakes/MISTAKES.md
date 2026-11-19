# CIS342 專案錯誤紀錄

> 本檔僅記錄 `cis342/project`（車牌辨識 LPR group project）發生的錯誤。
> 對應的全局紀錄：`C:/Users/honok/.copilot/mistake-log/MISTAKES.md`

---

## 📝 錯誤記錄

### 錯誤：改寫 markdown cell 時用固定索引，把內容寫進 code cell 並覆蓋掉另一個 cell

- **時間**：2026-02-XX（CIS342 LPR notebook 建置期間）
- **來源專檔**：cis342/project（CIS342 車牌辨識 LPR group project）
- **分類**：`假設錯誤` / `工具誤用` / `邏輯缺陷`
- **任務描述**：修改 `notebooks/lpr_dev.ipynb` 的 markdown cell（例如把 AI 使用聲明改成組員姓名劃分、把分工上移）
- **錯誤描述**：
  - 我用 `C = nb["cells"]` 拿到原始索引後，直接以 `setmd(C[13], ...)` 之類的固定索引寫入
  - 但前一步已經做過 cell 重排／插入，`C` 的索引與「畫面上看到的第 N 個 cell」已經不一致
  - 結果：(a) markdown 內容被寫進 `cell_type == "code"` 的 cell；(b) insert 造成索引位移，後續寫入把 `[EV-01]` 的 code cell 整個蓋掉
- **根本原因**：把「陣列索引」當成「穩定識別碼」在用，而 notebook 的 cell 順序正是我這幾輪在改的東西。沒有每次重新載入檔案、沒有用內容比對定位。
- **修正方式**：
  - 改為每次從檔案重新 `json.load`，並用**內容比對**定位 cell：
    ```python
    idx = next(i for i,c in enumerate(nb["cells"])
               if "".join(c["source"]).startswith("## AI 使用聲明（Ho Nok Hei）"))
    ```
  - 寫入前 assert `c["cell_type"] == "ma"`（markdown）
  - 修改後用 `nbformat.validate()` + 檢查 `cell id` 是否全唯一 + 印出所有 cell 標題清單核對
- **預防措施**：
  1. **Notebook 一律用「內容」定位 cell，不用索引**；索引只在同一次、同一個 list 物件內、且沒有 insert/delete 時才可用
  2. 寫入 markdown 前 assert 該 cell 的 `cell_type`
  3. 每次寫回後印出「索引 → cell_type → 首行標題」全表，人工核對數量與順序
  4. 結構性操作（重排、插入、刪除）與內容修改**分開兩次執行**
- **經驗教訓**：在會被自己重排的容器裡，索引是會過期的假設；能當識別碼的只有內容。

### 錯誤：重寫 markdown cell 後，舊版 cell 沒刪除，造成同一節出現兩份

- **時間**：2026-02-XX（CIS342 LPR notebook，AI 使用聲明改寫）
- **來源專檔**：cis342/project
- **分類**：`邏輯缺陷` / `過度簡化`
- **任務描述**：把「AI 使用聲明（Ho Nok Hei）」由 6 列改寫、並把「Li Chi Shing」改為空白模板
- **錯誤描述**：
  - 我先用「複製 → 修改 → 附加」的方式產生新版 AI 聲明 cell，但沒有刪掉舊的兩份
  - `nbconvert --execute` 成功、`nbformat.validate()` 也通過（格式沒問題），但 cell 數從 45 變成 47
  - 直到印出各 cell 首行標題才發現 `## AI 使用聲明（Ho Nok Hei）` 與 `## AI 使用聲明（Li Chi Shing）` 各出現兩次
- **根本原因**：把「驗證通過」等同於「內容正確」。validate 只檢查 nbformat schema，完全不檢查語意重複。我沒有在寫回後做「標題唯一性」檢查。
- **修正方式**：
  - 寫一段去重邏輯：以 markdown 的第一個 `## ` 標題為 key，重複者只保留第一次出現的
  - 修正後 cell 數回到 45，並重新 `nbconvert --execute` 確認 0 error cell
- **預防措施**：
  1. 修改既有節點應為 **in-place 覆寫 source**，不要「新增一份新的」再刪舊的
  2. 每次寫回後執行**標題重複檢查**：
     ```python
     heads = [next((l for l in "".join(c["source"]).splitlines() if l.startswith("## ")), None) for c in nb["cells"]]
     assert len(heads) == len(set(h for h in heads if h))
     ```
  3. 同時檢查 cell 總數是否符合預期（增删前後都要有預期值）
- **經驗教訓**：schema 驗證通過 ≠ 文件正確；結構性修改後必須驗「語意不變量」（數量、唯一性、順序），不能只驗格式。
