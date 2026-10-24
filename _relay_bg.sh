#!/bin/bash
# Paleidzia komanda M PC fone, rezultata raso i /workspace/_out/<name>.txt
NAME="$1"; FILE="$2"
mkdir -p /workspace/_out
nohup /workspace/_relay_cmd.sh -f "$FILE" > "/workspace/_out/$NAME.txt" 2>&1 &
echo "started $NAME (pid $!)"
