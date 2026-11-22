---
name: agent-bridge
description: >
  Coordinate with the other group member's AI agent through the Radmin VPN Bridge
  (tools/bridge.py) on the CIS342 licence-plate-recognition group project. Use this skill
  whenever the user says 隊友, 組員, 分工, 對齊方向, 問一下他, 他做到哪, 跟他講, 通知他一聲,
  留言板, bridge, inbox, "他改了什麼"; at the start of any work session on this project; and
  especially BEFORE or AFTER changing anything the two halves share — labels.csv 欄位,
  PLATE_W/PLATE_H, 函式契約 (localize/rectify/binarize/recognize), shared/rectified 格式,
    或檔案命名規則. Also use when sending a status receipt ([READ-OK] / [READ-QUESTION] /
    [READ-BLOCKED] / [READ-LATER] / [READ-CONFLICT]) after reading a teammate message.
    The core rule: this channel carries decisions that cross the boundary between the two
    halves of the notebook. It is not a progress log and not a chat.
---

# Bridge 使用守則（nok 這端）

Bridge 是兩台電腦上兩個 Agent 的**留言板**，跑在 Radmin VPN 上。
CLI 語法、參數、疑難排解一律看 [`shared/bridge/README.md`](../../../shared/bridge/README.md) ——
本文件只講**什麼時候該說話、該說什麼**，不重複抄指令說明。

## 這個通道是什麼、不是什麼

| 是 | 不是 |
|---|---|
| 跨越兩人分工邊界的**決策**同步 | 進度日誌（「我寫完 binarize 了」） |
| 契約變更的**事前通知** | 無狀態資訊的客套（「收到」「OK」「好」） |
| 對方看不到的**風險告知** | 你能自己決定的事 |
| 被卡住時的**具體求援** | 把整份檔案貼過來 |
| **狀態回執**（已讀是哪一種已讀，見下節） | 技術辯論、逐步討論 |

判斷標準分兩層：

- **正常訊息**：這件事會不會改變他那邊的行為？不會，就不要寄。
- **狀態回執**：不用改變他的行為，但要讓他知道你這邊的處境（見下一節）。

## 允許「一次」自動回執（狀態回執）

原本是「絕不自動回覆」。現在放寬成：**每收到一則訊息，最多自動回一則狀態回執**。

理由很具體：`ack` 只告訴對方「游標推進了」，但沒有告訴他**為什麼**推進 ——
是認同？是有疑問？是要等他？對方只能乾等，不知道該不該繼續做。
狀態回執就是補這個缺口：讓「已讀」變成有語意的已讀。

### 硬性上限：一次，而且只回執

| 規則 | 說明 |
|---|---|
| **每則訊息最多回一則** | 收到 #28 → 最多寄 #29 一則回執。不得針對自己的回執再回 |
| **禁止對回執再回執** | 若收到的訊息本身是回執（`part` 以「回執」開頭），**只 `ack`，不寄任何東西** |
| **禁止技術辯論** | 回執裡不新增主張、不提新方案、不反駁。要辯論 → 停下來問使用者 |
| **必須有狀態碼** | 沒有狀態碼的回執等於客套，不准寄 |

第三條是關鍵：只放寬「告知狀態」，不放寬「自動對話」。
一旦允許在回執裡講技術意見，兩端就會開始互相論證 —— 那是本來要防的東西。

### 五種狀態碼（必須選一個）

回執第一行必須是這五種之一，方便對方一眼分類：

```
[READ-OK]       收到，認同，我這邊不需要動作
[READ-QUESTION] 收到，但有一點要先問清楚（問題必須寫在回執裡，只寫一次）
[READ-BLOCKED]  收到，但我這邊被卡住／要等你的東西（寫清楚等什麼）
[READ-LATER]    收到，但現在不做，我要先處理手上的事（寫清楚大約何時）
[READ-CONFLICT] 收到，但和我這邊的實測數字／契約不一致（指出哪一項，不要展開辯論）
```

`[READ-CONFLICT]` 最容易失控 —— 它只准「指出不一致的那一項與我方數字」，
不准推論原因、不准提修正方案。原因與方案留給人決定後的下一次正常訊息。

### 回執格式

三段式照舊，但第一行是狀態碼：

```
[READ-OK] §5 幾何校正 #28
結論：已讀，我方不需改動。
影響：無。
要做：不用動作。
```

長度上限：**8 行**。超過 8 行代表這不是回執，是正常訊息 → 停下來問使用者。

### 什麼時候**不要**回執

- 訊息只是 `[READ-*]` 回執 → 只 `ack`
- 訊息是廣播 `to=all` 且與你無關 → 只 `ack`
- 你還沒讀完／還沒查證 → 先 `ack`，查清楚後才發正式訊息（**不要**先回 `[READ-LATER]` 再回一次）
- 使用者明確說「不要回」

### 與 `ack` 的關係

`ack` 仍然是必要的：它推進游標，避免下次 `--unread` 重撈。
**順序是：`inbox --unread` → `ack` → 寄回執**。
先 `ack` 才寄，這樣就算寄失敗，也不會下次重複讀到同一則而重寄。

## 開工前先收信

每個工作階段開始、以及動手改任何共用東西之前：

```powershell
py tools/bridge.py inbox --unread
```

為什麼：對方可能已經改了契約而你還不知道。專案裡最容易出事的不是寫錯程式，
而是**兩邊對同一個欄位/常數有不同認知**，然後各自都覺得自己是對的。

看完用 `ack` 標記，否則下次 `--unread` 還是會撈到同一批。

## 什麼時候要寄（正常訊息，非回執）

四種情況，其他都先問使用者：

1. **共用契約要變更** —— 這是最重要的。包含：
   - `labels.csv` 的欄位或語意（`difficulty` 值、`note` 格式）
   - `PLATE_W` / `PLATE_H` / `TOP_K` / `MAX_SIDE` 等 `[S0-2]` 常數
   - 任何函式簽名或回傳結構（`localize` / `segment` / `rectify` / `binarize` / `recognize`）
   - `shared/rectified/` 的檔名或尺寸規則

   **要在動手之前寄，不是之後。** 事後通知等於讓他先撞牆再被告知有牆。

2. **你需要他那邊的東西才能往下做** —— 說明你要什麼、為什麼需要、沒有它你能先做什麼。

3. **你發現他負責的部分有問題** —— 附上證據（檔名、行號、實際輸出），不要只說「怪怪的」。

4. **回答他直接問你的問題**。

> 這四種是「正常訊息」，沒有長度上限（仍建議 ≤20 行），可以含技術內容。
> 狀態回執是另一種東西，見上一節。

## 什麼時候不要寄

- 只是報告進度 → 寫進你自己的 `AI_EDIT_LOG.md`
- 只是確認收到 → 狀態回執就夠，不要另外再寄一則正常訊息
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
py tools/bridge.py send --to shing --part "§5 幾何校正" --text @"
結論：shared/rectified/ 的圖改成等比縮放 + 置中補邊，不再拉伸成 480x140。
影響：較方的車牌左右會留白，binarize() 不能假設整張都是車牌。
要做：用 <stem>_mask.png 判斷有效區（255=真實影像、0=補邊）。
"@
```

範例（壞，不要這樣）：

```
我这边改好了，你看一下
```

後者沒有結論、沒有影響、沒有動作，對方只能再問一輪 —— 這就是浪費一次往返。

### 寫訊息的具體約定

- **不要貼整份檔案**。引用路徑與 cell 編號，例如 `notebooks/lpr_dev.ipynb` 的 `[S0-2]`。
- 超過 8000 字會被工具拒絕，但真正的界線更低：一則超過 ~20 行通常代表你要拆成兩則。
- 中文直接用，不需要 ASCII 化。工具是 UTF-8。
- 有圖片或長表格要給 → 放進 `shared/` 並告知路徑，不要塞進訊息。

## 指令速查

只列日常會用到的，完整參數看 README。

```powershell
py tools/bridge.py status              # 連不連得上（失敗先看這步）
py tools/bridge.py inbox --unread      # 收未讀
py tools/bridge.py inbox --json        # 要自己解析時用
py tools/bridge.py send --part "§6 OCR" --text "..."
py tools/bridge.py ack                 # 看完標記已讀
```

狀態回執的實例（注意 `--part` 以「回執」開頭，方便對方端機器識別）：

```powershell
py tools/bridge.py send --to shing --part "回執 §10 入口" --text @"
[READ-QUESTION] §10 入口 #28
結論：已讀，但整圖兜底在 99 張上會不會拖慢要確認。
影響：我這邊暫不把 wholeimage 併入主評估。
要做：先不用動作，等我量完再回報。
"@
```

環境變數設一次就不用每次打 `--server`：`BRIDGE_URL`、`BRIDGE_PEER`（這端應為 `nok`）。

## 連不上時怎麼處理

先跑 `status`。若失敗：

- **不要自己去起伺服器**。`serve --host 0.0.0.0` 等於把服務開到區網上，
  這是網路曝露的決定，該由人拍板。
- 把失敗訊息給使用者，並提醒可能是對方那台沒開服務。
- 注意 Radmin VPN **擋 ICMP**，`ping` 不通是正常的，不代表連不上。
  要測請用 `Test-NetConnection -ComputerName <IP> -Port 8791`。

## 與 README 的分工

| 文件 | 負責什麼 | 誰看 |
|---|---|---|
| `shared/bridge/README.md` | CLI 語法、參數、疑難排解 | 人 |
| 本文件 | 何時說、說什麼、回執怎麼寫 | Agent |

要改指令行為時改 README 與 `tools/bridge.py`；要改協作習慣時改本文件。
兩邊不要互相抄，否則遲早不同步。