# CIS342 Course Project — 實作內容劃分表 (v0.2 / 2 人版)

> **組員數：2 人**。因此採「兩條垂直線（Vertical Slice）」分工：**A 線 = 定位線、B 線 = 辨識線**，
> 各自從頭到尾負責自己的階段，只透過 §1 契約接合。**不採按階段輪流**，因為 2 人輪流會造成每次都要重新理解對方進度、合併成本爆炸。
>
> **用途**：組內討論分工用。認領後在 §3 填名字。
> **專案**：Hong Kong License Plate Recognition (LPR)
> **交付**：Colab `ipynb` 原始碼 + PDF 報告 + 4 成功案例 + 2 失敗案例；**2026-12-18 12:00 前** Moodle
> **評分**：程式執行 40% / 報告 30% / 現場簡報 30%
> **不可省略的四階段**：Localization → Segmentation → Geometric Transformation → OCR

---

## 0. 共同前提（先講好，否則合併會爆炸）

1. **執行環境 = Google Colab + `.ipynb`**。每人本機各有一份自己的 notebook 開發，完成後**只把自己負責的 cell 貼到共用的 Colab notebook**。
2. 因為要複製貼上合併，**禁止寫 `import mymodule`、`from lpr import xxx`**。所有函式都必須直接寫在 notebook 的 cell 裡。
3. **Cell 標記規範**（貼上時必須保留，方便組長定位與衝突排查）：
   ```
   # ==== [LOC-01] Localization: candidate generation ====
   ```
4. **共用常數集中在 §0 設定 cell**（影像路徑、`PLATE_W/H`、門檻值、`TEST_IMG`）。**只有整合負責人（組長）可以改這個 cell。**
5. **每人貼上的 cell 下方必須附一個 `# --- self test ---` demo cell**，用固定的 `TEST_IMG` 就能跑。這樣別人不用等整合也能驗你的階段。
6. **介面契約一旦凍結，改動必須在群組公告**（見 §1）。
7. 每人**不要動別人的 cell**；需要別人的階段出錯，先在群組回報，不要自己改。

---

## 1. 資料契約（最優先凍結，第 1 天就要定案）

```python
# 影像一律 np.ndarray, BGR, uint8（統一用 cv2.imread）
# 車牌校正後統一尺寸（寫在 §0，實測後再調）

PLATE_W, PLATE_H = 480, 140

Candidate = {
    "quad":  np.float32 (4, 2),      # 四點，順時針，由左上開始
    "bbox":  (x, y, w, h),           # 外接框
    "score": float,                  # 越大越可能是車牌
    "source": str                    # 哪個策略找到的（利於 ablation 與報告）
}
```

| 階段 | 函式簽名 | 輸入 | 輸出 |
|---|---|---|---|
| 前處理 | `preprocess(img)` | 原圖 BGR | BGR（尺寸不變） |
| **定位** | `localize(img)` | 前處理後影像 | `List[Candidate]`，score 由高到低 |
| **擷取** | `segment(img, quad)` | 原始影像 + 四點 | `(plate_bgr, mask_uint8)` |
| **幾何校正** | `rectify(plate_bgr, mask)` | 車牌區 | `(upright_bgr, upright_mask)`，尺寸固定 |
| **字元辨識** | `recognize(upright_bgr, upright_mask)` | 校正後車牌 | `{"text": str, "conf": float, "char_boxes": list}` |
| 後處理 | `postprocess(text)` | 字串 | `(fixed_text, is_valid_plate)` |

> 這張表就是「合併介面」。只要大家都遵守，四個人的程式碼貼在一起就能跑。

### `labels.csv` 欄位（已凍結）

| 欄位 | 型別 | 說明 |
|---|---|---|
| `file` | str | 影像檔名（不含路徑） |
| `plate_idx` | str | 同圖第幾個車牌；單車牌固定 `0`（多車牌擴充預留） |
| `split` | str | `main`（主要測試集）或 `external`（外部測試集，不參與調參） |
| `text` | str | 正確車牌字串，全大寫、不含空白 |
| `front_rear` | str | `front`（白底）或 `rear`（黃底） |
| `difficulty` | str | `normal` / `hard` / `unreadable` / `not_plate`（語意見 §7） |
| `note` | str | 備註；`[D1-02]` 匯入時會寫入 `bbox=x,y,w,h;n_obj=n` |

**單一車牌原則**：本版 `run_pipeline()` 每次只輸出一個字串。同圖多車牌只標註面積最大者，其餘視為背景。

---

## 2. 模組劃分表（認領用）

### A. 基礎與資料（建議：組長 / 1 人）

| 編號 | Notebook 段落 | 具體要做什麼 | 難度 | 依賴 | 交付物 |
|---|---|---|---|---|---|
| **S0** | §0 Setup | Colab 環境、`cv2/numpy/matplotlib` 確認、共用常數、`PLATE_W/H`、debug 存圖函式 `save_stage(case_name, stage, img)` | ★☆☆ | — | 可執行的 setup cell |
| **D1** | §1 Dataset | 取得 100 張港車牌影像作 `main` 集（評分主力）、10–15 張作 `external` 集（未參與調參，證明非過擬合）；建 `labels.csv`（`file, plate_idx, split, text, front_rear, difficulty, note`） | ★★☆ | — | 影像集 + `labels.csv` |
| **EV** | §1 Eval | 評估框架：`evaluate(localize_fn, segment_fn, rectify_fn, recognize_fn)` 輸出每階段成功率、字元準確率 (CER)、整體 plate accuracy、每張圖耗時 | ★★☆ | S0, D1, 各模組介面 | `evaluation.csv` + 一張 summary 表 |

### B. 前處理 + 車牌定位（**A 線核心，全案最難**）

| 編號 | Notebook 段落 | 具體要做什麼 | 難度 | 依賴 | 交付物 |
|---|---|---|---|---|---|
| **PRE-01** | §2 Preprocess | 尺度正規化、去噪、光照補償（CLAHE / Retinex / 灰世界）、銳化；輸出仍為原尺寸 BGR | ★★☆ | S0 | `preprocess()` + 前後對照圖 |
| **LOC-01** | §3 Localization | **候選產生**：白/黃車牌色彩模型（HSV / Lab / 自訂 ratio）、轉灰階、形態學閉運算、`findContours` 取四邊形候選 | ★★★ | S0, PRE-01 | `localize_candidates()` |
| **LOC-02** | §3 Localization | **候選篩選與評分**：長寬比（港牌約寬扁）、面積、矩形度、內部邊緣密度（Sobel/Canny）、黑字對比度 → 綜合 score，取 top-k | ★★★ | LOC-01 | `score_candidates()`，輸出契約格式 |
| **LOC-03**(加分) | §3 Localization | 進階：滑動視窗 + HOG/SVM、或 YOLO/OpenCV DNN 當 fallback 保底 | ★★★ | LOC-02, EV | 可切換的 detector |

### C. 擷取 + 幾何校正

| 編號 | Notebook 段落 | 具體要做什麼 | 難度 | 依賴 | 交付物 |
|---|---|---|---|---|---|
| **SEG-01** | §4 Segmentation | 以 quad 為基礎裁切 → 精修邊界（Hough 找車牌上下框線、或對 quad 做 refine）→ 產生車牌 mask（白底/黃底 + 黑字分離） | ★★★ | LOC 契約, S0 | `segment()` |
| **GEO-01** | §5 Geometry | 四點排序（左上/右上/右下/左下）→ `cv2.getPerspectiveTransform` → warp 到 `PLATE_W × PLATE_H` → 旋轉/翻轉正規化 | ★★☆ | SEG-01 | `rectify()` |
| **GEO-02** | §5 Geometry | 邊界情況：極端傾斜、只有 3 點可用、warp 後仍歪 → 二次校正（`minAreaRect` 或 `deskew`） | ★★★ | GEO-01 | 修正前後對照 |

### D. 字元辨識 + 後處理

| 編號 | Notebook 段落 | 具體要做什麼 | 難度 | 依賴 | 交付物 |
|---|---|---|---|---|---|
| **OCR-01** | §6 OCR | 二值化（Otsu / adaptive / Sauvola）、極性判斷（確保黑字白底）、去除車牌邊框與螺絲孔 | ★★☆ | GEO-01 | 乾淨二值圖 + 可視化 |
| **OCR-02a** | §6 OCR | **自製路線（拿高分用）**：垂直投影切字 → 字元正規化 → 自建模板比對 或 自己訓練小 CNN | ★★★ | OCR-01 | 切字結果 + 辨識結果 |
| **OCR-02b** | §6 OCR | **現成路線（保底用）**：EasyOCR / PaddleOCR / Tesseract，限定 char whitelist（數字 + 省份字母）與單行模式 | ★☆☆ | OCR-01 | 可直接呼叫的 `recognize()` |
| **POST-01** | §7 Post | 車牌字串規則驗證與修正（常見混淆 O/0、I/1、S/5、B/8；長度與前綴檢查），輸出 `is_valid_plate` | ★★☆ | OCR-02 | `postprocess()` + 修正統計 |

> **OCR-02a / 02b 建議兩人分開做，最後比較**。報告的 "methodology + insight" 分數就靠這個對照。

### E. 整合、報告、簡報

| 編號 | 段落 | 具體要做什麼 | 難度 | 依賴 | 交付物 |
|---|---|---|---|---|---|
| **INT-01** | §5.5 整合（A 段） | `run_frontend()` / `export_dataset_frontend()`：定位→擷取→校正，把中間狀態寫成 `shared/stages/<stem>_0X_*.png`（只寫 `04_segment` / `05_rectify` / `05_rectify_mask`）。加失敗守門與 GT-bbox 示範模式 | ★★☆ | GEO-01 | `shared/stages/` 檔案 |
| **INT-02** | §8 整合（B 段） | `list_stage_stems()` / `load_stage()` / `run_backend()`：用 `glob` 讀 A 段檔案 → OCR → 後處理。另保留記憶體版 `run_pipeline()` 供 §9 評估 | ★★☆ | INT-01, OCR, POST | `run_backend()` + 批次表 |
| **DOC** | report/ | PDF 報告：方法論（每階段為何選此法 + 對照實驗）、結果表、失敗分析、參考文獻 | ★★☆ | EV, INT | PDF |
| **CASE** | report/ | 挑定 4 成功 + 2 挑戰/失敗案例，附每階段中間圖與失敗原因 | ★☆☆ | INT | 案例章節 |
| **PPT** | — | 現場簡報（Week 11 起）、demo 流程、分工說明 | ★★☆ | 全部 | 投影片 + demo script |

---

## 3. 分工方案（2 人版）

### 3.1 兩條垂直線

| | **A 線：定位線（Front-half）** | **B 線：辨識線（Back-half）** |
|---|---|---|
| **負責模組** | S0, D1, PRE-01, LOC-01, LOC-02, SEG-01, GEO-01 | EV, OCR-01, OCR-02a/02b, POST-01, INT, DOC, CASE, PPT |
| **產出 50% 的 pipeline** | 影像 → **校正好的車牌圖** | 校正車牌圖 → **字串** + 整合/評估/報告 |
| **技術難度** | ★★★（電腦視覺、幾何、調參） | ★★☆（OCR、工程整合、寫作量大） |
| **實際工作量** | 重演算法、較少寫作 | 較多寫作 + 整合，但算法難度低 |
| **卡關風險** | 高（定位失敗 → 全案失敗） | 低（可用現成 OCR 保底） |

> **平衡理由**：A 線演算法最難但產出少；B 線演算法簡單但要吃下評估、整合、報告、簡報全部文書。**兩邊總工時接近，且都不會閒置等對方。**

### 3.2 詳細認領表

| 認領人 | 主責模組 | 次要支援 |
|---|---|---|
| **A（定位）** | S0, D1, PRE-01, LOC-01, LOC-02, SEG-01, GEO-01 | 提供 B 線所有 debug 中間圖 |
| **B（辨識/整合）** | EV, OCR-01, OCR-02b, POST-01, INT, DOC, CASE, PPT | OCR-02a 自製切字（有餘力） |

### 3.3 強制協作點（不遵守就會爆炸）

| 時間 | 協作動作 | 為什麼 |
|---|---|---|
| **Day 1（今天）** | 兩人一起把 §1 契約讀完並簽名定案 | 契約改了整份重寫 |
| **W1 結束** | A 必須交出「能跑但粗糙的 `localize()`+`rectify()`」，即使準確率 <30% | B 沒有 input 就無法開發 OCR |
| **W1 結束** | B 必須交出 `run_pipeline()` 骨架 + 可執行的 `preprocess()` 佔位版 | A 需要 pipeline 才能驗證 |
| **W2 起** | A 交 `rectify()` 輸出圖存到共用 Google Drive 資料夾 `shared/rectified/` | B 用真實輸出開發 OCR，不用等 A 每次重跑 |
| **W2 起** | A 段（§5.5 `INT-01`）每次跑完把中間狀態留在 `shared/stages/`；B 段（§8 `INT-02`）用 `glob` 自己去掃 | **§8 整合已拆兩段**：B 不必等 A 的程式定案，只等檔案。缺檔即視為 A 段失敗 |
| **每週日 22:00** | 15 分鐘 sync：各自貼進共用 Colab、跑一次、記錄誰壞了 | 避免週末才發現衝突 |

> **關鍵做法**：A 用真實資料跑出 `shared/rectified/*.png`，B 直接讀這批圖開發 OCR。**這樣 B 完全不用等 A 完成定位就能開工。**

#### `shared/rectified/` 的格式契約

| 項目 | 值 |
|---|---|
| 檔名 | `<stem>.png`，另附 `<stem>_mask.png`（255 = 真實影像、0 = 補邊） |
| 尺寸 | 固定 `PLATE_W × PLATE_H` = **480 × 140** |
| 補邊 | 等比縮放後不足處補灰 `(32,32,32)`，**不拉伸、不變形** |

**現況（定位鏈未完成時的替代品）**：`[LOC-01]`→`[GEO-01]` 還是 stub，
所以由 `tools/export_rectified.py` 直接吃 `labels.csv` 的 GT bbox 裁切產生：

```bash
py tools/export_rectified.py --all        # 全部 99 張（跳過 unreadable）
py tools/export_rectified.py IMG_4540     # 指定檔名
py tools/export_rectified.py --list       # 先看清單
```

⚠️ 三條紅線：
1. 這批圖**不是 pipeline 產出**，報告不可這樣寫；`[GEO-01]` 完成後重跑覆蓋
2. §9 評估**一律走真 pipeline**，用 GT 裁切圖算準確率等於用答案做題
3. 沒有做透視校正 —— 資料集近半數 bbox 接近正方形（`AR` 中位數 1.52，車牌斜拍），
   所以較方的車牌左右會留白。`binarize()` 必須用 `_mask.png` 判斷有效區，
   不能假設整張 480×140 都是車牌

#### `shared/stages/` 的格式契約（§8 拆段後的 A→B 介面）

| 項目 | 值 |
|---|---|
| 檔名 | `<stem>_04_segment.png`、`<stem>_05_rectify.png`、`<stem>_05_rectify_mask.png` |
| `stem` | 原圖檔名去副檔名，例如 `train_IMG_1231_JPG.rf.4427…` |
| `05_rectify` | 固定 `PLATE_W × PLATE_H` = **480 × 140**，BGR（**不可轉灰階**，白/黃底極性要靠它） |
| `05_rectify_mask` | 單通道，255 = 真實影像、0 = 補邊 |
| 誰寫 | A 段 `[INT-01]` `export_dataset_frontend()` |
| 誰讀 | B 段 `[INT-02]` `list_stage_stems()` → `load_stage()` |

**B 段怎麼知道有哪些輸入**：`glob('*_05_rectify.png')`，**沒有額外的 manifest 檔**。
A 段定位失敗就不會產出該 stem 的檔案，因此「掃到什麼」就等於「A 段成功處理了哪些」，
清單與檔案天生一致，不會有兩份資料對不上的問題。

⚠️ 兩條紅線：
1. `shared/stages/` 只放 B 段真的需要的三個階段。`01_input`～`03_localize` 是定位除錯用的大圖
   （每張 2 MB），不要寫進去，否則 100 張就 200 MB
2. 示範模式（`use_gt_bbox=True`）的輸出**不可用於報告或 §9 準確率** —— 那是拿答案做題

---

### 3.4 兩人 Agent 對齊通道（Bridge）

除了固定 sync，日常方向對齊走一個極輕量的留言板，跑在 Radmin VPN 上：

| 項目 | 值 |
|---|---|
| 伺服器 | `nok` 那台（`http://26.123.142.162:8791`） |
| 工具 | `tools/bridge.py`（純標準庫單檔，不需 `pip install`） |
| 檢視 | 瀏覽器開 `http://26.123.142.162:8791/`（唯讀表格） |
| 說明 | `shared/bridge/README.md` |

```bash
py tools/bridge.py inbox --unread                      # 收未讀
py tools/bridge.py send --part "§6 OCR" --text "..."   # 寄訊息
py tools/bridge.py ack                                 # 標記已讀
```

**刻意設計成手動觸發**：不做背景輪詢、不做自動回覆，所以不會出現
兩個 Agent 互相回覆到無窮迴圈。防呆含 5 分鐘同內容去重、8000 字上限、
5000 則總量上限。

⚠️ Radmin VPN 會擋 ICMP，`ping` 不通是正常的；
要測連線請用 `Test-NetConnection -ComputerName 26.123.142.162 -Port 8791`。

---

## 4. 里程碑（2 人版，倒推自 12/18 截止）

| 期間 | **A 線（定位）** | **B 線（辨識/整合）** | 共同驗收 |
|---|---|---|---|
| **11/16–11/22 (W1)** | S0 + D1 資料集；LOC-01/02 粗糙版 | 讀 §1 契約、寫 `run_pipeline()` 骨架、Tesseract baseline | 1 張圖能端到端輸出字串（哪怕錯） |
| **11/23–11/29 (W2)** | SEG-01、GEO-01；輸出 30+ 張 rectified 圖 | OCR-01 二值化、OCR-02b 現成 OCR 調 whitelist | 共用 notebook 可跑完 10 張不 crash |
| **11/30–12/06 (W3)** | LOC 調參、GEO-02 邊界案例、跑 EV 定位段 | POST-01 規則修正、EV 全量跑、初版成功案例 | `evaluation.csv` 產出，知道 weakest link |
| **12/07–12/13 (W4)** | 補失敗案例、協助 DOC 方法論章節 | DOC 報告主體、CASE 4+2 定稿、PPT 初版 | 報告 80%、可 demo |
| **12/14–12/17** | 協助 rehearsal、修正 demo 時發現的 bug | 簡報 rehearsal、格式檢查、上傳 Moodle | 12/18 12:00 前已上傳 |

> ⚠️ 簡報自 **Week 11** 開始（暫定）→ **12 月初就必須有可 demo 版本**。
> ⚠️ 2 人組**沒有 buffer 空間**：W3 若 EV 結果太差，必須立刻砍加分項、只保 baseline 能跑。

---

## 5. 加分項（2 人版：**只挑 2 個**，其餘寫進報告 future work 即可）

| 加分項 | 內容 | 認領 | 備註 |
|---|---|---|---|
| B2 | 自製字元切分 + 模板/小 CNN 辨識，與 EasyOCR 對照 | B（有餘力） | **最高性價比**：直接對應「不可只用現成套件」 |
| B4 | Ablation study：逐一關閉模組看準確率變化 | B（用 EV 就很便宜） | 報告分數最划算 |
| B1 | YOLO detector 對照 | A（僅在 W3 提前完成時） | 時間不夠就放棄，不要冒險 |
| B3 | 資料擴增 | A | 併入 D1 順手做 |

> **2 人組策略**：加分項只做「寫起來便宜、報告加分大」的 B2 與 B4。B1 需要訓練時間，**除非 W3 提前完成否則不做**。

---

## 6. 兩個人開會 10 分鐘要定案的 5 件事

1. **誰走 A 線（定位）、誰走 B 線（辨識/整合）？** ← 先定這個，其他都是次要
2. 是否允許用 **EasyOCR / PaddleOCR**？（影響 B 線 W1 能不能一天內有 baseline）
3. 資料集從哪來？自己拍幾張？要不要用網路上公開的港車牌圖？
4. `PLATE_W/H` 統一尺寸定多少？（雙方介面，不能各寫各的）
5. **單一整合窗口**是誰？（負責把兩人 cell 貼進共用 Colab 並最終上傳；另一人只提 PR 式的 cell 片段）

> 2 人組**沒有第三方仲裁**。若對方法選擇有分歧：**先各自用 5 張圖實測，用數字決定**，不要靠感覺爭論。

---

## 7. 標註例外處理（**已納入計劃，尚未實作**）

> 背景：100 張裡有 2 張不能用一般方式評分。
> 這節只是把「要做什麼」定下來、在程式碼裡先把接口位置佔住，
> **本次不實作**。動到 §9 前先回頭看這節。

### 7.1 為什麼需要例外處理

`§9` 的準確率是「輸出的字串與 `text` 完全相符才算對」。若 `text` 填的是**猜測值**，
等於自己造一個錯的標準答案，模型答對也會被扣分。所以完全不可判讀的那張維持 **`text` 空白**，
改用 `difficulty` 標記「不可評分」，評估時明確排除 —— 而不是硬猜一個值，也不是整列刪掉
（刪掉會讓樣本數對不上報告寫的 100 張）。

### 7.2 現況（已定案，不要改）

| # | 檔名 | `text` | `difficulty` | 處理方式 |
|---|---|---|---|---|
| #16 | `train_IMG_4715_...` | 空白 | `unreadable` | 車牌中間 1 字被反光白塊完全蓋住，人眼亦不可判讀 → **排除**，不列入準確率 |
| #26 | `train_IMG_4965_...` | `ARTELLIA` | `hard` | 標註框對到前保桿上的品牌字樣、**不是車牌** → **保留在評估內**，預期會判錯，作為「資料集誤標」失敗案例 |

> 兩者差別很重要：#16 是「人不可判讀」（排除），#26 是「機器應該判錯」（保留，且失敗是合理結果）。

`difficulty` 實際使用 4 種值：`normal`（可直接判讀）、`hard`（模糊／部分被遮／非車牌）、
`unreadable`（完全不可判讀）、`not_plate`（標註框不是車牌；目前無此值，保留給未來）。

### 7.3 待辦清單

- [x] **文件同步**：`TASK_DIVISION.md §1` 與 notebook「`labels.csv` 欄位」兩處的
      `difficulty` 說明已補上 `unreadable` / `not_plate` 與語意
- [x] **`label_progress()` 判定修正**：改由 `_is_labelled()` 統一判定 ——
      「`text` 非空 **或** `difficulty` 屬 `UNSCORABLE_DIFFICULTIES`」才算已處理；
      `next_unlabeled()` 同步改用同一判定，否則 #16 會一直被當成待標註
- [ ] **`evaluate()` 排除邏輯**：實作 §9 時，用 `evaluable_labels()` 過濾後才計算準確率，
      並在 summary 表列出「排除張數 / 有效樣本數」
- [ ] **報告寫法**：明寫「100 張中 1 張因反光不可判讀、已排除，有效樣本 99 張」，
      並在「失敗案例分析」章節分別引用 #16（客觀不可判讀）與 #26（資料集誤標）

### 7.4 程式碼接口

- `[S0-2]` 定義 `LABEL_DIFFICULTIES` / `UNSCORABLE_DIFFICULTIES` 兩個常數，
  所有需要判斷難度的地方都引用它們，不要在各地硬寫字串
- `[D1-03]` 的 `_is_labelled()` 是「是否已處理」的唯一判定來源，
  `label_progress()` 與 `next_unlabeled()` 都呼叫它
- `[EV-01]` 的 `EVAL_EXCLUDE_DIFFICULTY` 是 `UNSCORABLE_DIFFICULTIES` 的別名，
  `evaluable_labels()` 空殼仍待實作，實作 §9 時直接填內容即可

---

## 8. Definition of Done（每個模組貼上前自我檢查）

- [ ] cell 開頭有 `# ==== [編號] 說明 ====` 標記
- [ ] 函式簽名與 §1 契約完全一致（參數、回傳型別）
- [ ] 下方有 `# --- self test ---` cell，用 `TEST_IMG` 可直接跑
- [ ] 有至少 2 張「輸入 → 輸出」可視化圖
- [ ] 在共用 notebook 上由別人重跑一次也得到同樣結果
- [ ] 有把「為什麼這樣做」寫一句話給寫報告的人

## 協作方式（2026-11-21 起）

### 版本控制

- Repo：`https://github.com/onenok/cis342`（public）
- `Ho Nok Hei`（`onenok`）為 maintainer，`Li Chi Shing`（`angus1244`）為 collaborator
- `project/shared/` 底下的 PNG 走 **Git LFS**（`git lfs install` 一次即可）

### 分支規則

**不要直接 push `master`。** 每個人開自己的分支：

| 人 | 分支前綴 | 只改哪些 cell |
|---|---|---|
| Ho Nok Hei | `nok/*` | §0–§5、§8 `[INT-01]`/`[INT-02]` |
| Li Chi Shing | `shing/*` | §6、§7、§9 |

流程：

```bash
git fetch origin
git checkout -b shing/ocr origin/master   # 一定從最新 master 開
# ...改自己的 cell...
git add -A && git commit
git push origin shing/ocr
# 到 GitHub 開 PR 回 master
```

**開分支前務必先 `git fetch` 並從 `origin/master` 開。** 若從自己的舊分支開，
PR 會把對方已完成的整節還原成空殼，而 diff 只會顯示「改了很多行」，不會警告。

### notebook 輸出

`.ipynb` 在進入 git 時會自動清除執行輸出（`tools/strip_nb_outputs.py` clean filter）。
本機檔案仍保留輸出，可以直接看結果；只有 commit 進去的版本是乾淨的。

每個 clone 只需設定一次：

```powershell
pwsh -NoProfile -File tools/setup_nb_filter.ps1
```

沒設定也不影響 pull，但你的 commit 會帶著 base64 輸出，PR 的 diff 會變得很難讀。

### 檔案交接

| 方向 | 內容 | 方式 |
|---|---|---|
| A → B | `shared/stages/`、`shared/rectified_auto/` | git（LFS），B 線 `git lfs pull` |
| B → A | `[OCR-01]`/`[OCR-02]`/`[POST-01]` 程式碼 | 分支 + PR |
| 雙向 | 契約變更、阻塞 | `tools/bridge.py`（見下節） |

### 溝通

`tools/bridge.py` 只用於**跨越分工邊界的決策**：共用契約變更、被卡住求援、
對方看不到的風險告知。進度報告寫在自己的 `AI_EDIT_LOG.md`，不要用 bridge 聊天。
