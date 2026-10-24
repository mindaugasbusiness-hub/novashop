mkpush() {
  local src="$1" dst="$2" name="$3"
  local b64=$(base64 -w0 "$src")
  {
    echo '$ErrorActionPreference = "Continue"'
    echo "\$b64 = '$b64'"
    echo "New-Item -ItemType Directory -Force -Path (Split-Path -Parent '$dst') | Out-Null"
    echo "[IO.File]::WriteAllBytes('$dst', [Convert]::FromBase64String(\$b64))"
    echo "'IRASYTA: $dst | ' + (Get-Item '$dst').Length + ' B'"
    echo "'SHA256: ' + (Get-FileHash '$dst' -Algorithm SHA256).Hash"
  } > "_mcmd/push-$name.ps1"
}
mkpush "$1" "$2" "$3"
