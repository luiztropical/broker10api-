
"""
═══════════════════════════════════════════════════════════════════════════════
  BROKER 10 API SERVER - TRADER CRISTÃO
  Servidor REST que conecta na Broker 10 e expõe dados para seu aplicativo web
  Hospedar no Render.com (gratuito) ou Railway.app
═══════════════════════════════════════════════════════════════════════════════
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import time
import json
import threading
from datetime import datetime

# Importa a API da Broker 10 (os arquivos que você enviou)
# Na hospedagem, você precisa ter esses arquivos instalados como pacote
# Ou usar: pip install broker10api (se estiver no PyPI)
# Por enquanto, vou assumir que os arquivos estão no mesmo diretório

import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from broker10api.stable_api import Broker10_Api
    import broker10api.constants as OP_code
    import broker10api.global_value as global_value
except ImportError:
    print("AVISO: broker10api não encontrado. Usando modo simulação.")
    Broker10_Api = None

app = Flask(__name__)
CORS(app)  # Permite chamadas de qualquer origem (seu aplicativo web)

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURAÇÕES
# ═══════════════════════════════════════════════════════════════════════════════

# Pegar do ambiente (Render.com) ou usar padrão
BROKER_EMAIL = os.environ.get("BROKER_EMAIL", "seu_email@exemplo.com")
BROKER_PASSWORD = os.environ.get("BROKER_PASSWORD", "sua_senha")
API_PORT = int(os.environ.get("PORT", 5000))

# ═══════════════════════════════════════════════════════════════════════════════
# ESTADO GLOBAL
# ═══════════════════════════════════════════════════════════════════════════════

api_instance = None
connection_status = {
    "connected": False,
    "last_check": None,
    "error": None,
    "profile": None,
    "balance": None,
    "currency": None,
    "mode": "PRACTICE"
}

# Cache de dados
cache = {
    "candles": {},
    "payouts": {},
    "actives": {},
    "last_update": 0
}

# Lock para operações thread-safe
api_lock = threading.Lock()

# ═══════════════════════════════════════════════════════════════════════════════
# FUNÇÕES DE CONEXÃO
# ═══════════════════════════════════════════════════════════════════════════════

def connect_broker():
    """Conecta na Broker 10"""
    global api_instance, connection_status

    if Broker10_Api is None:
        connection_status["error"] = "API broker10api não instalada"
        return False

    try:
        print(f"[{datetime.now()}] Conectando na Broker 10...")
        api_instance = Broker10_Api(BROKER_EMAIL, BROKER_PASSWORD)
        ok, reason = api_instance.connect()

        if ok:
            connection_status["connected"] = True
            connection_status["error"] = None
            connection_status["last_check"] = time.time()

            # Pega informações do perfil
            try:
                profile = api_instance.get_profile()
                connection_status["profile"] = profile
            except:
                pass

            # Pega saldo
            try:
                balance = api_instance.get_balance()
                connection_status["balance"] = balance
            except:
                pass

            # Pega moeda
            try:
                currency = api_instance.get_currency()
                connection_status["currency"] = currency
            except:
                pass

            # Pega modo
            try:
                mode = api_instance.get_balance_mode()
                connection_status["mode"] = mode
            except:
                pass

            print(f"[{datetime.now()}] ✅ Conectado! Saldo: {connection_status['balance']} {connection_status['currency']}")
            return True
        else:
            connection_status["connected"] = False
            connection_status["error"] = str(reason)
            print(f"[{datetime.now()}] ❌ Erro: {reason}")
            return False

    except Exception as e:
        connection_status["connected"] = False
        connection_status["error"] = str(e)
        print(f"[{datetime.now()}] ❌ Exceção: {e}")
        return False

def ensure_connection():
    """Garante que está conectado"""
    if not connection_status["connected"] or api_instance is None:
        return connect_broker()
    return True

# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS DA API
# ═══════════════════════════════════════════════════════════════════════════════

@app.route("/")
def home():
    """Página inicial - status"""
    return jsonify({
        "status": "online",
        "service": "Broker 10 API Server - TRADER CRISTÃO",
        "version": "1.0",
        "connected": connection_status["connected"],
        "timestamp": datetime.now().isoformat()
    })

@app.route("/status")
def status():
    """Status da conexão"""
    return jsonify({
        "connected": connection_status["connected"],
        "balance": connection_status["balance"],
        "currency": connection_status["currency"],
        "mode": connection_status["mode"],
        "error": connection_status["error"],
        "last_check": connection_status["last_check"]
    })

@app.route("/connect", methods=["POST"])
def api_connect():
    """Força reconexão"""
    data = request.get_json() or {}

    # Permite sobrescrever credenciais via request
    email = data.get("email", BROKER_EMAIL)
    password = data.get("password", BROKER_PASSWORD)

    global BROKER_EMAIL, BROKER_PASSWORD
    BROKER_EMAIL = email
    BROKER_PASSWORD = password

    ok = connect_broker()
    return jsonify({
        "success": ok,
        "status": connection_status
    })

@app.route("/balance")
def api_balance():
    """Retorna saldo atual"""
    if not ensure_connection():
        return jsonify({"error": "Não conectado", "status": connection_status}), 503

    try:
        with api_lock:
            balance = api_instance.get_balance()
            currency = api_instance.get_currency()
            mode = api_instance.get_balance_mode()

            connection_status["balance"] = balance
            connection_status["currency"] = currency
            connection_status["mode"] = mode

            return jsonify({
                "balance": balance,
                "currency": currency,
                "mode": mode
            })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/actives")
def api_actives():
    """Retorna pares disponíveis (abertos)"""
    if not ensure_connection():
        return jsonify({"error": "Não conectado"}), 503

    try:
        with api_lock:
            # Pega dados de inicialização
            data = api_instance.get_all_init_v2(0.1)

            binarias = []
            turbo = []

            for tipo, lista in [("binary", binarias), ("turbo", turbo)]:
                if tipo in data:
                    for aid, active in data[tipo]["actives"].items():
                        nome = str(active["name"]).split(".")[1]
                        if active["enabled"] and not active["is_suspended"]:
                            lista.append({
                                "id": int(aid),
                                "name": nome,
                                "type": tipo,
                                "is_otc": "OTC" in nome.upper()
                            })

            return jsonify({
                "binary": binarias,
                "turbo": turbo,
                "total": len(binarias) + len(turbo)
            })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/candles/<active>")
def api_candles(active):
    """Retorna candles de um par"""
    if not ensure_connection():
        return jsonify({"error": "Não conectado"}), 503

    # Parâmetros da query
    interval = int(request.args.get("interval", 60))  # segundos (60=M1, 300=M5)
    count = int(request.args.get("count", 10))

    try:
        with api_lock:
            endtime = time.time()
            candles = api_instance.get_candles(active, interval, count, endtime)

            # Formata candles
            formatted = []
            for c in candles:
                formatted.append({
                    "from": c.get("from"),
                    "to": c.get("to"),
                    "open": c.get("open"),
                    "close": c.get("close"),
                    "max": c.get("max"),
                    "min": c.get("min"),
                    "volume": c.get("volume"),
                    "color": "green" if c.get("close", 0) >= c.get("open", 0) else "red"
                })

            return jsonify({
                "active": active,
                "interval": interval,
                "candles": formatted
            })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/payout/<active>")
def api_payout(active):
    """Retorna payout de um par"""
    if not ensure_connection():
        return jsonify({"error": "Não conectado"}), 503

    timeframe = int(request.args.get("timeframe", 1))

    try:
        with api_lock:
            payout = api_instance.get_payout(active, timeframe)
            return jsonify({
                "active": active,
                "timeframe": timeframe,
                "payout": payout
            })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/buy", methods=["POST"])
def api_buy():
    """Executa uma ordem de compra"""
    if not ensure_connection():
        return jsonify({"error": "Não conectado"}), 503

    data = request.get_json()
    if not data:
        return jsonify({"error": "Dados não fornecidos"}), 400

    active = data.get("active")
    amount = data.get("amount", 1)
    direction = data.get("direction", "CALL")  # CALL ou PUT
    expiration = data.get("expiration", 1)  # minutos

    if not active:
        return jsonify({"error": "Par de moedas não especificado"}), 400

    try:
        with api_lock:
            # Executa ordem binária
            status, order_id = api_instance.buy_binary(active, amount, direction, expiration)

            return jsonify({
                "success": status,
                "order_id": order_id,
                "active": active,
                "direction": direction,
                "amount": amount,
                "expiration": expiration
            })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/check/<order_id>")
def api_check(order_id):
    """Verifica resultado de uma ordem"""
    if not ensure_connection():
        return jsonify({"error": "Não conectado"}), 503

    try:
        with api_lock:
            # Tenta check_win_v3 (para binárias)
            try:
                result = api_instance.check_win_v3(order_id, polling_time=1)
                return jsonify({
                    "order_id": order_id,
                    "profit": result,
                    "win": result > 0 if result else None
                })
            except:
                pass

            # Fallback para check_win_v2
            try:
                result = api_instance.check_win_v2(order_id, polling_time=1)
                return jsonify({
                    "order_id": order_id,
                    "profit": result,
                    "win": result > 0 if result else None
                })
            except:
                pass

            return jsonify({"error": "Não foi possível verificar resultado"}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/change_mode", methods=["POST"])
def api_change_mode():
    """Troca entre REAL e PRACTICE"""
    if not ensure_connection():
        return jsonify({"error": "Não conectado"}), 503

    data = request.get_json() or {}
    mode = data.get("mode", "PRACTICE")

    try:
        with api_lock:
            api_instance.change_balance(mode)
            connection_status["mode"] = mode
            return jsonify({"success": True, "mode": mode})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ═══════════════════════════════════════════════════════════════════════════════
# INICIALIZAÇÃO
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Tenta conectar ao iniciar
    print("=" * 60)
    print("  BROKER 10 API SERVER - TRADER CRISTÃO")
    print("=" * 60)

    # Conecta na inicialização (opcional)
    # connect_broker()

    # Inicia servidor
    app.run(host="0.0.0.0", port=API_PORT, debug=False)
