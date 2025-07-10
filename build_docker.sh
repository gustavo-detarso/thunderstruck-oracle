#!/bin/bash

# Sai do script em caso de erro em qualquer linha
set -e

echo "⏳ Limpando cache e imagens antigas do Docker..."
docker builder prune -af
docker image prune -af

echo "📁 Garantindo existência da pasta logs/"
mkdir -p logs

logfile="logs/build-$(date +%Y-%m-%d_%H-%M-%S).log"
echo "🚀 Iniciando build com log em $logfile"

docker compose build --no-cache | tee "$logfile"

echo "✅ Build concluído. Log salvo em $logfile"
