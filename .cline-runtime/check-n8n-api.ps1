Write-Output '===== N8N API ====='
foreach($url in @('http://127.0.0.1:5678/api/v1/workflows','http://127.0.0.1:5678/rest/workflows')){
 try{$r=Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 8;Write-Output ($url+'|'+$r.StatusCode+'|'+$r.Content.Substring(0,[Math]::Min(500,$r.Content.Length)))}catch{Write-Output ($url+'|'+$_.Exception.Message)}
}
Write-Output '===== N8N CLI ====='
& 'C:\Users\M\Desktop\Kumstis\runtime\node24\node.exe' 'C:\Users\M\Desktop\Kumstis\runtime\n8n\node_modules\n8n\bin\n8n' --help 2>&1 | Select-Object -First 80 | Out-String -Width 2000
Write-Output '===== ZVERIS START BUDELAS ====='
Select-String -Path 'C:\Users\M\CLINE\tools\*.ps1','C:\Users\M\Desktop\Kumstis\*.ps1' -Pattern 'ui_app:app|8091' -Context 3,5 -ErrorAction SilentlyContinue | Select-Object -First 10 | Format-List
