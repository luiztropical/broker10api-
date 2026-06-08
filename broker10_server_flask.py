"""
═══════════════════════════════════════════════════════════════════════════════
  BROKER 10 API SERVER - TRADER CRISTÃO (Flask)
  Servidor HTTP Flask para deploy no Render.com
  Conecta à API Broker 10 e expõe endpoints REST JSON
═══════════════════════════════════════════════════════════════════════════════
"""

import os
import sys
import json
import time
import threading
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS

print("=" * 60)
print("  BROKER 10 API SERVER - TRADER CRISTÃO (Flask)")
print("=" * 60)

# ═══════════════════════════════════════════════════════════════════════════════
# IMPORTS DA API BROKER 10
# ═══════════════════════════════════════════════════════════════════════════════
API_AVAILABLE = False
api_error = None

try:
    print("\n[1/4] Carregando módulos da API Broker 10...")

    # Adiciona o diretório atual ao path para imports
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    from stable_api import Broker10_Api
    print("   ✓ stable_api")

    import constants as OP_code
    print("   ✓ constants")

    import global_value
    print("   ✓ global_value")

    import expiration
    print("   ✓ expiration")

    API_AVAILABLE = True
    print("\n[✓] API Broker 10 carregada com sucesso!")

except Exception as e:
    API_AVAILABLE = False
    api_error = f"{type(e).__name__}: {str(e)}"
    print(f"\n[✗] ERRO ao carregar API: {api_error}")

# ═══════════════════════════════════════════════════════════════════════════════
# FLASK APP
# ═══════════════════════════════════════════════════════════════════════════════
app = Flask(__name__)
CORS(app)  # Permite requisições de qualquer origem (Lovable, etc)

# ═══════════════════════════════════════════════════════════════════════════════
# ESTADO GLOBAL
# ═══════════════════════════════════════════════════════════════════════════════
class AppState:
    def __init__(self):
        self.api_instance = None
        self.connected = False
        self.error = None
        self.balance = None
        self.currency = None
        self.mode = "PRACTICE"
        self.lock = threading.Lock()
        self.realtime_subscriptions = {}  # Par -> thread de streaming
        self.realtime_data = {}  # Par -> últimas velas

    def get_credentials(self):
        return {
            "email": os.environ.get("BROKER_EMAIL", ""),
            "password": os.environ.get("BROKER_PASSWORD", "")
        }

    def connect(self):
        if not API_AVAILABLE:
            self.error = f"API broker10api não disponível: {api_error}"
            return False

        creds = self.get_credentials()

        if not creds["email"] or not creds["password"]:
            self.error = "Credenciais não configuradas (BROKER_EMAIL / BROKER_PASSWORD)"
            return False

        try:
            print("\n" + "=" * 60)
            print("INICIANDO CONEXÃO BROKER 10")
            print(f"EMAIL: {creds['email']}")
            print("=" * 60)

            self.api_instance = Broker10_Api(
                creds["email"],
                creds["password"]
            )
            print("[✓] Objeto API criado")

            ok, reason = self.api_instance.connect()
            print(f"[✓] Resultado: ok={ok}, reason={reason}")

            if ok:
                self.connected = True
                self.error = None

                # Pega informações da conta
                try:
                    self.balance = self.api_instance.get_balance()
                    self.currency = self.api_instance.get_currency()
                    self.mode = self.api_instance.get_balance_mode()
                    print(f"[✓] Saldo: {self.balance} {self.currency} | Modo: {self.mode}")
                except Exception as e:
                    print(f"[!] Aviso: não conseguiu pegar saldo: {e}")

                print("[✓] CONECTADO COM SUCESSO!")
                return True
            else:
                self.connected = False
                self.error = str(reason)
                print(f"[✗] Falha na conexão: {reason}")
                return False

        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            print(f"[✗] ERRO COMPLETO: {error_msg}")
            self.connected = False
            self.error = error_msg
            return False


app_state = AppState()

# ═══════════════════════════════════════════════════════════════════════════════
# ROTAS DA API
# ═══════════════════════════════════════════════════════════════════════════════

@app.route("/", methods=["GET"])
def status():
    """Status da API"""
    return jsonify({
        "status": "online",
        "service": "Broker 10 API Server - TRADER CRISTÃO",
        "version": "2.0 Flask",
        "api_available": API_AVAILABLE,
        "connected": app_state.connected,
        "balance": app_state.balance,
        "currency": app_state.currency,
        "mode": app_state.mode,
        "error": app_state.error,
        "timestamp": datetime.now().isoformat()
    })


@app.route("/connect", methods=["POST", "OPTIONS"])
def connect():
    """Conectar à Broker 10 com email/senha"""
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"})

    data = request.get_json() or {}

    # Atualiza credenciais se fornecidas
    if data.get("email"):
        os.environ["BROKER_EMAIL"] = data["email"]
    if data.get("password"):
        os.environ["BROKER_PASSWORD"] = data["password"]

    ok = app_state.connect()

    return jsonify({
        "success": ok,
        "connected": app_state.connected,
        "balance": app_state.balance,
        "currency": app_state.currency,
        "mode": app_state.mode,
        "error": app_state.error
    })


@app.route("/balance", methods=["GET"])
def balance():
    """Pega saldo da conta"""
    if not app_state.connected:
        app_state.connect()

    if not app_state.connected:
        return jsonify({"error": "Não conectado", "details": app_state.error}), 503

    try:
        with app_state.lock:
            bal = app_state.api_instance.get_balance()
            curr = app_state.api_instance.get_currency()
            mode = app_state.api_instance.get_balance_mode()

            app_state.balance = bal
            app_state.currency = curr
            app_state.mode = mode

        return jsonify({
            "balance": bal,
            "currency": curr,
            "mode": mode
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/actives", methods=["GET"])
def actives():
    """Lista todos os pares de moedas disponíveis"""
    if not app_state.connected:
        app_state.connect()

    if not app_state.connected:
        return jsonify({"error": "Não conectado", "details": app_state.error}), 503

    try:
        with app_state.lock:
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

            # Separa OTC e normal
            pares_otc = [p for p in binarias if p["is_otc"]]
            pares_normal = [p for p in binarias if not p["is_otc"]]

            return jsonify({
                "binary": binarias,
                "turbo": turbo,
                "otc": pares_otc,
                "normal": pares_normal,
                "total": len(binarias) + len(turbo)
            })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/candles/<active>", methods=["GET"])
def candles(active):
    """Pega velas históricas de um par"""
    if not app_state.connected:
        app_state.connect()

    if not app_state.connected:
        return jsonify({"error": "Não conectado"}), 503

    interval = int(request.args.get("interval", 60))  # segundos (60=M1, 300=M5)
    count = int(request.args.get("count", 10))

    try:
        with app_state.lock:
            endtime = time.time()
            candles_data = app_state.api_instance.get_candles(active, interval, count, endtime)

            formatted = []
            for c in candles_data:
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
                "count": len(formatted),
                "candles": formatted
            })

    except Exception as e:
        return jsonify({"error": str(e), "active": active}), 500


@app.route("/realtime/<active>", methods=["GET"])
def realtime(active):
    """Pega velas em tempo real (requer subscribe primeiro)"""
    if not app_state.connected:
        app_state.connect()

    if not app_state.connected:
        return jsonify({"error": "Não conectado"}), 503

    size = int(request.args.get("size", 60))  # intervalo em segundos

    try:
        with app_state.lock:
            # Inicia streaming se não estiver rodando
            if active not in app_state.realtime_subscriptions:
                app_state.api_instance.start_candles_stream(active, size, 100)
                app_state.realtime_subscriptions[active] = True
                print(f"[✓] Streaming iniciado para {active} M{size//60}")

            # Pega dados em tempo real
            rt_data = app_state.api_instance.get_realtime_candles(active, size)

            if rt_data:
                # Converte para lista ordenada
                candles_list = []
                for timestamp, candle in sorted(rt_data.items()):
                    candles_list.append({
                        "from": candle.get("from"),
                        "to": candle.get("to"),
                        "open": candle.get("open"),
                        "close": candle.get("close"),
                        "max": candle.get("max"),
                        "min": candle.get("min"),
                        "volume": candle.get("volume"),
                        "color": "green" if candle.get("close", 0) >= candle.get("open", 0) else "red"
                    })

                return jsonify({
                    "active": active,
                    "size": size,
                    "streaming": True,
                    "count": len(candles_list),
                    "candles": candles_list[-20:]  # Últimas 20 velas
                })
            else:
                return jsonify({
                    "active": active,
                    "size": size,
                    "streaming": True,
                    "count": 0,
                    "candles": [],
                    "message": "Aguardando dados..."
                })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/payout/<active>", methods=["GET"])
def payout(active):
    """Pega payout de um par específico"""
    if not app_state.connected:
        app_state.connect()

    if not app_state.connected:
        return jsonify({"error": "Não conectado"}), 503

    timeframe = int(request.args.get("timeframe", 1))  # minutos

    try:
        with app_state.lock:
            payout_val = app_state.api_instance.get_payout(active, timeframe)

            return jsonify({
                "active": active,
                "timeframe": timeframe,
                "payout": payout_val
            })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/buy", methods=["POST", "OPTIONS"])
def buy():
    """Executa uma ordem de compra"""
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"})

    if not app_state.connected:
        app_state.connect()

    if not app_state.connected:
        return jsonify({"error": "Não conectado"}), 503

    data = request.get_json() or {}

    active = data.get("active")
    amount = data.get("amount", 1)
    direction = data.get("direction", "CALL")  # CALL ou PUT
    expiration = data.get("expiration", 1)  # minutos

    if not active:
        return jsonify({"error": "Par de moedas não especificado"}), 400

    try:
        with app_state.lock:
            status, order_id = app_state.api_instance.buy_binary(
                active, amount, direction, expiration
            )

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


@app.route("/change_mode", methods=["POST", "OPTIONS"])
def change_mode():
    """Troca entre REAL e PRACTICE"""
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"})

    if not app_state.connected:
        app_state.connect()

    if not app_state.connected:
        return jsonify({"error": "Não conectado"}), 503

    data = request.get_json() or {}
    mode = data.get("mode", "PRACTICE")

    try:
        with app_state.lock:
            app_state.api_instance.change_balance(mode)
            app_state.mode = mode

            return jsonify({
                "success": True,
                "mode": mode
            })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/check_win/<order_id>", methods=["GET"])
def check_win(order_id):
    """Verifica resultado de uma ordem"""
    if not app_state.connected:
        app_state.connect()

    if not app_state.connected:
        return jsonify({"error": "Não conectado"}), 503

    try:
        with app_state.lock:
            # Converte order_id para int se necessário
            try:
                order_id = int(order_id)
            except:
                pass

            result = app_state.api_instance.check_win_v3(order_id, polling_time=1)

            return jsonify({
                "order_id": order_id,
                "profit": result,
                "win": result > 0 if result else None
            })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ═══════════════════════════════════════════════════════════════════════════════
# INICIALIZAÇÃO
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    PORT = int(os.environ.get("PORT", 5000))

    print("\n" + "=" * 60)
    print(f"INICIANDO SERVIDOR FLASK NA PORTA {PORT}")
    print("=" * 60)

    # Tenta conectar automaticamente se credenciais estiverem configuradas
    if API_AVAILABLE and os.environ.get("BROKER_EMAIL") and os.environ.get("BROKER_PASSWORD"):
        print("\n[*] Credenciais encontradas, tentando conexão automática...")
        app_state.connect()

    # Inicia servidor Flask
    app.run(host="0.0.0.0", port=PORT, debug=False)
