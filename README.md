
# 🚀 BROKER 10 API SERVER - TRADER CRISTÃO

Servidor REST que conecta na corretora Broker 10 e expõe dados via HTTP para seu aplicativo web.

---

## 📋 O QUE ESTE SERVIDOR FAZ

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/` | GET | Status do servidor |
| `/status` | GET | Status da conexão Broker 10 |
| `/connect` | POST | Conectar na Broker 10 |
| `/balance` | GET | Saldo atual |
| `/actives` | GET | Pares de moedas disponíveis |
| `/candles/<par>` | GET | Candles de um par (ex: EURUSD-OTC) |
| `/payout/<par>` | GET | Payout % de um par |
| `/buy` | POST | Executar ordem CALL/PUT |
| `/check/<id>` | GET | Verificar resultado WIN/LOSS |
| `/change_mode` | POST | Trocar REAL/PRACTICE |

---

## 🛠️ COMO HOSPEDAR NO RENDER.COM (GRATUITO)

### Passo 1: Criar conta no Render
1. Acesse: https://render.com
2. Crie conta com GitHub ou email
3. É GRATUITO!

### Passo 2: Criar repositório no GitHub
1. Crie um repositório novo
2. Faça upload desses 4 arquivos:
   - `broker10_server.py` (o servidor)
   - `requirements.txt` (dependências)
   - `render.yaml` (configuração Render)
   - Todos os arquivos da pasta `broker10api/` (a API Python)

### Passo 3: Conectar no Render
1. No painel do Render, clique "New +" → "Web Service"
2. Conecte seu repositório GitHub
3. O Render vai detectar o `render.yaml` automaticamente

### Passo 4: Configurar variáveis de ambiente
1. No painel do seu serviço, vá em "Environment"
2. Adicione:
   - `BROKER_EMAIL` = seu_email@broker10.com
   - `BROKER_PASSWORD` = sua_senha

### Passo 5: Deploy!
1. Clique "Deploy"
2. O Render vai te dar uma URL tipo: `https://broker10-api-server.onrender.com`
3. Pronto! Sua API está no ar!

---

## 🔌 COMO SEU APLICATIVO WEB USA ESTA API

### Exemplo em JavaScript (para colocar no seu aplicativo):

```javascript
// URL base da sua API hospedada
const API_URL = "https://broker10-api-server.onrender.com";

// 1. Verificar status
async function checkStatus() {
    const res = await fetch(`${API_URL}/status`);
    const data = await res.json();
    console.log("Conectado:", data.connected);
    console.log("Saldo:", data.balance, data.currency);
    return data;
}

// 2. Pegar candles
async function getCandles(par = "EURUSD-OTC", interval = 60) {
    const res = await fetch(`${API_URL}/candles/${par}?interval=${interval}&count=10`);
    const data = await res.json();
    return data.candles; // Array de candles
}

// 3. Executar ordem
async function buyOrder(par, direction, amount, expiration) {
    const res = await fetch(`${API_URL}/buy`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            active: par,
            direction: direction,  // "CALL" ou "PUT"
            amount: amount,        // valor em dólares
            expiration: expiration  // minutos
        })
    });
    return await res.json();
}

// 4. Verificar resultado
async function checkResult(orderId) {
    const res = await fetch(`${API_URL}/check/${orderId}`);
    return await res.json();
}
```

---

## 📦 ESTRUTURA DE ARQUIVOS

```
meu-projeto/
├── broker10_server.py      ← Servidor Flask (este arquivo)
├── requirements.txt       ← Dependências Python
├── render.yaml            ← Configuração Render
├── broker10api/            ← Pasta com a API da Broker 10
│   ├── __init__.py
│   ├── api.py
│   ├── stable_api.py
│   ├── constants.py
│   ├── global_value.py
│   ├── expiration.py
│   └── ws/                ← WebSocket handlers
│       └── ...
└── README.md
```

---

## ⚠️ IMPORTANTE

1. **Segurança**: Nunca deixe email/senha no código! Use variáveis de ambiente.
2. **Limite gratuito**: O Render free "dorme" após 15 min de inatividade. A primeira chamada pode demorar ~30s para "acordar".
3. **Para manter ativo**: Use um serviço como UptimeRobot (gratuito) para pingar a cada 5 minutos.

---

## 🆘 SUPORTE

Se tiver dúvidas, me chame! Estamos juntos nessa, meu amigo! 🙏
