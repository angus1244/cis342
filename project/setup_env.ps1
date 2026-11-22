# ==== CIS342 Group 6 — 一鍵建立本機執行環境 ====
#
# 用途：在全新的機器上（例如 presentation 當天的電腦）把專案跑起來。
#      不需要上傳 venv，也不需要 Google Colab。
#
# 用法（在 project 目錄下開 PowerShell）：
#   .\setup_env.ps1
#
# 參數：
#   -PythonExe  <路徑>   指定 python.exe（預設自動找 py -3.12 / python）
#   -VenvDir    <目錄>   venv 放哪裡（預設 .venv）
#   -SkipKernel          不註冊 Jupyter kernel
#   -Check               只做「環境是否已就緒」檢查，不安裝

[CmdletBinding()]
param(
    [string]$PythonExe = '',
    [string]$VenvDir   = '.venv',
    [switch]$SkipKernel,
    [switch]$Check
)

$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $here

$reqFile  = Join-Path $here 'requirements.txt'
$venvPath = Join-Path $here $VenvDir
$venvPy   = Join-Path $venvPath 'Scripts\python.exe'
$kernel   = 'cis342'

function Write-Step($msg) { Write-Host "`n=== $msg ===" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "  [OK] $msg" -ForegroundColor Green }
function Write-Bad($msg)  { Write-Host "  [!!] $msg" -ForegroundColor Red }

if (-not (Test-Path $reqFile)) { throw "找不到 requirements.txt：$reqFile" }

# ---- 1. 決定 Python ----
if ($Check) {
    if (-not (Test-Path $venvPy)) { Write-Bad "尚未建立 venv：$venvPath"; exit 1 }
} else {
    Write-Step '1/5 選擇 Python 直譯器'
    if (-not $PythonExe) {
        foreach ($cand in @('py -3.12', 'py -3', 'python')) {
            $parts = $cand.Split(' ')
            $exe = $parts[0]
            if (-not (Get-Command $exe -ErrorAction SilentlyContinue)) { continue }
            try {
                $v = & $exe $parts[1..($parts.Length - 1)] -c "import sys;print('%d.%d'%sys.version_info[:2])" 2>$null
                if ($v -eq '3.12') { $PythonExe = $cand; break }
                if (-not $PythonExe) { $PythonExe = $cand }
            } catch { }
        }
    }
    if (-not $PythonExe) { throw '找不到 Python。請先安裝 Python 3.12，或用 -PythonExe 指定路徑。' }
    $ver = & (($PythonExe.Split(' '))[0]) @($PythonExe.Split(' ')[1..($PythonExe.Split(' ').Length - 1)] | Where-Object { $_ }) -c "import sys;print(sys.version.split()[0])"
    Write-Ok "使用 $PythonExe（Python $ver）"
    if ($ver -notlike '3.12.*') {
        Write-Host "  [注意] 本專案在 3.12.10 上驗證；$ver 未經測試，可能仍需微調。" -ForegroundColor Yellow
    }

    # ---- 2. 建立 venv ----
    Write-Step "2/5 建立虛擬環境 $VenvDir"
    if (Test-Path $venvPy) {
        Write-Ok 'venv 已存在，沿用（不重建）'
    } else {
        & (($PythonExe.Split(' '))[0]) @($PythonExe.Split(' ')[1..($PythonExe.Split(' ').Length - 1)] | Where-Object { $_ }) -m venv $venvPath
        if (-not (Test-Path $venvPy)) { throw 'venv 建立失敗' }
        Write-Ok 'venv 已建立'
    }

    # ---- 3. 安裝套件 ----
    Write-Step '3/5 安裝 requirements.txt（第一次約 10-15 分鐘，會下載約 700 MB）'
    & $venvPy -m pip install --upgrade pip --quiet
    & $venvPy -m pip install -r $reqFile
    if ($LASTEXITCODE -ne 0) { throw 'pip install 失敗，請看上方訊息' }
    Write-Ok '套件安裝完成'

    # ---- 4. 註冊 Jupyter kernel ----
    if (-not $SkipKernel) {
        Write-Step "4/5 註冊 Jupyter kernel '$kernel'"
        & $venvPy -m ipykernel install --user --name $kernel --display-name "Python (CIS342 LPR)" | Out-Null
        Write-Ok "kernel '$kernel' 已註冊，notebook 請選這個 kernel"
    }
}

# ---- 5. 驗證 ----
Write-Step '5/5 驗證環境'
$env:PYTHONIOENCODING = 'utf-8'
$verifyScript = @'
import sys
fail = []

def expect(mod, want=None, mode="eq", label=None):
    name = label or mod
    try:
        m = __import__(mod)
    except Exception as e:
        print(f"  BAD {name:12s} 匯入失敗：{e}")
        fail.append(f"{name}: {e}")
        return
    got = str(getattr(m, "__version__", "?"))
    if mode == "any":
        ok = True
    elif mode == "prefix":
        ok = got.startswith(want)
    else:
        ok = got == want
    note = "" if ok else f"（期望 {want}）"
    print(("  OK  " if ok else "  BAD ") + f"{name:12s} {got}{note}")
    if not ok:
        fail.append(f"{name}: 期望 {want}，實際 {got}")

expect("numpy", "2.5.5")
expect("cv2", "5.0", mode="prefix")
expect("pandas", "3.1.1")
expect("PIL", "13.0.0")
expect("matplotlib", "3.11.2")
expect("torch", mode="any")
expect("easyocr", mode="any")

print()
if fail:
    print("驗證失敗：")
    for f in fail:
        print("  -", f)
    sys.exit(1)
print("環境驗證通過。")
'@
$verifyScript | & $venvPy -
$code = $LASTEXITCODE

Write-Host ''
if ($code -eq 0) {
    Write-Host '完成。執行 notebook：' -ForegroundColor Green
    Write-Host "  $venvPath\Scripts\python.exe -m jupyter lab notebooks\lpr_dev.ipynb"
    Write-Host '或用 VS Code 開啟 notebook，kernel 選 "Python (CIS342 LPR)"。'
} else {
    Write-Bad '驗證未通過，請檢查上面的項目。'
    exit 1
}