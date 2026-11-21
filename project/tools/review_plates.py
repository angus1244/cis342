"""車牌標註審核工具（Gradio）

用途：把 `data/labels.csv` 的 100 張車牌裁切圖分頁顯示，讓人逐張核對 `text` 欄是否正確。
這是不進交付版本的開發輔助工具，不屬於 notebook 內容。

啟動：`.venv\\Scripts\\python.exe tools\\review_plates.py`

為什麼要分頁：`gr.Gallery` 一次塞 100 張圖（每張都已放大到 800px 寬）會讓
單次 response 變成數十 MB，瀏覽器要等很久才畫得出來。所以只送出「當前這一頁」的
檔案路徑，其餘留在磁碟上不碰。
"""

from __future__ import annotations

import json
import os
import re
import unicodedata

import cv2
import gradio as gr
import pandas as pd

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LABELS = os.path.join(PROJ, "data", "labels.csv")
IMAGES = os.path.join(PROJ, "data", "images")
CACHE = os.path.join(PROJ, "debug", "review_cache")
STATE_FILE = os.path.join(PROJ, "debug", "review_state.json")

PAGE_SIZES = [6, 8, 10, 12, 20]
DEFAULT_PAGE_SIZE = 8
CROP_WIDTH = 800  # 裁切圖統一放大到這個寬度，Gallery 與大圖預覽共用同一份

DIFFICULTY_CHOICES = ["normal", "hard", "unreadable", "not_plate"]
FR_CHOICES = ["", "front", "rear"]

BBOX_RE = re.compile(r"bbox=(-?\d+),(-?\d+),(\d+),(\d+)")


# ---------------------------------------------------------------- 資料與影像


def load_df() -> pd.DataFrame:
    df = pd.read_csv(LABELS, dtype=str, encoding="utf-8-sig").fillna("")
    return df.reset_index(drop=True)


def save_df(df: pd.DataFrame) -> None:
    df.to_csv(LABELS, index=False, encoding="utf-8-sig")


def normalize_plate_text(text: str) -> str:
    """與 notebook `[D1-01]` 完全相同的正規化規則，避免兩邊結果不一致。"""
    s = unicodedata.normalize("NFKC", str(text)).upper()
    return re.sub(r"[^0-9A-Z\u4e00-\u9fff]", "", s)


def build_cache(df: pd.DataFrame) -> list[str]:
    """把每一列的車牌區域裁切、放大後存成 JPEG，回傳與列序對齊的路徑清單。

    先落檔再交給 Gallery，是因為 Gallery 收到 numpy 陣列時每次 response 都要重新
    編碼；給路徑則由 Gradio 直接靜態送出，而且同一頁來回翻也不會重算。
    """
    os.makedirs(CACHE, exist_ok=True)
    paths: list[str] = []
    for i, row in df.iterrows():
        out = os.path.join(CACHE, f"p{i + 1:03d}.jpg")
        paths.append(out)
        src = os.path.join(IMAGES, row["file"])
        m = BBOX_RE.search(str(row["note"]))
        if os.path.exists(out) or not m or not os.path.exists(src):
            continue
        img = cv2.imread(src)
        if img is None:
            continue
        x, y, w, h = (int(v) for v in m.groups())
        # 上下多留一點，方便判斷是白底還是黃底（正反面）；左右留少一點避免抓到隔壁車
        mx, my = int(w * 0.10), int(h * 0.35)
        H, W = img.shape[:2]
        crop = img[max(0, y - my) : min(H, y + h + my), max(0, x - mx) : min(W, x + w + mx)]
        if crop.size == 0:
            continue
        ch, cw = crop.shape[:2]
        scale = CROP_WIDTH / cw
        crop = cv2.resize(
            crop, (CROP_WIDTH, max(1, int(ch * scale))), interpolation=cv2.INTER_CUBIC
        )
        cv2.imwrite(out, crop, [cv2.IMWRITE_JPEG_QUALITY, 88])
    return paths


def load_reviewed() -> set[str]:
    if not os.path.exists(STATE_FILE):
        return set()
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f).get("reviewed", []))
    except (ValueError, OSError):
        return set()


def save_reviewed(reviewed: set[str]) -> None:
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump({"reviewed": sorted(reviewed)}, f, ensure_ascii=False, indent=1)


# ---------------------------------------------------------------- 畫面更新


def make_progress(df: pd.DataFrame, reviewed: set[str]) -> str:
    done = sum(1 for f in df["file"] if f in reviewed)
    return f"**進度：{done} / {len(df)}** 已審核　·　剩 {len(df) - done} 張"


def gallery_page(
    df: pd.DataFrame, paths: list[str], reviewed: set[str], page: int, size: int
):
    """只回傳當前頁的 (路徑, 標題) 清單 —— 這是效能的關鍵。"""
    start = page * size
    stop = min(start + size, len(df))
    items = []
    for i in range(start, stop):
        mark = "✅ " if df.at[i, "file"] in reviewed else ""
        cap = f"#{i + 1}\u3000{mark}{df.at[i, 'text'] or '（空白）'}"
        items.append((paths[i], cap))
    return items, start, stop


def page_label(page: int, size: int, total: int) -> str:
    start = page * size
    stop = min(start + size, total)
    return f"第 {start + 1}–{stop} 張（共 {total} 張）"


def detail_for(df: pd.DataFrame, paths: list[str], idx: int):
    row = df.iloc[idx]
    return (
        paths[idx],
        row["text"],
        row["difficulty"] if row["difficulty"] in DIFFICULTY_CHOICES else "normal",
        row["front_rear"] if row["front_rear"] in FR_CHOICES else "",
        f"**#{idx + 1}**\u3000`{row['file']}`",
    )


# ---------------------------------------------------------------- 主程式


def build_app() -> gr.Blocks:
    df0 = load_df()
    paths0 = build_cache(df0)
    reviewed0 = load_reviewed()

    with gr.Blocks(title="車牌標註審核") as demo:
        gr.Markdown(
            "## 車牌標註審核\n"
            "點選下方任一張圖 → 右側可修改車牌字串 → 按「儲存並下一張」。\n"
            "**判定說明**：`normal` 可直接判讀、`hard` 模糊或部分被遮、"
            "`unreadable` 完全看不清、`not_plate` 這個框根本不是車牌。"
        )

        df_state = gr.State(df0)
        paths_state = gr.State(paths0)
        page_state = gr.State(0)
        reviewed_state = gr.State(reviewed0)
        idx_state = gr.State(0)

        with gr.Row():
            with gr.Column(scale=7):
                gallery = gr.Gallery(
                    value=gallery_page(df0, paths0, reviewed0, 0, DEFAULT_PAGE_SIZE)[0],
                    label=page_label(0, DEFAULT_PAGE_SIZE, len(df0)),
                    columns=4,
                    rows=2,
                    height="auto",
                    object_fit="contain",
                    allow_preview=True,
                )
                with gr.Row():
                    prev_btn = gr.Button("← 上一頁")
                    page_box = gr.Number(
                        value=1, label="頁碼", precision=0, minimum=1, scale=0
                    )
                    next_btn = gr.Button("下一頁 →")
                    size_dd = gr.Dropdown(
                        choices=PAGE_SIZES,
                        value=DEFAULT_PAGE_SIZE,
                        label="每頁張數",
                        scale=0,
                    )
                progress_md = gr.Markdown(make_progress(df0, reviewed0))

            with gr.Column(scale=5):
                detail_md = gr.Markdown("**尚未選取**\u3000請先點左邊任一張圖")
                preview = gr.Image(label="放大預覽", height=260)
                text_box = gr.Textbox(
                    label="車牌字串（可直接修改，儲存時會自動大寫並去掉圓點／連字號）",
                    placeholder="例：RDA2388",
                )
                with gr.Row():
                    diff_radio = gr.Radio(
                        choices=DIFFICULTY_CHOICES,
                        value="normal",
                        label="判定",
                        scale=2,
                    )
                    fr_radio = gr.Radio(
                        choices=FR_CHOICES,
                        value="",
                        label="正／反面（選填）",
                        scale=1,
                    )
                with gr.Row():
                    save_btn = gr.Button("儲存並下一張", variant="primary")
                    skip_btn = gr.Button("略過這張")
                status_md = gr.Markdown("")

        gr.Markdown(
            "> 提示：`front` 通常白底、`rear` 通常黃底。跨境車牌（粵Z）請保留中文字。"
        )

        # ---------- 事件 ----------

        def relabel(page: int, size: int, total: int):
            return gr.update(label=page_label(page, size, total))

        def on_size(
            df: pd.DataFrame, paths: list[str], reviewed: set[str], size: int
        ):
            items, _, _ = gallery_page(df, paths, reviewed, 0, int(size))
            return (
                gr.update(value=items, label=page_label(0, int(size), len(df))),
                0,
                1,
                make_progress(df, reviewed),
            )

        def on_prev(
            df: pd.DataFrame, paths: list[str], reviewed: set[str], page: int, size: int
        ):
            page = max(0, page - 1)
            items, _, _ = gallery_page(df, paths, reviewed, page, int(size))
            return (
                gr.update(value=items, label=page_label(page, int(size), len(df))),
                page,
                page + 1,
            )

        def on_next(
            df: pd.DataFrame, paths: list[str], reviewed: set[str], page: int, size: int
        ):
            last = max(0, (len(df) - 1) // int(size))
            page = min(last, page + 1)
            items, _, _ = gallery_page(df, paths, reviewed, page, int(size))
            return (
                gr.update(value=items, label=page_label(page, int(size), len(df))),
                page,
                page + 1,
            )

        def on_jump(
            df: pd.DataFrame,
            paths: list[str],
            reviewed: set[str],
            page_number,
            size: int,
        ):
            last = max(0, (len(df) - 1) // int(size))
            page = min(last, max(0, int(page_number or 1) - 1))
            items, start, _ = gallery_page(df, paths, reviewed, page, int(size))
            return (
                gr.update(value=items, label=page_label(page, int(size), len(df))),
                page,
                page + 1,
                start,
                *detail_for(df, paths, start),
            )

        def on_select(
            df: pd.DataFrame,
            paths: list[str],
            page: int,
            size: int,
            evt: gr.SelectData,
        ):
            idx = page * int(size) + evt.index
            if idx >= len(df):
                return 0, "", "normal", "", ""
            return idx, *detail_for(df, paths, idx)

        def on_save(
            df: pd.DataFrame,
            paths: list[str],
            reviewed: set[str],
            idx: int,
            text: str,
            difficulty: str,
            front_rear: str,
        ):
            df = df.copy()
            clean = normalize_plate_text(text)
            df.at[idx, "text"] = clean
            df.at[idx, "difficulty"] = difficulty
            df.at[idx, "front_rear"] = front_rear
            save_df(df)
            reviewed = set(reviewed) | {df.at[idx, "file"]}
            save_reviewed(reviewed)

            nxt = min(idx + 1, len(df) - 1)
            warn = ""
            if text and not clean:
                warn = "　⚠️ 原輸入沒有任何英數或中文，已存成空白"
            elif str(text) != clean:
                warn = f"　（已正規化為 `{clean}`）"
            status = f"✅ 已儲存 **#{idx + 1}** = `{clean or '（空白）'}`{warn}"
            return (
                df,
                reviewed,
                nxt,
                *detail_for(df, paths, nxt),
                status,
                make_progress(df, reviewed),
            )

        def on_skip(df: pd.DataFrame, paths: list[str], idx: int):
            nxt = min(idx + 1, len(df) - 1)
            return nxt, *detail_for(df, paths, nxt), ""

        # 分頁
        size_dd.change(
            on_size,
            inputs=[df_state, paths_state, reviewed_state, size_dd],
            outputs=[gallery, page_state, page_box, progress_md],
        )
        prev_btn.click(
            on_prev,
            inputs=[df_state, paths_state, reviewed_state, page_state, size_dd],
            outputs=[gallery, page_state, page_box],
        )
        next_btn.click(
            on_next,
            inputs=[df_state, paths_state, reviewed_state, page_state, size_dd],
            outputs=[gallery, page_state, page_box],
        )
        page_box.submit(
            on_jump,
            inputs=[df_state, paths_state, reviewed_state, page_box, size_dd],
            outputs=[gallery, page_state, page_box, idx_state, preview, text_box,
                     diff_radio, fr_radio, detail_md],
        )

        # 選圖與編輯
        gallery.select(
            on_select,
            inputs=[df_state, paths_state, page_state, size_dd],
            outputs=[idx_state, preview, text_box, diff_radio, fr_radio, detail_md],
        )
        save_btn.click(
            on_save,
            inputs=[df_state, paths_state, reviewed_state, idx_state, text_box,
                    diff_radio, fr_radio],
            outputs=[df_state, reviewed_state, idx_state, preview, text_box,
                     diff_radio, fr_radio, detail_md, status_md, progress_md],
        )
        skip_btn.click(
            on_skip,
            inputs=[df_state, paths_state, idx_state],
            outputs=[idx_state, preview, text_box, diff_radio, fr_radio, detail_md,
                     status_md],
        )

    return demo


def find_free_port(start: int = 7870, stop: int = 7920) -> int:
    """找一個沒人用的 port。

    7860–7869 這一段常被其他專案（例如 cis341 的 Gradio）或 Windows 保留區佔住，
    寫死會直接 `OSError: Cannot find empty port`，所以改成往後掃。
    """
    import socket

    for port in range(start, stop):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                try:
                    s.bind(("127.0.0.1", port))
                    return port
                except OSError:
                    continue
    raise OSError(f"{start}–{stop} 之間找不到可用的 port")


if __name__ == "__main__":
    port = find_free_port()
    print(f"車牌標註審核工具啟動於 http://127.0.0.1:{port}")
    build_app().launch(
            server_port=port,
        allowed_paths=[CACHE],
        inbrowser=True,
        show_error=True,
            theme=gr.themes.Soft(),
    )