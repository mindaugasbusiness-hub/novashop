$ErrorActionPreference = 'Continue'
$base = 'http://127.0.0.1:5678'
$sess = Import-Clixml 'C:\Users\M\CLINE\tools\_n8n_sess.xml'
$paths = @('/rest/settings','/rest/workflows','/rest/active-workflows','/rest/node-types','/types/nodes.json','/rest/me','/rest/credentials','/rest/projects')
foreach ($p in $paths) {
  try {
    $r = Invoke-WebRequest -Uri ($base + $p) -WebSession $sess -UseBasicParsing -TimeoutSec 20
    $len = $r.Content.Length
    $short = $r.Content.Substring(0, [Math]::Min(120, $len))
    "$p -> " + $r.StatusCode + ' | ' + $len + ' B | ' + $short.Replace("`n", ' ')
  } catch {
    "$p -> KLAIDA " + $(if ($_.Exception.Response) { [int]$_.Exception.Response.StatusCode } else { $_.Exception.Message })
  }
}
