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

---


### 錯誤：先開 'w' 再讀同一個檔案，導致檔案被清空

- **時間**：2026-11-20 11:49
- **來源專檔**：cis342/project（CIS342 車牌辨識 LPR group project）
- **分類**：`邏輯缺陷` / `路徑錯誤` / `工具誤用`
- **任務描述**：在 `notebooks/AI_EDIT_LOG.md` 回填 commit hash（把 `PLACEHOLDER` 換成實際 hash）
- **錯誤描述**：
  - 寫成單行：
    ```python
    io.open(p,"w",encoding="utf-8").write(io.open(p,encoding="utf-8").read().replace("PLACEHOLDER","65b4913"))
    ```
  - Python 求值順序：先建立 `open(p,"w")` 物件（**此刻檔案已被 truncate 成 0 bytes**），才去執行 `open(p).read()`
  - 結果讀到空字串，寫回空字串 → **整個 68 行的紀錄檔被清空**
  - 而 commit 仍成功（`1 file changed, 68 deletions(-)`），若沒看 stat 就會直接進歷史
- **根本原因**：在同一個運算式裡同時做「寫入開檔」與「讀取同檔」。`'w'` 模式開檔即截斷，這是 Python 的基本行為，我卻用單行鏈式寫法把它藏起來了。
- **修正方式**：
  - 先 `git checkout 65b4913 -- project/notebooks/AI_EDIT_LOG.md` 還原
  - 改成分離步驟：
    ```python
    text = io.open(p, encoding="utf-8").read()   # 先完整讀
    text = text.replace(...)                      # 在記憶體中處理
    io.open(p, "w", encoding="utf-8").write(text) # 最後才寫
    ```
  - 並在寫入前後印出字元數（`before: 2316 -> after: 2312`）作為斷言依據
- **預防措施**：
  1. **讀檔與寫檔永遠分成兩個語句**，絕不在同一個運算式裡同時出現
  2. 要保證安全就用 `io.open(p, "r+")` 或先寫暫存檔再 `os.replace()`
  3. **每次 commit 後檢查 `git show --stat`**：若出現「只有刪除、沒有新增」且數量很大，就是內容被清空的徵兆
  4. 對「只做字串替換」的操作，可以加 assert 確認替換前後的長度差異合理
- **經驗教訓**：`open(p, 'w')` 是**破壞性操作**，它與讀取同一個檔案不能放在同一個運算式裡 —— Python 的求值順序會讓你先清空檔案，再讀到空白。


### 錯誤：commit 後未檢查 stat，讓「清空檔案」的變更進入歷史

- **時間**：2026-11-20 11:49
- **來源專檔**：cis342/project
- **分類**：`過度簡化` / `工具誤用`
- **任務描述**：將 commit hash 回填至 `AI_EDIT_LOG.md` 並 commit
- **錯誤描述**：
  - commit 輸出 `1 file changed, 68 deletions(-)`，**只有刪除沒有新增**
  - 我當下仍回報「backfilled」並繼續下一步，直到下一輪才因為好奇而發現
- **根本原因**：把 `git commit` 的成功訊息（有 commit hash）等同於「變更內容正確」。實際上 git 只負責記錄，不負責判斷內容合不合理。
- **修正方式**：從 `65b4913` 還原檔案，重新以「先讀後寫」方式回填，並再次驗證行數（68 行）
- **預防措施**：
  1. **看到 `N deletions(-)` 而 `insertions(+)` 為 0 或明顯偏少時，必須先 `git show --stat` / `git show HEAD -- <file>` 檢查**
  2. 對「只改一兩個字」的操作，預期 diff 應該是小幅增減；若顯示大量刪除就是異常
  3. 重要檔案在同一次操作前後都應記錄行數或大小
- **經驗教訓**：git 的成功只代表「已記錄」，不代表「記錄了正確的東西」；`--stat` 是免費的防呆檢查，不該跳過。
