$root = 'C:\Users\M\CLINE'
$stamp = Get-Date -Format 'yyyy-MM-dd_HHmmss'
$backupDir = Join-Path $root "BACKUPS\$stamp\CLINE"
New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
$files = @('02_DIENORASTIS.md', '04_TODO.md', '09_PAKEITIMAI.md')
foreach ($name in $files) { Copy-Item -LiteralPath (Join-Path $root $name) -Destination (Join-Path $backupDir $name) }
function Add-AfterTitle([string]$path, [string]$entry) {
    $text = [IO.File]::ReadAllText($path)
    $pos = $text.IndexOf("`n")
    if ($pos -lt 0) { throw "Netiketas failo formatas: $path" }
    $updated = $text.Insert($pos + 1, "`r`n" + $entry + "`r`n")
    [IO.File]::WriteAllText($path, $updated, [Text.UTF8Encoding]::new($false))
}
$changeEntry = @'
## 2026-10-25 — F6 paleidimo pataisymas
- Failas: `Desktop\pakeitimai 111\_vilkas_global_hotkeys.py`.
- Priežastis: kitas procesas užėmė F1, o sena logika dėl to sustabdydavo ir laisvus F6–F11.
- Pakeitimas: F1 konfliktas nebeblokuoja F6–F11; F1 savininkas nekeistas ir neuždarytas.
- Patikra: `py_compile` OK; F6 panelis `http://127.0.0.1:8766/` = HTTP 200; procesas PID 2256 gyvas.
- Originalo kopija: `C:\Users\M\CLINE\BACKUPS\2026-10-25_125157\Desktop\pakeitimai 111\_vilkas_global_hotkeys.py`.
'@
$diaryEntry = @'
## 2026-10-25 — nauja Cline sesija
- Prisijungta per naują relay; perskaityti 00–04 ir sesijos pradžios ataskaita.
- Rasta ir pataisyta F6 klaida: F1 buvo užimtas kito proceso, todėl nepasidarydavo F6–F11 ir :8766.
- F6 panelis dabar HTTP 200, F6–F11 veikia; F1 paliktas esamam procesui. Kopija BACKUPS\2026-10-25_125157.
'@
$todoEntry = @'
## 2026-10-25 — šios sesijos būsena
- [x] F6 panelis :8766 atstatytas ir patikrintas (HTTP 200); F6–F11 nebeblokuojami dėl kito proceso F1.
- [ ] Jei M nori F1 perimti atgal — pirmiausia identifikuoti jo dabartinį savininką; nieko neuždaryti be patikros.
'@
Add-AfterTitle (Join-Path $root '09_PAKEITIMAI.md') $changeEntry
Add-AfterTitle (Join-Path $root '02_DIENORASTIS.md') $diaryEntry
Add-AfterTitle (Join-Path $root '04_TODO.md') $todoEntry
Write-Output ('MEMORY_BACKUP=' + $backupDir)
& 'C:\Users\M\CLINE\VISKAS\viskas-atnaujinti.ps1'
Write-Output '===== NAUJA BŪSENA ====='
Get-Content -LiteralPath 'C:\Users\M\CLINE\VISKAS\06_DABARTINE_BUSENA.md' -Encoding UTF8 -TotalCount 22
Write-Output '===== ATMINTIES IRASAI ====='
Get-Content -LiteralPath (Join-Path $root '09_PAKEITIMAI.md') -Encoding UTF8 -TotalCount 12
