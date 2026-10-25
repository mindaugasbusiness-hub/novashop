Write-Output '===== START-NATIVE N8N ENV ====='
Select-String -LiteralPath 'C:\Users\M\Desktop\Kumstis\start-native.ps1' -Pattern 'N8N_USER_FOLDER|N8N_ENCRYPTION|N8N_RUNNERS|Start-Hidden' -Context 2,4 | Format-List
Write-Output '===== N8N.DATA TURINYS ====='
Get-ChildItem -LiteralPath 'C:\Users\M\Desktop\Kumstis\runtime\n8n-data' -Force | Select-Object Mode,Name,LastWriteTime | Format-Table -AutoSize
Get-ChildItem -LiteralPath 'C:\Users\M\Desktop\Kumstis\runtime\n8n-data\.n8n' -Force -ErrorAction SilentlyContinue | Select-Object Mode,Name,LastWriteTime | Format-Table -AutoSize
Write-Output '===== SESIJOS STRUKTURA ====='
$p='C:\Users\M\.cline\data\sessions\1792840477306_ppss1\1792840477306_ppss1.messages.json'
$data=Get-Content -LiteralPath $p -Raw -Encoding UTF8 | ConvertFrom-Json
Write-Output ('TOP_TYPE='+$data.GetType().FullName)
if($data -is [array]){Write-Output ('COUNT='+$data.Count);$sample=$data[0]}else{Write-Output ('TOP_KEYS='+(($data.PSObject.Properties.Name)-join ','));$sample=$data.messages[0]}
Write-Output ('SAMPLE_KEYS='+(($sample.PSObject.Properties.Name)-join ','))
foreach($prop in $sample.PSObject.Properties){Write-Output ($prop.Name+'|'+$prop.TypeNameOfValue+'|'+$(if($prop.Value -is [string]){'len='+$prop.Value.Length}else{''}))}
Write-Output '===== META FAILAS ====='
Get-Content -LiteralPath 'C:\Users\M\.cline\data\sessions\1792840477306_ppss1\1792840477306_ppss1.json' -Raw -Encoding UTF8
