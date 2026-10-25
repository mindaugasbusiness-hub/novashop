$p='C:\Users\M\.cline\data\sessions\1792840477306_ppss1\1792840477306_ppss1.messages.json'
$data=Get-Content -LiteralPath $p -Raw -Encoding UTF8 | ConvertFrom-Json
$data.messages | Select-Object -First 4 | ForEach-Object {
 Write-Output ('MESSAGE role='+$_.role+' items='+$_.content.Count+' ts='+$_.ts)
 $i=0
 foreach($c in $_.content){
  Write-Output ('  item'+$i+' keys='+(($c.PSObject.Properties.Name)-join ','))
  foreach($prop in $c.PSObject.Properties){$v=$prop.Value;if($v -is [string]){$v=$v.Substring(0,[Math]::Min(160,$v.Length))};Write-Output ('    '+$prop.Name+'='+$v)}
  $i++
 }
}
