"""把 notebook 的執行輸出清掉，讓 git 的 diff 只反映程式碼變更。

用途：git clean filter。設定方式見 tools/setup_nb_filter.ps1。
本機的 .ipynb 仍然保留輸出，只有「進到 git 的那一份」會被清掉。

用法：
    python tools/strip_nb_outputs.py <file.ipynb>    # 就地清除
    python tools/strip_nb_outputs.py --stdin         # 給 git filter 用
"""

import json
import sys


def strip(nb_text: str) -> str:
    nb = json.loads(nb_text)
    changed = False
    for cell in nb.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
        if cell.get("outputs"):
            cell["outputs"] = []
            changed = True
        if cell.get("execution_count") is not None:
            cell["execution_count"] = None
            changed = True
        md = cell.get("metadata") or {}
        if "execution" in md:          # nbconvert 寫入的時間戳，每次執行都不同
            md.pop("execution")
            changed = True
    if not changed:
        return nb_text
    return json.dumps(nb, indent=1, ensure_ascii=False, sort_keys=True) + "\n"


def main() -> int:
    if "--stdin" in sys.argv:
        data = sys.stdin.buffer.read().decode("utf-8")
        if not data.strip():
            return 0
        # 一律走 buffer：Windows 主控台預設 cp950，直接寫 str 會在中文/emoji 上炸
        sys.stdout.buffer.write(strip(data).encode("utf-8"))
        sys.stdout.buffer.flush()
        return 0

    paths = [a for a in sys.argv[1:] if not a.startswith("-")]
    if not paths:
        print(__doc__)
        return 2
    for p in paths:
        with open(p, "r", encoding="utf-8") as f:
            src = f.read()
        out = strip(src)
        if out != src:
            with open(p, "w", encoding="utf-8", newline="\n") as f:
                f.write(out)
            print(f"已清除輸出：{p}")
        else:
            print(f"沒有輸出需要清除：{p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())