#!/bin/bash

set -e

echo "📁 Garantindo existência da pasta logs/"
mkdir -p logs

logfile="logs/app-$(date +%Y-%m-%d_%H-%M-%S).log"
echo "🚀 Subindo o app com log em $logfile"

docker compose up 2>&1 | tee "$logfile"

echo "✅ Execução concluída. Log salvo em $logfile"
