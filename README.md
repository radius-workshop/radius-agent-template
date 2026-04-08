# radius-agent-template

A minimal [NEST](https://github.com/projnanda/NEST-beta) agent that can send and receive payments on the [Radius network](https://radiustech.xyz). Fork this, set your env vars, and you have a payment-capable agent.

## Quick Start

```bash
# Clone
git clone https://github.com/radius-workshop/radius-agent-template.git
cd radius-agent-template

# Install
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env: add RADIUS_PRIVATE_KEY (required), ANTHROPIC_API_KEY (optional)

# Run
python agent.py
```

The agent starts on `http://localhost:6000/a2a` and registers with the NANDA agent network.

## Two Modes

### Command Routing (no LLM)

If `ANTHROPIC_API_KEY` is not set, the agent uses simple command routing:

```
balance              → Check your RUSD + SBC balances
balance 0x1234...    → Check someone else's balances
send 0x1234... 1.5   → Send 1.5 SBC to an address
status 0xabcd...     → Check a transaction's status
faucet               → Request testnet SBC
info                 → Chain info (ID, block, gas price)
help                 → List commands
```

### Natural Language (with LLM)

If `ANTHROPIC_API_KEY` is set, the agent uses Claude with tool-calling. Users can ask things like:

- "What's my balance?"
- "Send 0.5 SBC to 0x1234..."
- "Did my last transaction go through? Here's the hash: 0xabcd..."
- "Get me some testnet tokens"

## Files

| File | Purpose |
|------|---------|
| `agent.py` | Entry point — NANDA setup, command routing, LLM handler |
| `tools.py` | Tool definitions (Anthropic schema) + execution |
| `radius_wallet.py` | Vendored wallet library (balance, send, faucet, contracts) |
| `nest.yaml` | NEST agent configuration |
| `.env.example` | Environment variable template |
| `Dockerfile` | Container deployment (Railway, etc.) |

## How It Works

1. **NANDA registration** — The agent registers with the NANDA agent network on startup, making it discoverable by other agents via the A2A protocol.

2. **Message handling** — Incoming messages (from other agents or users) are routed to `agent_logic()`, which either parses commands directly or sends them to Claude for tool-calling.

3. **Wallet operations** — The `radius_wallet.py` module handles all blockchain interaction: signing transactions locally with a private key, querying the Radius RPC, and interacting with the faucet.

4. **No external signer** — Unlike the [Wallet Concierge](https://github.com/radius-workshop/nanda-wallet-concierge) which uses a separate Privy signer service, this template signs locally. This is simpler but only suitable for testnet/hackathons.

## Talking to This Agent

From another NEST agent or any A2A client:

```python
import httpx

response = httpx.post("http://localhost:6000/a2a", json={
    "jsonrpc": "2.0",
    "method": "message/send",
    "id": "1",
    "params": {
        "message": {
            "parts": [{"kind": "text", "text": "What's my balance?"}],
            "messageId": "msg-1",
            "role": "user",
        }
    }
})
print(response.json())
```

## Deploy to Railway

1. Fork this repo
2. Create a new Railway project
3. Set environment variables (`RADIUS_PRIVATE_KEY`, optionally `ANTHROPIC_API_KEY`)
4. Deploy — Railway will build from the Dockerfile

## Alternatives

- **[Hermes Agent Template](https://github.com/radius-workshop/radius-hermes-railway-template)** — A different approach using the Hermes framework (Python + Bun). More features (Telegram, Linear, DID-Web) but more complex.
- **[Wallet Concierge](https://github.com/radius-workshop/nanda-wallet-concierge)** — Full-featured NEST agent with LangGraph, Privy signing, and Telegram bridge. Production-oriented but heavier.

## Production Notes

This template uses a **local private key** for signing. For production:

1. Switch to [Privy](https://privy.io/) embedded wallets for secure key management
2. Run the signer as a separate service (see Wallet Concierge architecture)
3. Set `NANDA_WALLET_PROVIDERS=privy` and configure Privy env vars
