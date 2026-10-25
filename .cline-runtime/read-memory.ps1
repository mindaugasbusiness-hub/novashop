$files = @(
    'C:\Users\M\CLINE\00_START_HERE.md',
    'C:\Users\M\CLINE\02_DIENORASTIS.md',
    'C:\Users\M\CLINE\04_TODO.md'
)
foreach ($file in $files) {
    Write-Output "`n===== $file ====="
    if (Test-Path -LiteralPath $file) {
        Get-Content -LiteralPath $file -Raw -Encoding UTF8
    } else {
        Write-Output 'FAILAS_NERASTAS'
    }
}
