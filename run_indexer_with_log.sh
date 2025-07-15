#!/bin/bash

set -e

echo "📁 Garantindo existência da pasta logs/"
mkdir -p logs/logs_extracao

logfile="logs/logs_extracao/indexer-$(date +%Y-%m-%d_%H-%M-%S).log"
echo "🚀 Rodando indexer com log em $logfile"

# Salva stdout e stderr
docker compose run --rm indexer 2>&1 | tee "$logfile"

echo "✅ Execução concluída. Log salvo em $logfile"
