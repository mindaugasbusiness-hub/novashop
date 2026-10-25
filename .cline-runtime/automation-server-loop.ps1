$python='C:\Users\M\AppData\Local\Programs\Python\Python312\python.exe'
$server='C:\Users\M\CLINE\tools\automation_server.py'
$log='C:\Users\M\CLINE\AUTOMATION_API_STDOUT.log'
function Test-Port([int]$Port) {
    try {
        $client = New-Object Net.Sockets.TcpClient
        $client.Connect('127.0.0.1', $Port)
        $client.Close()
        return $true
    } catch { return $false }
}
function Log([string]$Message) {
    Add-Content -LiteralPath $log -Value ('[{0}] {1}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Message) -Encoding UTF8
}
Log ('LOOP_ENTER pid=' + $PID)
while ($true) {
    if (-not (Test-Port 8792)) {
        Log 'LOOP_START_SERVER'
        try {
            & $python -X utf8 $server 2>&1 | Add-Content -LiteralPath $log -Encoding UTF8
        } catch {
            Log ('LOOP_ERROR ' + $_.Exception.Message)
        }
        Log 'LOOP_SERVER_EXITED'
    }
    Start-Sleep -Seconds 5
}
