"""匯出校正後的車牌圖到 shared/rectified/，供 B 線（§6 OCR）開發使用。

用途：§5 `[GEO-01]` 的完整實作還沒完成，但 B 線不能因此停擺。
本工具用 `labels.csv` 的 ground-truth bbox 直接裁切並縮放到契約尺寸，
先給出「尺寸與格式都正確」的圖，讓 OCR 可以先開發。
日後 `[GEO-01]` 完成後，改由 pipeline 輸出覆蓋同一個目錄即可。

用法：
    # 先確認有哪些可選
    .venv\\Scripts\\python.exe tools\\export_rectified.py --list

    # 匯出前 2 張（預設 normal 難度優先，跳過 unreadable）
    .venv\\Scripts\\python.exe tools\\export_rectified.py --limit 2

    # 指定檔名（可用 labels.csv 檔名的前綴或子字串）
    .venv\\Scripts\\python.exe tools\\export_rectified.py IMG_5129 IMG_5303

    # 全部 99 張可評分的都匯出
    .venv\\Scripts\\python.exe tools\\export_rectified.py --all
"""

from __future__ import annotations

import argparse
import os
import re
import sys

import cv2
import numpy as np
import pandas as pd

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LABELS = os.path.join(PROJ, "data", "labels.csv")
IMAGES = os.path.join(PROJ, "data", "images")
OUT_DIR = os.path.join(PROJ, "shared", "rectified")

# 與 notebook [S0-2] 的契約保持一致；改這裡也要同步改 notebook
PLATE_W, PLATE_H = 480, 140
UNSCORABLE = ("unreadable", "not_plate")

BBOX_RE = re.compile(r"bbox=(-?\d+),(-?\d+),(\d+),(\d+)")

# 縮放後留白的填色（灰），避免純黑被誤認為車牌黑邊或字元
PAD_VALUE = 32


def fit_to_contract(crop: np.ndarray) -> tuple[np.ndarray | None, np.ndarray | None]:
    """把車牌裁切等比縮放並置中到 PLATE_W x PLATE_H，不改變長寬比。

    為什麼不直接 resize：這批資料有近半數的 bbox 接近正方形（車牌在原圖中
    旋轉或斜拍）。直接拉伸成 480x140 會把字壓扁 —— 字高僅剩原來的 1/7，
    OCR 的任何參數在這種圖上都調不準。

    這裡保留原比例、不足處補邊，代價是較方的車牌左右會留白；
    但「字不變形」對開發 OCR 遠比「填滿畫面」重要。
    真正的透視校正（把斜拍拉成正視）仍屬 [GEO-01] 的工作範圍。

    回傳 (upright_bgr, mask_uint8)；mask 只在有影像的區域為 255。
    """
    ch, cw = crop.shape[:2]
    if ch < 2 or cw < 2:
        return None, None

    scale = min(PLATE_W / cw, PLATE_H / ch)
    nw = max(1, int(round(cw * scale)))
    nh = max(1, int(round(ch * scale)))
    resized = cv2.resize(crop, (nw, nh), interpolation=cv2.INTER_CUBIC)

    upright = np.full((PLATE_H, PLATE_W, 3), PAD_VALUE, np.uint8)
    area = np.zeros((PLATE_H, PLATE_W), np.uint8)
    x0, y0 = (PLATE_W - nw) // 2, (PLATE_H - nh) // 2
    upright[y0 : y0 + nh, x0 : x0 + nw] = resized
    area[y0 : y0 + nh, x0 : x0 + nw] = 255
    return upright, area


def load_df() -> pd.DataFrame:
    if not os.path.exists(LABELS):
        sys.exit(f"找不到 {LABELS}，請先執行 notebook 的 [D1-02]")
    df = pd.read_csv(LABELS, dtype=str, encoding="utf-8-sig").fillna("")
    return df.reset_index(drop=True)


def export_one(row: pd.Series) -> tuple[bool, str]:
    """裁切一張車牌並寫入 shared/rectified/<stem>.png。回傳 (成功, 訊息)。"""
    fname = row["file"]
    src = os.path.join(IMAGES, fname)
    if not os.path.exists(src):
        return False, f"缺影像檔：{fname}"

    m = BBOX_RE.search(str(row["note"]))
    if not m:
        return False, f"note 沒有 bbox：{fname}"
    x, y, w, h = (int(v) for v in m.groups())

    img = cv2.imread(src)
    if img is None:
        return False, f"讀不到影像：{fname}"

    H, W = img.shape[:2]
    # bbox 是 COCO 原始座標，直接裁切即可 —— 這裡刻意不經過 load_image()，
    # 因為 load_image() 會把最長邊縮到 1280，bbox 就必須跟著換算，
    # 多一層換算就多一個出錯機會。原圖裁切最單純。
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(W, x + w), min(H, y + h)
    if x1 <= x0 or y1 <= y0:
        return False, f"bbox 超出影像範圍：{fname}"

    crop = img[y0:y1, x0:x1].copy()
    if crop.size == 0:
        return False, f"裁切結果為空：{fname}"

    upright, area = fit_to_contract(crop)
    if upright is None:
        return False, f"影像太小無法輸出：{fname}"

    stem = os.path.splitext(fname)[0]
    cv2.imwrite(os.path.join(OUT_DIR, f"{stem}.png"), upright)

    # mask 只標出「真的有影像」的區域：等比縮放後留白的部分為 0。
    # 這讓 B 線可以正確判斷哪些像素是車牌、哪些是補邊。
    cv2.imwrite(os.path.join(OUT_DIR, f"{stem}_mask.png"), area)

    aspect = w / max(h, 1)
    note = ""
    if aspect < 2.0:
        note = "  ⚠️ 框很方（車牌在原圖中旋轉/斜拍），左右會留白"
    return True, f"{fname} -> {stem}.png  (原框 {w}x{h}, AR={aspect:.2f}){note}"


def main() -> None:
    ap = argparse.ArgumentParser(description="匯出校正車牌圖到 shared/rectified/")
    ap.add_argument("keys", nargs="*", help="檔名關鍵字（可多個）")
    ap.add_argument("--all", action="store_true", help="匯出全部可評分的列")
    ap.add_argument("--limit", type=int, default=0, help="只匯出前 N 張")
    ap.add_argument("--list", action="store_true", help="只列出可匯出的列，不寫檔")
    args = ap.parse_args()

    df = load_df()
    ok = ~df["difficulty"].isin(UNSCORABLE) & (df["text"].str.strip() != "")
    pool = df[ok]

    if args.list or not (args.keys or args.all or args.limit):
        print(f"可匯出 {len(pool)} 張（已排除 unreadable 或 text 空白）\n")
        for i, r in pool.head(20).iterrows():
            print(f"  {i + 1:3d}  {r['file'][:52]:<52}  {r['text']:<10} {r['difficulty']}")
        if len(pool) > 20:
            print(f"  … 其餘 {len(pool) - 20} 張略過")
        print("\n用法：--limit 2 ｜ --all ｜ 或直接給檔名關鍵字")
        return

    if args.keys:
        sel = pool[pool["file"].apply(lambda f: any(k in f for k in args.keys))]
        if sel.empty:
            sys.exit(f"沒有檔名包含 {args.keys} 的可匯出列，先用 --list 看看")
    else:
        sel = pool

    if args.limit:
        sel = sel.head(args.limit)

    os.makedirs(OUT_DIR, exist_ok=True)
    n_ok = 0
    for _, row in sel.iterrows():
        good, msg = export_one(row)
        print(("  ✅ " if good else "  ❌ ") + msg)
        n_ok += good

    print(f"\n完成：{n_ok} / {len(sel)} 張 -> {OUT_DIR}")
    if n_ok:
        print("提醒：這是 GT bbox 裁切，不是真透視校正。")
        print("      [GEO-01] 完成後請重跑覆蓋，否則報告不能說這是 pipeline 輸出。")


if __name__ == "__main__":
    main()