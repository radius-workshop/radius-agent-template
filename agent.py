#!/usr/bin/env python3
"""
Minimal NEST payment agent for the Radius network.

A forkable starting point: clone, set env vars, run. One service, local
signing, no complex dependencies. Uses the Anthropic SDK directly for
tool-calling (optional — works without an LLM via command routing too).

Usage:
    python agent.py
"""

import asyncio
import json
import os
import sys

from dotenv import load_dotenv

load_dotenv()

from nanda_core.core.adapter import NANDA
from radius_wallet import RadiusWallet
from tools import TOOLS, run_tool

# =============================================================================
# Configuration
# =============================================================================

AGENT_ID = os.environ.get("AGENT_ID", "radius-payment-agent")
PORT = int(os.environ.get("PORT", "6000"))

# Initialize wallet
private_key = os.environ.get("RADIUS_PRIVATE_KEY")
if not private_key:
    print("Error: RADIUS_PRIVATE_KEY is required. See .env.example.")
    sys.exit(1)

# Allow overriding RPC URL and chain ID via env vars (defaults to testnet)
rpc_url = os.environ.get("RADIUS_RPC_URL")
chain_id = os.environ.get("RADIUS_CHAIN_ID")

wallet_kwargs = {}
if rpc_url:
    wallet_kwargs["rpc_url"] = rpc_url
if chain_id:
    try:
        wallet_kwargs["chain_id"] = int(chain_id)
    except ValueError:
        print(f"Error: RADIUS_CHAIN_ID must be an integer, got: {chain_id!r}")
        sys.exit(1)

try:
    wallet = RadiusWallet(private_key, **wallet_kwargs)
except Exception as e:
    print(f"Error: Failed to initialize wallet — {e}")
    print("Check that RADIUS_PRIVATE_KEY is a valid hex-encoded private key.")
    sys.exit(1)

print(f"Wallet: {wallet.address}")

# Optional: Anthropic client for natural-language tool calling
anthropic_client = None
try:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if api_key:
        from anthropic import Anthropic

        anthropic_client = Anthropic(api_key=api_key)
        print("LLM: Claude enabled (natural language mode)")
    else:
        print("LLM: disabled (command routing mode). Set ANTHROPIC_API_KEY for natural language.")
except ImportError:
    print("LLM: anthropic package not installed. Using command routing mode.")


# =============================================================================
# Agent logic
# =============================================================================

def agent_logic(message: str, conversation_id: str) -> str:
    """Process an incoming message. Uses Claude tool-calling if available,
    otherwise falls back to simple command routing."""

    if anthropic_client:
        return _llm_handler(message)
    return _command_handler(message)


def _command_handler(message: str) -> str:
    """Simple command routing — no LLM needed.

    Commands:
        balance [address]           Check RUSD + SBC balances
        send <address> <amount>     Send SBC tokens
        status <tx_hash>            Check transaction status
        faucet                      Request testnet tokens
        info                        Chain info
        help                        Show available commands
    """
    parts = message.strip().split()
    if not parts:
        return "Send a command. Type 'help' for options."

    cmd = parts[0].lower()

    if cmd == "help":
        return (
            "Available commands:\n"
            "  balance [address]         Check RUSD + SBC balances\n"
            "  send <address> <amount>   Send SBC tokens\n"
            "  status <tx_hash>          Check transaction status\n"
            "  faucet                    Request testnet tokens\n"
            "  info                      Chain info\n"
            "  help                      Show this message"
        )

    if cmd == "balance":
        address = parts[1] if len(parts) > 1 else None
        result = run_tool(wallet, "check_balance", address=address)
        return _format_result(result)

    if cmd == "send":
        if len(parts) < 3:
            return "Usage: send <address> <amount>"
        result = run_tool(wallet, "send_sbc", to=parts[1], amount=parts[2])
        return _format_result(result)

    if cmd == "status":
        if len(parts) < 2:
            return "Usage: status <tx_hash>"
        result = run_tool(wallet, "tx_status", tx_hash=parts[1])
        return _format_result(result)

    if cmd == "faucet":
        result = run_tool(wallet, "request_faucet")
        return _format_result(result)

    if cmd == "info":
        result = run_tool(wallet, "chain_info")
        return _format_result(result)

    return f"Unknown command: {cmd}. Type 'help' for options."


def _llm_handler(message: str) -> str:
    """Use Claude to understand natural language and call tools."""
    tool_defs = [
        {
            "name": t["name"],
            "description": t["description"],
            "input_schema": t["input_schema"],
        }
        for t in TOOLS
    ]

    messages = [{"role": "user", "content": message}]

    system_prompt = (
        f"You are a Radius payment agent. Your wallet address is {wallet.address}. "
        "Use your tools to help the user check balances, send SBC tokens, check "
        "transaction status, and request faucet funds on the Radius network. "
        "Be concise."
    )

    response = anthropic_client.messages.create(
        model=os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514"),
        max_tokens=1024,
        system=system_prompt,
        tools=tool_defs,
        messages=messages,
    )

    # Handle tool use loop (Claude may call multiple tools)
    while response.stop_reason == "tool_use":
        tool_blocks = [b for b in response.content if b.type == "tool_use"]
        tool_results = []
        for block in tool_blocks:
            result = run_tool(wallet, block.name, **block.input)
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result) if isinstance(result, dict) else str(result),
                }
            )

        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})

        response = anthropic_client.messages.create(
            model=os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514"),
            max_tokens=1024,
            system=system_prompt,
            tools=tool_defs,
            messages=messages,
        )

    # Extract text response
    text_blocks = [b.text for b in response.content if hasattr(b, "text")]
    return "\n".join(text_blocks) if text_blocks else "Done."


def _format_result(result) -> str:
    if isinstance(result, dict):
        return json.dumps(result, indent=2)
    return str(result)


# =============================================================================
# Main
# =============================================================================

async def main():
    nanda = NANDA(
        agent_id=AGENT_ID,
        agent_logic=agent_logic,
        agent_name="Radius Payment Agent",
        domain="payments",
        specialization="wallet",
        description="Agent that can check balances, send SBC tokens, and interact with the Radius network",
        capabilities=["a2a", "payments"],
        port=PORT,
        registry_url=os.environ.get("NANDA_REGISTRY_URL"),
        public_url=os.environ.get("PUBLIC_URL"),
        host="0.0.0.0",
        enable_telemetry=True,
    )

    print("=" * 50)
    print("Radius Payment Agent")
    print("=" * 50)
    print(f"Agent ID:  {AGENT_ID}")
    print(f"Wallet:    {wallet.address}")
    print(f"Endpoint:  http://localhost:{PORT}/a2a")
    print(f"Mode:      {'LLM (natural language)' if anthropic_client else 'Command routing'}")
    print("=" * 50)

    await nanda.start()


if __name__ == "__main__":
    asyncio.run(main())
