Write-Output '===== PAGRINDINIS PUSLAPIS ====='
& curl.exe -sS -o NUL -w 'root_http=%{http_code} bytes=%{size_download}\n' --max-time 10 'http://127.0.0.1:8091/'
Write-Output '===== TURINYS ====='
$r=Invoke-WebRequest -Uri 'http://127.0.0.1:8091/' -UseBasicParsing -TimeoutSec 10
Write-Output ('title=' + ($r.Content -match '<title>Žvėris Kareivis</title>'))
Write-Output ('chat_api=' + ($r.Content -match "'/api/chat'"))
Write-Output ('status_api=' + ($r.Content -match "'/api/status'"))
Write-Output '===== API ====='
& curl.exe -sS -o NUL -w 'status_http=%{http_code}\n' --max-time 12 'http://127.0.0.1:8091/api/status'
& curl.exe -sS -o NUL -w 'memory_http=%{http_code}\n' --max-time 12 'http://127.0.0.1:8091/api/memory/chat'
