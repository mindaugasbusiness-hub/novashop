$ErrorActionPreference = 'Continue'
[Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
$server = '__SERVER__'
$key = '__KEY__'
$headers = @{ Authorization = "Bearer $key" }
$client = "$env:COMPUTERNAME/$env:USERNAME"
Write-Host 'CLINE RYSYS: prisijungta. Palik si langa atidaryta.' -ForegroundColor Green
while ($true) {
    try {
        $job = Invoke-RestMethod -Uri "$server/api/poll" -Method Post -Headers $headers -ContentType 'application/json; charset=utf-8' -Body (@{ client = $client } | ConvertTo-Json -Compress) -TimeoutSec 35
        if ($job.id) {
            $output = ''
            $exitCode = 0
            $tempDir = Join-Path $env:TEMP 'cline-relay'
            New-Item -ItemType Directory -Path $tempDir -Force | Out-Null
            $outFile = Join-Path $tempDir ($job.id + '.out.txt')
            $errFile = Join-Path $tempDir ($job.id + '.err.txt')
            $encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes([string]$job.command))
            $child = Start-Process -FilePath 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe' -ArgumentList @('-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-EncodedCommand',$encoded) -WindowStyle Hidden -RedirectStandardOutput $outFile -RedirectStandardError $errFile -PassThru
            $timedOut = $false
            try {
                Wait-Process -Id $child.Id -Timeout 240 -ErrorAction Stop
            } catch {
                $timedOut = $true
                Stop-Process -Id $child.Id -Force -ErrorAction SilentlyContinue
            }
            $exitCode = if ($timedOut) { 124 } else { [int]$child.ExitCode }
            if (Test-Path -LiteralPath $outFile) { $output += (Get-Content -LiteralPath $outFile -Raw -Encoding UTF8 -ErrorAction SilentlyContinue) }
            if (Test-Path -LiteralPath $errFile) { $errText = Get-Content -LiteralPath $errFile -Raw -Encoding UTF8 -ErrorAction SilentlyContinue; if ($errText) { $output += "`n" + $errText } }
            if ($timedOut) { $output += "`nRELAY_TIMEOUT: komanda virsijo 240 s ir buvo sustabdyta." }
            Remove-Item -LiteralPath $outFile,$errFile -Force -ErrorAction SilentlyContinue
            $body = @{ id = $job.id; output = $output; exit_code = $exitCode } | ConvertTo-Json -Depth 4 -Compress
            Invoke-RestMethod -Uri "$server/api/result" -Method Post -Headers $headers -ContentType 'application/json; charset=utf-8' -Body ([Text.Encoding]::UTF8.GetBytes($body)) -TimeoutSec 60 | Out-Null
        }
    } catch {
        Start-Sleep -Seconds 3
    }
}
