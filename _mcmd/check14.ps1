$ErrorActionPreference = 'Continue'
'=== disabled-nodes.rule.js ==='
Get-Content 'C:\Users\M\Desktop\Kumstis\runtime\n8n\node_modules\n8n\dist\modules\breaking-changes\rules\v2\disabled-nodes.rule.js' -ErrorAction SilentlyContinue | Select-Object -First 60
'=== n8n-nodes-base versija ==='
(Get-Content 'C:\Users\M\Desktop\Kumstis\runtime\n8n\node_modules\n8n-nodes-base\package.json' -Raw | ConvertFrom-Json).version
'=== n8n versija ==='
(Get-Content 'C:\Users\M\Desktop\Kumstis\runtime\n8n\node_modules\n8n\package.json' -Raw | ConvertFrom-Json).version
'=== ExecuteCommand node versija ==='
Select-String -Path 'C:\Users\M\Desktop\Kumstis\runtime\n8n\node_modules\n8n-nodes-base\dist\nodes\ExecuteCommand\ExecuteCommand.node.js' -Pattern 'version' -ErrorAction SilentlyContinue | Select-Object -First 3 | ForEach-Object { $_.Line.Trim().Substring(0,[Math]::Min(120,$_.Line.Trim().Length)) }
