"""
═══════════════════════════════════════════════════════════════════════════════
  BROKER 10 API SERVER - TRADER CRISTÃO (Socket Puro)
  Servidor HTTP feito com sockets TCP puros - funciona em qualquer Python!
═══════════════════════════════════════════════════════════════════════════════
"""

import os
import sys
import json
import time
import threading
import socket
from datetime import datetime

print("INICIO DO SERVIDOR")

# Importa a API da Broker 10
try:
    print("TESTANDO IMPORTS...")
    from stable_api import Broker10_Api
    print("OK stable_api")
    import constants as OP_code
    print("OK constants")
    import global_value
    print("OK global_value")
    API_AVAILABLE = True
    print("BROKER API CARREGADA")
except Exception as e:
    API_AVAILABLE = False
    print("################################")
    print("ERRO IMPORTANDO API")
    print(type(e).__name__)
    print(str(e))
    print("################################")

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
            print("=" * 60)
            print("INICIANDO LOGIN BROKER10")
            print("EMAIL:", creds["email"])
            print("=" * 60)

            self.api_instance = Broker10_Api(
                creds["email"],
                creds["password"]
            )

            print("OBJETO API CRIADO")

            ok, reason = self.api_instance.connect()

            print("RESULTADO LOGIN:")
            print("OK =", ok)
            print("REASON =", reason)

            if ok:
                self.connected = True
                self.error = None

                try:
                    self.balance = self.api_instance.get_balance()
                    self.currency = self.api_instance.get_currency()
                    self.mode = self.api_instance.get_balance_mode()
                except:
                    pass

                print("CONECTADO COM SUCESSO")
                return True

            else:
                self.connected = False
                self.error = str(reason)
                return False

        except Exception as e:
            print("ERRO COMPLETO DA BROKER:")
            print(type(e))
            print(str(e))

            self.connected = False
            self.error = str(e)
            return False


app_state = AppState()


def parse_request(data):
    """Parse simples de requisição HTTP"""
    lines = data.split("\r\n")
    if not lines:
        return None, None, None, {}

    first_line = lines[0]
    parts = first_line.split(" ")
    if len(parts) < 2:
        return None, None, None, {}

    method = parts[0]
    path = parts[1]

    # Parse query string
    if "?" in path:
        path, query_str = path.split("?", 1)
        query = {}
        for param in query_str.split("&"):
            if "=" in param:
                k, v = param.split("=", 1)
                query[k] = v
    else:
        query = {}

    # Parse body
    body = ""
    if "\r\n\r\n" in data:
        header_end = data.index("\r\n\r\n") + 4
        body = data[header_end:]

    return method, path, query, body


def send_response(conn, status_code, data):
    """Envia resposta HTTP"""
    status_text = {
        200: "OK",
        404: "Not Found",
        500: "Internal Server Error",
        503: "Service Unavailable"
    }
    text = status_text.get(status_code, "Unknown")

    body = json.dumps(data)
    response = f"HTTP/1.1 {status_code} {text}\r\n"
    response += "Content-Type: application/json\r\n"
    response += "Access-Control-Allow-Origin: *\r\n"
    response += "Access-Control-Allow-Methods: GET, POST, OPTIONS\r\n"
    response += "Access-Control-Allow-Headers: Content-Type\r\n"
    response += f"Content-Length: {len(body)}\r\n"
    response += "\r\n"
    response += body

    conn.sendall(response.encode("utf-8"))


def handle_request(conn, addr):
    """Processa uma requisição"""
    try:
        data = conn.recv(4096).decode("utf-8")
        if not data:
            return

        method, path, query, body = parse_request(data)

        if not method or not path:
            send_response(conn, 400, {"error": "Requisição inválida"})
            return

        # Handle OPTIONS (CORS preflight)
        if method == "OPTIONS":
            send_response(conn, 200, {"status": "ok"})
            return

        # Parse body JSON for POST
        body_data = {}
        if body:
            try:
                body_data = json.loads(body)
            except:
                pass

        # Rota raiz - status
        if path == "/" or path == "/status":
            send_response(conn, 200, {
                "status": "online",
                "service": "Broker 10 API Server - TRADER CRISTÃO",
                "version": "socket",
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
                        app_state.currency = self.api_instance.get_currency()
                        app_state.mode = self.api_instance.get_balance_mode()
                except Exception as e:
                    send_response(conn, 500, {"error": str(e)})
                    return

            send_response(conn, 200, {
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
                send_response(conn, 503, {"error": "Não conectado"})
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

                    send_response(conn, 200, {
                        "binary": binarias,
                        "turbo": turbo,
                        "total": len(binarias) + len(turbo)
                    })
                    return
            except Exception as e:
                send_response(conn, 500, {"error": str(e)})
                return

        # Rota candles
        if path.startswith("/candles/"):
            active = path.split("/")[2]
            interval = int(query.get("interval", 60))
            count = int(query.get("count", 10))

            if not app_state.connected:
                app_state.connect()

            if not app_state.connected:
                send_response(conn, 503, {"error": "Não conectado"})
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

                    send_response(conn, 200, {
                        "active": active,
                        "interval": interval,
                        "candles": formatted
                    })
                    return
            except Exception as e:
                send_response(conn, 500, {"error": str(e)})
                return

        # Rota payout
        if path.startswith("/payout/"):
            active = path.split("/")[2]
            timeframe = int(query.get("timeframe", 1))

            if not app_state.connected:
                app_state.connect()

            if not app_state.connected:
                send_response(conn, 503, {"error": "Não conectado"})
                return

            try:
                with app_state.lock:
                    payout = app_state.api_instance.get_payout(active, timeframe)
                    send_response(conn, 200, {
                        "active": active,
                        "timeframe": timeframe,
                        "payout": payout
                    })
                    return
            except Exception as e:
                send_response(conn, 500, {"error": str(e)})
                return

        # Rota connect (POST)
        if path == "/connect" and method == "POST":
            if body_data.get("email"):
                os.environ["BROKER_EMAIL"] = body_data["email"]
            if body_data.get("password"):
                os.environ["BROKER_PASSWORD"] = body_data["password"]

            ok = app_state.connect()
            send_response(conn, 200, {
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

        # Rota buy (POST)
        if path == "/buy" and method == "POST":
            if not app_state.connected:
                app_state.connect()

            if not app_state.connected:
                send_response(conn, 503, {"error": "Não conectado"})
                return

            active = body_data.get("active")
            amount = body_data.get("amount", 1)
            direction = body_data.get("direction", "CALL")
            expiration = body_data.get("expiration", 1)

            if not active:
                send_response(conn, 400, {"error": "Par de moedas não especificado"})
                return

            try:
                with app_state.lock:
                    status, order_id = app_state.api_instance.buy_binary(active, amount, direction, expiration)
                    send_response(conn, 200, {
                        "success": status,
                        "order_id": order_id,
                        "active": active,
                        "direction": direction,
                        "amount": amount,
                        "expiration": expiration
                    })
                    return
            except Exception as e:
                send_response(conn, 500, {"error": str(e)})
                return

        # Rota change_mode (POST)
        if path == "/change_mode" and method == "POST":
            if not app_state.connected:
                app_state.connect()

            if not app_state.connected:
                send_response(conn, 503, {"error": "Não conectado"})
                return

            mode = body_data.get("mode", "PRACTICE")

            try:
                with app_state.lock:
                    app_state.api_instance.change_balance(mode)
                    app_state.mode = mode
                    send_response(conn, 200, {"success": True, "mode": mode})
                    return
            except Exception as e:
                send_response(conn, 500, {"error": str(e)})
                return

        # Rota não encontrada
        send_response(conn, 404, {"error": "Rota não encontrada"})

    except Exception as e:
        print(f"Erro ao processar requisição: {e}")
    finally:
        conn.close()


def run_server():
    """Inicia o servidor socket"""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("0.0.0.0", API_PORT))
    server.listen(5)

    print(f"[{datetime.now()}] Servidor socket iniciado na porta {API_PORT}")
    print(f"[{datetime.now()}] API Broker 10 disponível: {API_AVAILABLE}")

    # Tenta conectar na inicialização
    if API_AVAILABLE:
        app_state.connect()

    while True:
        conn, addr = server.accept()
        thread = threading.Thread(target=handle_request, args=(conn, addr))
        thread.daemon = True
        thread.start()


if __name__ == "__main__":
    print("=" * 60)
    print("  BROKER 10 API SERVER - TRADER CRISTÃO (Socket)")
    print("=" * 60)
    run_server()
# teste deploy
