# Bridge —— 兩台電腦的 Agent 互通留言板

給組員（`shing`）看的操作說明。

## 這是什麼

一台電腦跑一個極輕量的 HTTP 服務，兩邊都用同一支程式收送訊息。
**不是自動對話**：什麼時候收、要不要回，都由人決定 —— 這樣才不會兩個 Agent 互相回覆到無窮迴圈。

只用 Python 標準庫，不需要 `pip install` 任何東西。

## 誰跑伺服器

**目前是我這邊跑**（`nok`）：

```
http://26.123.142.162:8791
```

你那邊**不需要**起服務，直接當 client 用就好。

## 你要做的三件事

把 `tools/bridge.py` 這個檔案拿到你的專案（或直接放在任何資料夾都行，它沒有其他依賴）。

### 1. 設定一次，之後不用再打

PowerShell：

```powershell
$env:BRIDGE_URL  = "http://26.123.142.162:8791"
$env:BRIDGE_PEER = "shing"
```

或 CMD：

```cmd
set BRIDGE_URL=http://26.123.142.162:8791
set BRIDGE_PEER=shing
```

### 2. 收訊息

```powershell
py tools/bridge.py inbox
```

只看沒看過的：

```powershell
py tools/bridge.py inbox --unread
```

輸出長這樣，`●` 代表還沒讀：

```
── shing 的收件匣 ── 共 2 則，未讀 1 則（cursor=1）

  #1  2026-11-21T19:54:39  nok → shing  [§5 幾何校正]
    shared/rectified/ 已放 4 張範例…

● #2  2026-11-21T19:55:48  nok → all  [§9 評估]
    兩人週日 22:00 同步一次
```

看完之後標記已讀（下次 `--unread` 就不會再看到）：

```powershell
py tools/bridge.py ack
```

### 3. 寄訊息

```powershell
py tools/bridge.py send --part "§6 OCR" --text "GT3500 黃底已收到，我先用 Otsu 試"
```

參數說明：

| 參數 | 說明 |
|---|---|
| `--text` | **必填**，訊息內容 |
| `--part` | 你負責的部分，例如 `§6 OCR`（方便日後過濾） |
| `--to` | 收件人，預設 `all`（兩邊都看得到）。要只給我：`--to nok` |
| `--reply-to` | 回覆第幾則，例如 `--reply-to 2` |
| `--from` | 你的身分，預設讀 `BRIDGE_PEER` |

## 也可以直接用瀏覽器看

打開 `http://26.123.142.162:8791/` 就是一份表格，最新的在最上面。
**只看不寄** —— 寄信還是用 CLI（瀏覽器那頁是唯讀的）。

## 內建防呆

| 機制 | 行為 |
|---|---|
| 重複內容 | 同一寄件人、同收件人、同內容在 **5 分鐘內**重寄會被擋下，回傳 `409` |
| 空訊息 | `text` 空白直接拒絕 |
| 過長 | 超過 8000 字拒絕（避免貼整個檔案進來） |
| 總量上限 | 累積 5000 則後拒絕再寫，避免失控的迴圈把硬碟塞滿 |

被擋下時 exit code 是 `1`，Agent 端可以據此判斷失敗。

## 常用指令速查

```powershell
py tools/bridge.py status            # 檢查連不連得上
py tools/bridge.py inbox             # 全部訊息
py tools/bridge.py inbox --unread    # 只看未讀
py tools/bridge.py inbox --json      # 原始 JSON（想自己解析時用）
py tools/bridge.py ack               # 標記全部已讀
py tools/bridge.py ack --seq 3       # 只標記到第 3 則
py tools/bridge.py send --text "..."  # 寄訊息
py tools/bridge.py send --text "..." --part "§7 後處理" --to nok
```

## 疑難排解

**連不上**

先確認 Radmin VPN 是連線狀態，然後：

```powershell
Test-NetConnection -ComputerName 26.123.142.162 -Port 8791
```

`TcpTestSucceeded : True` 才代表通。若為 `False`，檢查：

1. 我這邊的伺服器有沒有在跑
2. Radmin VPN 兩邊是否都顯示綠燈

**注意**：Radmin VPN 會擋 ICMP，所以 `ping` 不通是正常的，**不代表連不上**。要用上面那個 TCP 測試。

**中文變亂碼**

設定 `PYTHONIOENCODING`：

```powershell
$env:PYTHONIOENCODING = "utf-8"
```

**想自己跑伺服器**

如果之後我這邊關機、要換你跑：

```powershell
py tools/bridge.py serve --host 0.0.0.0 --port 8791
```

然後告訴我你的 Radmin IP（`26.171.34.199`），我改成連你。
Windows 防火牆若跳出詢問，要選**允許**（`python.exe` 在 Public profile 下已有允許規則，
通常不會跳）。

## 為什麼刻意做得這麼陽春

需求是「雙向、對齊方向、不要複雜、不要死迴圈」。所以：

- **不做自動輪詢** —— 沒有背景 daemon 一直抓，就不會兩個 Agent 自己聊起來
- **不做自動回覆** —— 收到訊息不會觸發任何模型呼叫
- **單一檔案** —— 你那邊不用裝任何東西，也不用同步專案結構
- **純 append-only JSONL** —— 不會因為併發寫入把檔案寫壞

如果之後覺得需要「回合上限」「立場標記」這類結構化討論，再往上加欄位就好，
現在的 `part` / `reply_to` 已經足以串起對話脈絡。