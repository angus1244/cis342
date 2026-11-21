# 設定 .ipynb 的 strip-outputs filter（每個 clone 只需跑一次）
#
# 為什麼要這個：notebook 的 base64 圖片輸出每次執行都不同，就算程式沒改，
# 一執行整份 diff 都會變。設了這個 filter 之後，進 git 的版本永遠沒有輸出，
# PR 的 diff 就只剩真正改動的程式碼。本機檔案仍然保留輸出。
#
# 用法：在 repo 根目錄執行  pwsh -NoProfile -File tools/setup_nb_filter.ps1

$ErrorActionPreference = 'Stop'

$root = git rev-parse --show-toplevel
if (-not $root) { throw '不在 git repo 內' }
Set-Location $root

# 找 python：優先用專案的 venv，其次用系統的
$py = if (Test-Path 'project/.venv/Scripts/python.exe') {
    'project/.venv/Scripts/python.exe'
} elseif (Test-Path '.venv/Scripts/python.exe') {
    '.venv/Scripts/python.exe'
} else {
    'python'
}

$script = 'project/tools/strip_nb_outputs.py'
if (-not (Test-Path $script)) { $script = 'tools/strip_nb_outputs.py' }
if (-not (Test-Path $script)) { throw "找不到 strip_nb_outputs.py" }

git config --local filter.stripoutput.clean "$py $script --stdin"
git config --local filter.stripoutput.smudge 'cat'
git config --local filter.stripoutput.required true

Write-Host "已設定 filter.stripoutput："
git config --local --get-regexp 'filter\.stripoutput'

# 讓 .gitattributes 生效並重新整理已追蹤的 notebook
git add --renormalize .
Write-Host ''
Write-Host "若要立即套用到所有已追蹤檔案，執行：git add --renormalize . && git commit -m 'chore: strip notebook outputs'"