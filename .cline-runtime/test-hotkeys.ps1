Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class HotKeyProbe {
  [DllImport("user32.dll", SetLastError=true)] public static extern bool RegisterHotKey(IntPtr hWnd, int id, uint modifiers, uint vk);
  [DllImport("user32.dll")] public static extern bool UnregisterHotKey(IntPtr hWnd, int id);
}
'@
$keys = @(@('F1',0x70), @('F6',0x75), @('F7',0x76), @('F8',0x77), @('F9',0x78), @('F10',0x79), @('F11',0x7A))
$id = 12000
foreach ($key in $keys) {
    $ok = [HotKeyProbe]::RegisterHotKey([IntPtr]::Zero, $id, 0x4000, [uint32]$key[1])
    Write-Output ($key[0] + '=' + $(if ($ok) { 'LAISVAS' } else { 'UZIMTAS' }))
    if ($ok) { [HotKeyProbe]::UnregisterHotKey([IntPtr]::Zero, $id) | Out-Null }
    $id++
}
Write-Output '===== WSCRIPT PROCESAI ====='
Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'wscript|cscript' } | Select-Object ProcessId, Name, CommandLine | Format-List
Write-Output '===== F6 KODAS: REGISTRAVIMAS IR PANELIS ====='
Get-Content -LiteralPath 'C:\Users\M\Desktop\pakeitimai 111\_vilkas_global_hotkeys.py' -Encoding UTF8 | Select-Object -Skip 190 -First 180
