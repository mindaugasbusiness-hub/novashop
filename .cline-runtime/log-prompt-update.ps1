$root='C:\Users\M\CLINE';$v=Join-Path $root 'VISKAS';$stamp=Get-Date -Format 'yyyy-MM-dd_HHmmss';$bak=Join-Path $root "BACKUPS\$stamp\CLINE";$bakv=Join-Path $bak 'VISKAS'
New-Item -ItemType Directory -Path $bakv -Force|Out-Null
foreach($n in @('02_DIENORASTIS.md','04_TODO.md','09_PAKEITIMAI.md')){Copy-Item -LiteralPath (Join-Path $root $n) -Destination (Join-Path $bak $n)}
foreach($n in @('02_ATLIKTI_DARBAI.md','VISKAS_VISKAS.md')){Copy-Item -LiteralPath (Join-Path $v $n) -Destination (Join-Path $bakv $n)}
function Add-AfterTitle([string]$path,[string]$entry){$t=[IO.File]::ReadAllText($path);$i=$t.IndexOf("`n");if($i -lt 0){throw "Blogas formatas: $path"};[IO.File]::WriteAllText($path,$t.Insert($i+1,"`r`n"+$entry+"`r`n"),[Text.UTF8Encoding]::new($false))}
$entry=@'
## 2026-10-25 13:48 — nauja DI nuoroda
- `VISKAS\DUOK_NAUJAM_AI.txt` dabar nurodo `00_SKAITYK_NAUJAUSIA.md`.
- `CLINE NUORODA` naudojamas `NUKOPIJUOTI NUORODA.ps1` taip pat nukopijuoja naują kelią.
- Naujam DI: `Perskaityk C:\Users\M\CLINE\VISKAS\00_SKAITYK_NAUJAUSIA.md ir tesiam.`
- Originalios nuorodos kopija: `BACKUPS\2026-10-25_134836`.
'@
Add-AfterTitle (Join-Path $root '09_PAKEITIMAI.md') $entry
Add-AfterTitle (Join-Path $root '02_DIENORASTIS.md') $entry
Add-AfterTitle (Join-Path $v '02_ATLIKTI_DARBAI.md') $entry
Add-AfterTitle (Join-Path $v 'VISKAS_VISKAS.md') $entry
& 'C:\Users\M\AppData\Local\Programs\Python\Python312\python.exe' -X utf8 'C:\Users\M\CLINE\tools\surinkti-viska.py' 2>&1 | Out-String -Width 2000
Write-Output ('COLLECT_EXIT='+$LASTEXITCODE)
