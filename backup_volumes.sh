#!/bin/bash
DATA=$(date +%Y%m%d-%H%M%S)
tar -czf backup-$DATA.tar.gz db config logs data models
echo "✅ Backup criado: backup-$DATA.tar.gz"
