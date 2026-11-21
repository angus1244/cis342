# `shared/rectified/` 交接說明（給 B 線 / §6 OCR）

## 這批圖是什麼

**不是** pipeline 輸出，是**用 `labels.csv` 的 ground-truth bbox 直接裁切**的替代品。

原因：`[LOC-01]` → `[LOC-02]` → `[SEG-01]` → `[GEO-01]` 整條定位鏈還沒實作，
但 B 線的 §6 不該因此停擺。所以先給出「尺寸與格式都符合契約」的圖，讓 OCR 可以先開發。

> ⚠️ **報告不能把這批圖寫成 pipeline 的產出。** `[GEO-01]` 完成後必須重跑覆蓋，
> 且 §9 評估一律走真 pipeline，不能用這批 GT 裁切圖算準確率（那等於用答案做題）。

## 檔案契約

| 項目 | 值 |
|---|---|
| 檔名 | `<labels.csv 的檔名去掉 .jpg>.png` |
| 尺寸 | **固定 480 × 140**（`PLATE_W` × `PLATE_H`） |
| 色彩 | BGR 三通道 PNG（無損） |
| 遮罩 | `<同名>_mask.png`，單通道，255 = 真實影像，0 = 補邊 |
| 補邊顏色 | 灰 `(32, 32, 32)` |

**對應的標準答案**在 `labels.csv` 的 `text` 欄（同一個 stem 去掉 `.png` 就是 `file` 欄）。

張數：目前只放了 4 張範例（涵蓋白底與黃底）：
`GN2896`（白）、`YL7582`（白）、`GT3500`（黃）、`GG1996`（白，有反光）

要更多張：`py tools/export_rectified.py --all`（會跳過 `unreadable`，共 99 張）

## 兩個必須知道的限制

**1. 沒有做透視校正，斜拍的車牌仍是斜的**

這批資料有近半數的 bbox 接近正方形（`AR` 中位數 1.52），代表車牌在原圖中
是斜拍或旋轉的。例如 `train_IMG_1231`（`RDA2388`）的框是 953×990。

我試過自動找車牌四邊形再 warp，但失敗：車身是銀白色，色彩遮罩分不開，
`minAreaRect` 會抓到整個裁切區。所以改成**等比縮放 + 置中補邊**：

- 保留原比例，字**不變形**（這對調 OCR 參數最重要）
- 代價：較方的車牌左右會留白，實際內容區可能只佔畫面中間一塊

所以 §6 的 `binarize()` 必須能容忍補邊，不能假設「整張 480×140 都是車牌」。
用 `_mask.png` 判斷有效區域即可。

**2. `960GKF` 這類暗圖品質有限**

原圖雜訊大、對比低。這是資料本身的問題，不是裁切造成的。

## §6 可用的起點

```python
import cv2, numpy as np

stem = 'train_IMG_4540_jpg.rf.1d98a6417d83bba5fb2d53e4595861c7'
img  = cv2.imread(f'shared/rectified/{stem}.png')            # 480x140x3
mask = cv2.imread(f'shared/rectified/{stem}_mask.png', 0)    # 480x140, 0/255
```

`binarize(upright_bgr, upright_mask)` 直接把這兩個傳進去就能開始。

## 什麼時候會被覆蓋

`[GEO-01]` 實作完成後，改由 `run_pipeline()` 輸出到同一個目錄。
那時檔名會改成 `test_01.png` 這種與輸入圖對應的名字，不再用 `labels.csv` 的 stem。
B 線的程式請**不要硬編碼檔名**，用 `glob` 掃描目錄。