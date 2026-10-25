$ssh='C:\Windows\System32\OpenSSH\ssh.exe'
$key='C:\Users\M\CLINE\ssh\vps_cline'
$known='C:\Users\M\CLINE\ssh\known_hosts'
$remote=@'
echo '===== VPS SERVISAI ====='
hostname
systemctl is-active aukcionas vilko-mokykla cloudflared-penktadienio vilkas-tts
echo '===== ADMIN SLAPTAZODIS ====='
if grep -q '^Environment=AUKCIONAS_ADMIN_SLAPTAZODIS=' /etc/systemd/system/aukcionas.service; then echo 'service_plaintext=BLOGAI'; else echo 'service_plaintext=OK_NERA'; fi
if grep -q '^AUKCIONAS_ADMIN_SLAPTAZODIS=' /opt/aukcionas/.env; then echo 'env_admin=YRA'; else echo 'env_admin=NERA'; fi
grep -q '^EnvironmentFile=/opt/aukcionas/.env' /etc/systemd/system/aukcionas.service && echo 'EnvironmentFile=YRA'
echo '===== VPS KOPIJOS ====='
for f in /etc/systemd/system/aukcionas.service.bak-2026-10-25-cline /root/aukcionas.service.bak-2026-10-25-cline /opt/aukcionas/app.py.bak-pplist-2026-10-25 /opt/aukcionas/app.py.bak-panel-2026-10-25 /opt/aukcionas/vps-watchdog.sh.bak-2026-10-25-cline /opt/vps-watchdog.sh.bak-2026-10-25-cline; do if [ -f "$f" ]; then stat -c '%n|%s|%y' "$f"; else echo "$f NERA"; fi; done
echo '===== DAINOS IR SOKEJOS ====='
stat -c '%n|%s|%y' /opt/aukcionas/desk_songs/12.webm /opt/aukcionas/desk_songs/32.webm 2>&1
printf 'dance_files='; find /opt/aukcionas/photos -maxdepth 1 -type f -name 'dance_club_*.mp4' | wc -l
echo '===== APP PATIKRA ====='
grep -nE 'pplist|participant|dalyvi|Dalyvi|UŽSIREGISTRAVĘ|UZSIREGISTRAVE|184px|184 px|bottom: ?8px' /opt/aukcionas/app.py | tail -n 50
'@
& $ssh -i $key -o "UserKnownHostsFile=$known" -o StrictHostKeyChecking=yes -o BatchMode=yes -o ConnectTimeout=12 root@5.175.171.113 $remote 2>&1 | Out-String -Width 3000
Write-Output ('SSH_EXIT='+$LASTEXITCODE)
