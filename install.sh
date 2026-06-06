#!/bin/bash
# Script de instalação local - BROKER 10 API SERVER

echo "═══════════════════════════════════════════════════════"
echo "  INSTALADOR - BROKER 10 API SERVER (TRADER CRISTÃO)"
echo "═══════════════════════════════════════════════════════"

# Verificar Python
python3 --version || { echo "❌ Python3 não encontrado! Instale primeiro."; exit 1; }

# Criar ambiente virtual
echo "📦 Criando ambiente virtual..."
python3 -m venv venv
source venv/bin/activate

# Instalar dependências
echo "📦 Instalando dependências..."
pip install -r requirements.txt

# Criar pasta broker10api se não existir
if [ ! -d "broker10api" ]; then
    echo "⚠️  Pasta broker10api não encontrada!"
    echo "   Coloque os arquivos da API da Broker 10 nesta pasta:"
    echo "   - __init__.py"
    echo "   - api.py"
    echo "   - stable_api.py"
    echo "   - constants.py"
    echo "   - global_value.py"
    echo "   - expiration.py"
    echo "   - ws/ (pasta com os handlers WebSocket)"
    exit 1
fi

echo ""
echo "✅ Instalação completa!"
echo ""
echo "Para iniciar o servidor local:"
echo "  source venv/bin/activate"
echo "  python broker10_server.py"
echo ""
echo "O servidor vai rodar em: http://localhost:5000"
echo ""
