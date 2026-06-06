
"""
═══════════════════════════════════════════════════════════════════════════════
  BROKER 10 API SERVER - TRADER CRISTÃO (Versão Simples)
  Servidor HTTP nativo Python - funciona em qualquer versão!
═══════════════════════════════════════════════════════════════════════════════
"""

import os
import sys
import json
import time
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse

# Importa a API da Broker 10
try:
    from broker10api.stable_api import Broker10_Api
    import broker10api.constants as OP_code
    import broker10api.global_value as global_value
    API_AVAILABLE = True
except ImportError as e:
    print(f"AVISO: broker10api não encontrado: {e}")
    API_AVAILABLE = False

# Configurações
API_PORT = int(os.environ.get("PORT", 5000))

# Estado global
class AppState:
    def __init__(self):
        self.api_instance = None
        self.connected = False
        self.error = None
        self.balance = None
        self.currency = None
        self.mode = "PRACTICE"
        self.lock = threading.Lock()

    def get_credentials(self):
        return {
            "email": os.environ.get("BROKER_EMAIL", ""),
            "password": os.environ.get("BROKER_PASSWORD", "")
        }

    def connect(self):
        if not API_AVAILABLE:
            self.error = "API broker10api não instalada"
            return False

        creds = self.get_credentials()
        if not creds["email"] or not creds["password"]:
            self.error = "Credenciais não configuradas"
            return False

        try:
            print(f"[{datetime.now()}] Conectando na Broker 10...")
            self.api_instance = Broker10_Api(creds["email"], creds["password"])
            ok, reason = self.api_instance.connect()

            if ok:
                self.connected = True
                self.error = None
                try:
                    self.balance = self.api_instance.get_balance()
                    self.currency = self.api_instance.get_currency()
                    self.mode = self.api_instance.get_balance_mode()
                except:
                    pass
                print(f"[{datetime.now()}] Conectado!")
                return True
            else:
                self.connected = False
                self.error = str(reason)
                return False
        except Exception as e:
            self.connected = False
            self.error = str(e)
            return False

app_state = AppState()

class APIHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Silencia logs padrão
        pass

    def _send_json(self, status_code, data):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def do_OPTIONS(self):
        self._send_json(200, {"status": "ok"})

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        # Rota raiz - status
        if path == "/" or path == "/status":
            self._send_json(200, {
                "status": "online",
                "service": "Broker 10 API Server - TRADER CRISTÃO",
                "version": "simple",
                "connected": app_state.connected,
                "balance": app_state.balance,
                "currency": app_state.currency,
                "mode": app_state.mode,
                "error": app_state.error,
                "timestamp": datetime.now().isoformat()
            })
            return

        # Rota balance
        if path == "/balance":
            if not app_state.connected:
                app_state.connect()

            if app_state.connected and app_state.api_instance:
                try:
                    with app_state.lock:
                        app_state.balance = app_state.api_instance.get_balance()
                        app_state.currency = app_state.api_instance.get_currency()
                        app_state.mode = app_state.api_instance.get_balance_mode()
                except Exception as e:
                    self._send_json(500, {"error": str(e)})
                    return

            self._send_json(200, {
                "balance": app_state.balance,
                "currency": app_state.currency,
                "mode": app_state.mode
            })
            return

        # Rota actives
        if path == "/actives":
            if not app_state.connected:
                app_state.connect()

            if not app_state.connected:
                self._send_json(503, {"error": "Não conectado"})
                return

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

                    self._send_json(200, {
                        "binary": binarias,
                        "turbo": turbo,
                        "total": len(binarias) + len(turbo)
                    })
                    return
            except Exception as e:
                self._send_json(500, {"error": str(e)})
                return

        # Rota candles
        if path.startswith("/candles/"):
            active = path.split("/")[2]
            interval = int(query.get("interval", [60])[0])
            count = int(query.get("count", [10])[0])

            if not app_state.connected:
                app_state.connect()

            if not app_state.connected:
                self._send_json(503, {"error": "Não conectado"})
                return

            try:
                with app_state.lock:
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

                    self._send_json(200, {
                        "active": active,
                        "interval": interval,
                        "candles": formatted
                    })
                    return
            except Exception as e:
                self._send_json(500, {"error": str(e)})
                return

        # Rota payout
        if path.startswith("/payout/"):
            active = path.split("/")[2]
            timeframe = int(query.get("timeframe", [1])[0])

            if not app_state.connected:
                app_state.connect()

            if not app_state.connected:
                self._send_json(503, {"error": "Não conectado"})
                return

            try:
                with app_state.lock:
                    payout = app_state.api_instance.get_payout(active, timeframe)
                    self._send_json(200, {
                        "active": active,
                        "timeframe": timeframe,
                        "payout": payout
                    })
                    return
            except Exception as e:
                self._send_json(500, {"error": str(e)})
                return

        # Rota não encontrada
        self._send_json(404, {"error": "Rota não encontrada"})

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        # Ler body
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8")

        try:
            data = json.loads(body) if body else {}
        except:
            data = {}

        # Rota connect
        if path == "/connect":
            if data.get("email"):
                os.environ["BROKER_EMAIL"] = data["email"]
            if data.get("password"):
                os.environ["BROKER_PASSWORD"] = data["password"]

            ok = app_state.connect()
            self._send_json(200, {
                "success": ok,
                "status": {
                    "connected": app_state.connected,
                    "balance": app_state.balance,
                    "currency": app_state.currency,
                    "mode": app_state.mode,
                    "error": app_state.error
                }
            })
            return

        # Rota buy
        if path == "/buy":
            if not app_state.connected:
                app_state.connect()

            if not app_state.connected:
                self._send_json(503, {"error": "Não conectado"})
                return

            active = data.get("active")
            amount = data.get("amount", 1)
            direction = data.get("direction", "CALL")
            expiration = data.get("expiration", 1)

            if not active:
                self._send_json(400, {"error": "Par de moedas não especificado"})
                return

            try:
                with app_state.lock:
                    status, order_id = app_state.api_instance.buy_binary(active, amount, direction, expiration)
                    self._send_json(200, {
                        "success": status,
                        "order_id": order_id,
                        "active": active,
                        "direction": direction,
                        "amount": amount,
                        "expiration": expiration
                    })
                    return
            except Exception as e:
                self._send_json(500, {"error": str(e)})
                return

        # Rota change_mode
        if path == "/change_mode":
            if not app_state.connected:
                app_state.connect()

            if not app_state.connected:
                self._send_json(503, {"error": "Não conectado"})
                return

            mode = data.get("mode", "PRACTICE")

            try:
                with app_state.lock:
                    app_state.api_instance.change_balance(mode)
                    app_state.mode = mode
                    self._send_json(200, {"success": True, "mode": mode})
                    return
            except Exception as e:
                self._send_json(500, {"error": str(e)})
                return

        # Rota não encontrada
        self._send_json(404, {"error": "Rota não encontrada"})

def run_server():
    server = HTTPServer(("0.0.0.0", API_PORT), APIHandler)
    print(f"[{datetime.now()}] Servidor iniciado na porta {API_PORT}")
    print(f"[{datetime.now()}] URL: http://0.0.0.0:{API_PORT}")
    print(f"[{datetime.now()}] API Broker 10 disponível: {API_AVAILABLE}")

    # Tenta conectar na inicialização
    if API_AVAILABLE:
        app_state.connect()

    server.serve_forever()

if __name__ == "__main__":
    print("=" * 60)
    print("  BROKER 10 API SERVER - TRADER CRISTÃO (Simples)")
    print("=" * 60)
    run_server()
