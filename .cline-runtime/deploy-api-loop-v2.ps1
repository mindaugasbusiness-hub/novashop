$ErrorActionPreference='Stop'
$target='C:\Users\M\CLINE\tools\automation-server-loop.ps1'
$stamp=Get-Date -Format 'yyyy-MM-dd_HHmmss'
$bak="C:\Users\M\CLINE\BACKUPS\$stamp\CLINE\tools"
New-Item -ItemType Directory -Path $bak -Force|Out-Null
Copy-Item -LiteralPath $target -Destination (Join-Path $bak 'automation-server-loop.ps1')
[IO.File]::WriteAllBytes($target,[Convert]::FromBase64String('JHB5dGhvbj0nQzpcVXNlcnNcTVxBcHBEYXRhXExvY2FsXFByb2dyYW1zXFB5dGhvblxQeXRob24zMTJccHl0aG9uLmV4ZScKJHNlcnZlcj0nQzpcVXNlcnNcTVxDTElORVx0b29sc1xhdXRvbWF0aW9uX3NlcnZlci5weScKJGxvZz0nQzpcVXNlcnNcTVxDTElORVxBVVRPTUFUSU9OX0FQSV9TVERPVVQubG9nJwpBZGQtQ29udGVudCAtTGl0ZXJhbFBhdGggJGxvZyAtVmFsdWUgKCdbezB9XSBMT09QX0VOVEVSIHBpZD17MX0nIC1mIChHZXQtRGF0ZSAtRm9ybWF0ICd5eXl5LU1NLWRkIEhIOm1tOnNzJyksICRQSUQpIC1FbmNvZGluZyBVVEY4CiRjcmVhdGVkTmV3PSRmYWxzZQokbXV0ZXg9TmV3LU9iamVjdCBTeXN0ZW0uVGhyZWFkaW5nLk11dGV4KCR0cnVlLCdMb2NhbFxDbGluZUF1dG9tYXRpb25BcGknLCRjcmVhdGVkTmV3KQppZigtbm90ICRjcmVhdGVkTmV3KXskbXV0ZXguRGlzcG9zZSgpO2V4aXQgMH0Kd2hpbGUgKCR0cnVlKSB7CiAgICAkbGlzdGVuaW5nID0gR2V0LU5ldFRDUENvbm5lY3Rpb24gLUxvY2FsUG9ydCA4NzkyIC1TdGF0ZSBMaXN0ZW4gLUVycm9yQWN0aW9uIFNpbGVudGx5Q29udGludWUKICAgIGlmICgtbm90ICRsaXN0ZW5pbmcpIHsKICAgICAgICBBZGQtQ29udGVudCAtTGl0ZXJhbFBhdGggJGxvZyAtVmFsdWUgKCdbezB9XSBMT09QX1NUQVJUX1NFUlZFUicgLWYgKEdldC1EYXRlIC1Gb3JtYXQgJ3l5eXktTU0tZGQgSEg6bW06c3MnKSkgLUVuY29kaW5nIFVURjgKICAgICAgICB0cnkgewogICAgICAgICAgICAmICRweXRob24gLVggdXRmOCAkc2VydmVyIDI+JjEgfCBBZGQtQ29udGVudCAtTGl0ZXJhbFBhdGggJGxvZyAtRW5jb2RpbmcgVVRGOAogICAgICAgIH0gY2F0Y2ggewogICAgICAgICAgICBBZGQtQ29udGVudCAtTGl0ZXJhbFBhdGggJGxvZyAtVmFsdWUgKCdbezB9XSBMT09QX0VSUk9SIHsxfScgLWYgKEdldC1EYXRlIC1Gb3JtYXQgJ3l5eXktTU0tZGQgSEg6bW06c3MnKSwgJF8uRXhjZXB0aW9uLk1lc3NhZ2UpIC1FbmNvZGluZyBVVEY4CiAgICAgICAgfQogICAgfQogICAgU3RhcnQtU2xlZXAgLVNlY29uZHMgNQp9Cg=='))
$errs=$null
[void][System.Management.Automation.Language.Parser]::ParseFile($target,[ref]$null,[ref]$errs)
Write-Output ('PARSE_ERRORS='+(($errs|Measure-Object).Count))
Start-Process -FilePath 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe' -ArgumentList @('-NoProfile','-WindowStyle','Hidden','-ExecutionPolicy','Bypass','-File',$target) -WindowStyle Hidden
$ok=$false;for($i=0;$i -lt 40;$i++){Start-Sleep -Milliseconds 500;try{$h=Invoke-WebRequest 'http://127.0.0.1:8792/health' -UseBasicParsing -TimeoutSec 2;if($h.StatusCode -eq 200){$ok=$true;break}}catch{}}
Write-Output ('HEALTH_OK='+$ok)
if(-not $ok){Get-Content -LiteralPath 'C:\Users\M\CLINE\AUTOMATION_API_STDOUT.log' -Encoding UTF8 -Tail 20;throw 'Serveris nepaleistas'}
$token=(Get-Content -LiteralPath 'C:\Users\M\CLINE\tools\automation-secret.txt' -Raw).Trim()
foreach($action in @('ensure','collect','collect')){
 $r=& curl.exe -sS --max-time 45 -X POST -H "X-Automation-Key: $token" -w "|HTTP=%{http_code}|T=%{time_total}" ('http://127.0.0.1:8792/'+$action) 2>&1 | Out-String
 Write-Output ($action+' => '+($r.Trim()))
}
Write-Output '===== API LOG ====='
Get-Content -LiteralPath 'C:\Users\M\CLINE\AUTOMATION_API_LOG.txt' -Encoding UTF8 -Tail 8
Get-NetTCPConnection -LocalPort 8792 -State Listen -ErrorAction SilentlyContinue|Select-Object LocalPort,OwningProcess|Format-Table -AutoSize
