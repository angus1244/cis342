# shared/rectified_auto/ — 真 pipeline 產出的校正圖（子集）

**這是 `[LOC-01]`→`[GEO-01]` 真實跑出來的结果，不是答案裁切。**
與 `shared/rectified/` 不同：那裡的圖是用 `labels.csv` 的 GT bbox 裁的，
拿它算準確率等於用答案做題；這裡的圖是模型自己定位、自己校正的。

## 內容

| 項目 | 值 |
|---|---|
| 檔名 | `<stem>.png` + `<stem>_mask.png`；`stem` = `labels.csv` 的 `file` 去掉副檔名 |
| 尺寸 | 480 × 140（`PLATE_W` × `PLATE_H`） |
| mask 語意 | **255 = 真實影像，0 = 置中補邊** |
| 數量 | 26 組（52 檔） |
| `_index.csv` | `stem`, `text`（GT 答案）, `iou`（該張定位框與 GT 的 IoU） |

## ⚠️ 這批圖有選擇偏差，不能當 §9 的分母

這 26 張是「定位框與 GT 的 IoU ≥ 0.5」的子集，也就是**已經先篩掉失敗案例**。
用它算 §9 準確率會得到偏高的假數字。

正確用法：

- ✅ 開發 / 調 §6 參數 —— 這批是乾淨且真實的輸入
- ✅ 看 §6 在「定位正確時」表現如何（上限估計）
- ❌ 報告的整體準確率 —— 那必須用 `shared/stages/` 的全部 85 個 stem 當分母

## 來源與重現

由 `notebooks/lpr_dev.ipynb` 的 `[INT-01]` `export_dataset_frontend()` 產生
中間狀態到 `shared/stages/`，再依 IoU ≥ 0.5 篩出。

目前定位實測（99 張標註）：recall@1 = 30.3%、recall@5 = 48.5%、平均最佳 IoU = 0.411。
