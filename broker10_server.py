
"""
═══════════════════════════════════════════════════════════════════════════════
  BROKER 10 API SERVER - TRADER CRISTÃO (v2)
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

# Importa a API da Broker 10
try:
    from broker10api.stable_api import Broker10_Api
    import broker10api.constants as OP_code
    import broker10api.global_value as global_value
except ImportError:
    print("AVISO: broker10api não encontrado. Usando modo simulação.")
    Broker10_Api = None

app = Flask(__name__)
CORS(app)

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURAÇÕES (lidas do ambiente)
# ═══════════════════════════════════════════════════════════════════════════════

API_PORT = int(os.environ.get("PORT", 5000))

# ═══════════════════════════════════════════════════════════════════════════════
# CLASSE PARA GERENCIAR ESTADO (evita uso de global)
# ═══════════════════════════════════════════════════════════════════════════════

class AppState:
    def __init__(self):
        self.api_instance = None
        self.connection_status = {
            "connected": False,
            "last_check": None,
            "error": None,
            "profile": None,
            "balance": None,
            "currency": None,
            "mode": "PRACTICE"
        }
        self.api_lock = threading.Lock()

    def get_credentials(self):
        """Pega credenciais do ambiente"""
        return {
            "email": os.environ.get("BROKER_EMAIL", ""),
            "password": os.environ.get("BROKER_PASSWORD", "")
        }

    def connect(self):
        """Conecta na Broker 10"""
        if Broker10_Api is None:
            self.connection_status["error"] = "API broker10api não instalada"
            return False

        creds = self.get_credentials()
        if not creds["email"] or not creds["password"]:
            self.connection_status["error"] = "Credenciais não configuradas"
            return False

        try:
            print(f"[{datetime.now()}] Conectando na Broker 10...")
            self.api_instance = Broker10_Api(creds["email"], creds["password"])
            ok, reason = self.api_instance.connect()

            if ok:
                self.connection_status["connected"] = True
                self.connection_status["error"] = None
                self.connection_status["last_check"] = time.time()

                # Pega informações do perfil
                try:
                    profile = self.api_instance.get_profile()
                    self.connection_status["profile"] = profile
                except:
                    pass

                # Pega saldo
                try:
                    balance = self.api_instance.get_balance()
                    self.connection_status["balance"] = balance
                except:
                    pass

                # Pega moeda
                try:
                    currency = self.api_instance.get_currency()
                    self.connection_status["currency"] = currency
                except:
                    pass

                # Pega modo
                try:
                    mode = self.api_instance.get_balance_mode()
                    self.connection_status["mode"] = mode
                except:
                    pass

                print(f"[{datetime.now()}] Conectado! Saldo: {self.connection_status['balance']} {self.connection_status['currency']}")
                return True
            else:
                self.connection_status["connected"] = False
                self.connection_status["error"] = str(reason)
                print(f"[{datetime.now()}] Erro: {reason}")
                return False

        except Exception as e:
            self.connection_status["connected"] = False
            self.connection_status["error"] = str(e)
            print(f"[{datetime.now()}] Exceção: {e}")
            return False

    def ensure_connection(self):
        """Garante que está conectado"""
        if not self.connection_status["connected"] or self.api_instance is None:
            return self.connect()
        return True

# Instancia o estado global da aplicação
app_state = AppState()

# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS DA API
# ═══════════════════════════════════════════════════════════════════════════════

@app.route("/")
def home():
    """Página inicial - status"""
    return jsonify({
        "status": "online",
        "service": "Broker 10 API Server - TRADER CRISTÃO",
        "version": "2.0",
        "connected": app_state.connection_status["connected"],
        "timestamp": datetime.now().isoformat()
    })

@app.route("/status")
def status():
    """Status da conexão"""
    return jsonify({
        "connected": app_state.connection_status["connected"],
        "balance": app_state.connection_status["balance"],
        "currency": app_state.connection_status["currency"],
        "mode": app_state.connection_status["mode"],
        "error": app_state.connection_status["error"],
        "last_check": app_state.connection_status["last_check"]
    })

@app.route("/connect", methods=["POST"])
def api_connect():
    """Força reconexão"""
    data = request.get_json() or {}

    # Permite sobrescrever credenciais via request (opcional)
    if data.get("email"):
        os.environ["BROKER_EMAIL"] = data["email"]
    if data.get("password"):
        os.environ["BROKER_PASSWORD"] = data["password"]

    ok = app_state.connect()
    return jsonify({
        "success": ok,
        "status": app_state.connection_status
    })

@app.route("/balance")
def api_balance():
    """Retorna saldo atual"""
    if not app_state.ensure_connection():
        return jsonify({"error": "Não conectado", "status": app_state.connection_status}), 503

    try:
        with app_state.api_lock:
            balance = app_state.api_instance.get_balance()
            currency = app_state.api_instance.get_currency()
            mode = app_state.api_instance.get_balance_mode()

            app_state.connection_status["balance"] = balance
            app_state.connection_status["currency"] = currency
            app_state.connection_status["mode"] = mode

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
    if not app_state.ensure_connection():
        return jsonify({"error": "Não conectado"}), 503

    try:
        with app_state.api_lock:
            data = app_state.api_instance.get_all_init_v2(0.1)

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
    if not app_state.ensure_connection():
        return jsonify({"error": "Não conectado"}), 503

    interval = int(request.args.get("interval", 60))
    count = int(request.args.get("count", 10))

    try:
        with app_state.api_lock:
            endtime = time.time()
            candles = app_state.api_instance.get_candles(active, interval, count, endtime)

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
    if not app_state.ensure_connection():
        return jsonify({"error": "Não conectado"}), 503

    timeframe = int(request.args.get("timeframe", 1))

    try:
        with app_state.api_lock:
            payout = app_state.api_instance.get_payout(active, timeframe)
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
    if not app_state.ensure_connection():
        return jsonify({"error": "Não conectado"}), 503

    data = request.get_json()
    if not data:
        return jsonify({"error": "Dados não fornecidos"}), 400

    active = data.get("active")
    amount = data.get("amount", 1)
    direction = data.get("direction", "CALL")
    expiration = data.get("expiration", 1)

    if not active:
        return jsonify({"error": "Par de moedas não especificado"}), 400

    try:
        with app_state.api_lock:
            status, order_id = app_state.api_instance.buy_binary(active, amount, direction, expiration)

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
    if not app_state.ensure_connection():
        return jsonify({"error": "Não conectado"}), 503

    try:
        with app_state.api_lock:
            try:
                result = app_state.api_instance.check_win_v3(order_id, polling_time=1)
                return jsonify({
                    "order_id": order_id,
                    "profit": result,
                    "win": result > 0 if result else None
                })
            except:
                pass

            try:
                result = app_state.api_instance.check_win_v2(order_id, polling_time=1)
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
    if not app_state.ensure_connection():
        return jsonify({"error": "Não conectado"}), 503

    data = request.get_json() or {}
    mode = data.get("mode", "PRACTICE")

    try:
        with app_state.api_lock:
            app_state.api_instance.change_balance(mode)
            app_state.connection_status["mode"] = mode
            return jsonify({"success": True, "mode": mode})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ═══════════════════════════════════════════════════════════════════════════════
# INICIALIZAÇÃO
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("  BROKER 10 API SERVER - TRADER CRISTÃO v2")
    print("=" * 60)

    app.run(host="0.0.0.0", port=API_PORT, debug=False)
