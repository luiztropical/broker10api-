# Broker 10 API Server - TRADER CRISTÃO

Servidor Flask para conectar à API da Broker 10 e expor endpoints REST JSON.

## Deploy no Render.com

### 1. Configurar Variáveis de Ambiente
No dashboard do Render.com, vá em **Environment** e adicione:

```
BROKER_EMAIL=seu_email@broker10.com
BROKER_PASSWORD=sua_senha
```

### 2. Endpoints Disponíveis

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/` | Status da API |
| POST | `/connect` | Conectar com email/senha |
| GET | `/balance` | Saldo da conta |
| GET | `/actives` | Lista de pares disponíveis |
| GET | `/candles/{par}` | Velas históricas |
| GET | `/realtime/{par}` | Velas em tempo real |
| GET | `/payout/{par}` | Payout do par |
| POST | `/buy` | Executar ordem |
| POST | `/change_mode` | Trocar REAL/DEMO |
| GET | `/check_win/{order_id}` | Verificar resultado |

### 3. Exemplos de Uso

#### Conectar:
```bash
curl -X POST https://sua-api.onrender.com/connect   -H "Content-Type: application/json"   -d '{"email":"seu@email.com","password":"senha"}'
```

#### Pegar velas:
```bash
curl https://sua-api.onrender.com/candles/EURUSD-OTC?interval=60&count=10
```

#### Velas em tempo real:
```bash
curl https://sua-api.onrender.com/realtime/EURUSD-OTC?size=60
```

#### Executar ordem:
```bash
curl -X POST https://sua-api.onrender.com/buy   -H "Content-Type: application/json"   -d '{"active":"EURUSD-OTC","amount":10,"direction":"CALL","expiration":1}'
```

### 4. Estrutura de Arquivos no GitHub

```
broker10api/
├── broker10_server_flask.py  # Este servidor Flask
├── requirements.txt          # Dependências
├── Procfile                  # Comando de inicialização
├── stable_api.py             # API estável Broker 10
├── api.py                    # Core da API
├── constants.py              # Códigos dos ativos
├── global_value.py           # Variáveis globais
├── expiration.py             # Cálculos de expiração
├── __init__.py               # Inicialização
├── http/                     # Handlers HTTP
│   ├── login.py
│   ├── logout.py
│   ├── auth.py
│   ├── ...
└── ws/                       # WebSocket
    └── client.py
```
