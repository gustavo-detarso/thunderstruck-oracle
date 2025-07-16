#!/bin/bash

set -e

echo "⏳ Limpando cache e imagens antigas do Docker..."
docker builder prune -af
docker image prune -af

echo "📁 Garantindo existência da pasta logs/logs_build/"
mkdir -p logs/logs_build

logfile="logs/logs_build/build-$(date +%Y-%m-%d_%H-%M-%S).log"
echo "🚀 Iniciando build com log em $logfile"

docker compose build --no-cache | tee "$logfile"

echo "✅ Build concluído. Log salvo em $logfile"

