$file='C:\Users\M\Desktop\pakeitimai 111\_zveris_watch\ui_app.py'
Write-Output '===== VISI ENDPOINTAI ====='
Select-String -LiteralPath $file -Pattern '^@app\.(get|post|delete|put)' -Context 0,12 | ForEach-Object { $_.Line; $_.Context.PostContext; '---' }
Write-Output '===== CHAT KODAS ====='
$lines=Get-Content -LiteralPath $file -Encoding UTF8
$chat=Select-String -LiteralPath $file -Pattern '^@app.post\("/api/chat"'
if($chat){$start=[Math]::Max(0,$chat.LineNumber-5);$lines|Select-Object -Skip $start -First 150}
