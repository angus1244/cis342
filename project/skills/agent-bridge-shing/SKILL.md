---
name: agent-bridge
description: >
  Coordinate with the other group member's AI agent through the Radmin VPN Bridge
  (tools/bridge.py) on the CIS342 licence-plate-recognition group project. Use this skill
  whenever the user says 隊友, 組員, 分工, 對齊方向, 問一下他, 他做到哪, 跟他講, 通知他一聲,
  留言板, bridge, inbox, "他改了什麼"; at the start of any work session on this project; and
  especially BEFORE or AFTER changing anything the two halves share — labels.csv 欄位,
  PLATE_W/PLATE_H, 函式契約 (localize/rectify/binarize/recognize), shared/rectified 格式,
  或檔案命名規則. The core rule: this channel carries decisions that cross the boundary
  between the two halves of the notebook. It is not a progress log and not a chat.
---

# Bridge 使用守則（shing 這端）

你是組員 **Li Chi Shing（`shing`）** 的 Agent，負責 **B 線：§6 字元辨識 → §9 評估**。
Bridge 是兩台電腦上兩個 Agent 的**留言板**，跑在 Radmin VPN 上。
CLI 語法、參數、疑難排解一律看 `shared/bridge/README.md` ——
本文件只講**什麼時候該說話、該說什麼**，不重複抄指令說明。

## 你的身分與負責範圍

| 項目 | 值 |
|---|---|
| 身分 | `shing` |
| 負責 | §6 `binarize()` / `recognize()`、§7 `postprocess()`、§8 `run_pipeline()`、§9 `evaluate()` |
| 對方 | `nok`（A 線：§0 Setup、§1 資料集、§2 前處理、§3–§5 定位/擷取/幾何校正） |

你**依賴**他給的 `shared/rectified/` 圖片，他**依賴**你的 `recognize()` 契約。
這個依賴關係就是這條通道存在的理由。

## 這個通道是什麼、不是什麼

| 是 | 不是 |
|---|---|
| 跨越兩人分工邊界的**決策**同步 | 進度日誌（「我寫完 binarize 了」） |
| 契約變更的**事前通知** | 閒聊或客套（「收到」「OK」） |
| 對方看不到的**風險告知** | 你能自己決定的事 |
| 被卡住時的**具體求援** | 把整份檔案貼過來 |

判斷標準只有一句：**這件事會不會改變他那邊的行為？** 不會，就不要寄。

## 絕不自動回覆

這是唯一的硬紅線，理由很具體：工具只能擋「5 分鐘內文字完全相同」的重送，
擋不了「收到」→「好」→「掰」這種**內容不同但毫無資訊**的一來一往。
一旦兩端都自動回，就會變成兩個 Agent 互相回覆到燒光 token 且永不收斂。

所以：

- 收到訊息後，**讀完、摘要給使用者、停下來**。不要自己產生回覆。
- 只有在「滿足了下面的觸發條件」或「使用者明確要你回」時才寄。
- 使用者問「你覺得該回什麼」時，**先把草稿給人看**，不要直接寄出。

## 開工前先收信

每個工作階段開始、以及動手改任何共用東西之前：

```powershell
py tools/bridge.py inbox --unread
```

為什麼：對方可能已經改了契約而你還不知道。專案裡最容易出事的不是寫錯程式，
而是**兩邊對同一個欄位/常數有不同認知**，然後各自都覺得自己是對的。

看完用 `ack` 標記，否則下次 `--unread` 還是會撈到同一批。

## 什麼時候要寄

四種情況，其他都先問使用者：

1. **共用契約要變更** —— 這是最重要的。包含：
   - `labels.csv` 的欄位或語意（`difficulty` 值、`note` 格式）
   - `PLATE_W` / `PLATE_H` / `TOP_K` / `MAX_SIDE` 等 `[S0-2]` 常數
   - 任何函式簽名或回傳結構（`localize` / `segment` / `rectify` / `binarize` / `recognize`）
   - `shared/rectified/` 的檔名或尺寸規則

   **要在動手之前寄，不是之後。** 事後通知等於讓他先撞牆再被告知有牆。

2. **你需要他那邊的東西才能往下做** —— 說明你要什麼、為什麼需要、沒有它你能先做什麼。

3. **你發現他負責的部分有問題** —— 附上證據（檔名、cell 編號、實際輸出），不要只說「怪怪的」。

4. **回答他直接問你的問題**。

## 什麼時候不要寄

- 只是報告進度 → 寫進你自己的筆記
- 只是確認收到 → 不必，`ack` 就是確認
- 事情還沒定案、只是「可能」「也許」→ 先自己查清楚
- 可以自己決定且不影響他 → 直接做，做完在下次必要訊息裡提一句

## 訊息怎麼寫

一則只談一件事。用 `part` 說明涉及哪一節。

三段式，缺一不可：

```
結論：<你決定了什麼 / 發現了什麼問題>
影響：<他那邊會有什麼後果 —— 沒有影響就寫「無」>
要做：<要他做什麼具體動作，或「不用動作，知會而已」>
```

範例（好）：

```powershell
py tools/bridge.py send --to nok --part "§6 OCR" --text @"
結論：binarize() 需要 upright_mask 才不會把補邊算成黑邊。
影響：若你之後改 shared/rectified/ 的補邊顏色或尺寸，我這邊要跟著改。
要做：維持 480x140 與灰色 (32,32,32) 補邊，不要改成純黑。
"@
```

範例（壞，不要這樣）：

```
圖我收到了，我試試看
```

後者沒有結論、沒有影響、沒有動作 —— 等於浪費一次往返。

### 寫訊息的具體約定

- **不要貼整份檔案**。引用路徑與 cell 編號，例如 `[S0-2]`、`[GEO-01]`。
- 超過 8000 字會被工具拒絕，但真正的界線更低：一則超過 ~20 行通常代表你要拆成兩則。
- 中文直接用，不需要 ASCII 化。工具是 UTF-8。
- 有圖片或長表格要給 → 放進共用資料夾並告知路徑，不要塞進訊息。

## 指令速查

只列日常會用到的，完整參數看 `README.md`。

```powershell
py tools/bridge.py status              # 連不連得上（失敗先看這步）
py tools/bridge.py inbox --unread      # 收未讀
py tools/bridge.py inbox --json        # 要自己解析時用
py tools/bridge.py send --part "§6 OCR" --text "..."
py tools/bridge.py ack                 # 看完標記已讀
```

環境變數設一次就不用每次打 `--server`：

```powershell
$env:BRIDGE_URL  = "http://26.123.142.162:8791"   # nok 那台
$env:BRIDGE_PEER = "shing"
```

## 兩件關於 `shared/rectified/` 的事

**1. 那批圖不是 pipeline 產出。**
目前 `[LOC-01]`→`[GEO-01]` 還沒實作，那些圖是用 `labels.csv` 的 ground-truth bbox
直接裁切的替代品。所以：

- 拿它開發 OCR 完全可以
- 但**不能**用它算 §9 準確率（等於用答案做題）
- 報告裡也不能寫成 pipeline 的產出

**2. 它沒有做透視校正。**
資料集近半數的 bbox 接近正方形（車牌在原圖中是斜拍），所以圖是**等比縮放 + 置中補灰邊**，
較方的車牌左右會留白。

這對你的 `binarize()` 有直接影響：**不能假設整張 480×140 都是車牌**。
要用 `<stem>_mask.png` 判斷有效區（255 = 真實影像、0 = 補邊）。

## 連不上時怎麼處理

先跑 `status`。若失敗：

- **不要自己去起伺服器當替代**。若真要換你跑，那是「網路曝露」的決定，先問人類。
- 把失敗訊息給使用者，並提醒可能是對方那台沒開服務。
- 注意 Radmin VPN **擋 ICMP**，`ping` 不通是正常的，不代表連不上。
  要測請用 `Test-NetConnection -ComputerName 26.123.142.162 -Port 8791`。

## 與 README 的分工

| 文件 | 負責什麼 | 誰看 |
|---|---|---|
| `shared/bridge/README.md` | CLI 語法、參數、疑難排解 | 人 |
| 本文件 | 何時說、說什麼、絕不做什麼 | Agent |

要改指令行為時改 README 與 `tools/bridge.py`；要改協作習慣時改本文件。
兩邊不要互相抄，否則遲早不同步。