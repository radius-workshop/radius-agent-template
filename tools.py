"""
Tool definitions for the Radius Payment Agent.

Each tool wraps a RadiusWallet operation and exposes it in Anthropic's
tool-calling schema. Tools work with both the LLM handler and the
command router.
"""

from __future__ import annotations

from radius_wallet import RadiusWallet

# Tool definitions (Anthropic tool-calling format)
TOOLS = [
    {
        "name": "check_balance",
        "description": "Check RUSD (native) and SBC (ERC-20) balances for a wallet address. If no address provided, checks the agent's own wallet.",
        "input_schema": {
            "type": "object",
            "properties": {
                "address": {
                    "type": "string",
                    "description": "Wallet address to check. Omit to check the agent's own wallet.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "send_sbc",
        "description": "Send SBC tokens to a wallet address on Radius. Amount is in human-readable units (e.g. '1.5' for 1.5 SBC).",
        "input_schema": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Recipient wallet address."},
                "amount": {"type": "string", "description": "Amount of SBC to send (e.g. '0.1')."},
            },
            "required": ["to", "amount"],
        },
    },
    {
        "name": "tx_status",
        "description": "Check the status of a transaction by its hash.",
        "input_schema": {
            "type": "object",
            "properties": {
                "tx_hash": {"type": "string", "description": "Transaction hash to look up."},
            },
            "required": ["tx_hash"],
        },
    },
    {
        "name": "request_faucet",
        "description": "Request testnet SBC tokens from the Radius faucet.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "chain_info",
        "description": "Get Radius chain information: chain ID, block number, and gas price.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
]


def run_tool(wallet: RadiusWallet, tool_name: str, **kwargs) -> dict | str:
    """Execute a tool by name. Returns a dict or string result.

    All tool operations are wrapped in try/except so that RPC errors,
    insufficient balances, network timeouts, etc. produce an error dict
    instead of crashing the agent.
    """

    if tool_name == "check_balance":
        try:
            return wallet.get_balances(kwargs.get("address"))
        except Exception as e:
            return {"error": f"Failed to check balance: {e}"}

    if tool_name == "send_sbc":
        try:
            to = kwargs["to"]
            amount = kwargs["amount"]
            tx_hash = wallet.send_sbc(to, amount)
            receipt = wallet.wait_for_tx(tx_hash)
            return {
                "tx_hash": tx_hash,
                "status": "success" if wallet.tx_succeeded(receipt) else "failed",
                "explorer": wallet.explorer_url(tx_hash),
            }
        except (ValueError, KeyError) as e:
            return {"error": f"Invalid parameters: {e}"}
        except Exception as e:
            return {"error": f"Failed to send SBC: {e}"}

    if tool_name == "tx_status":
        try:
            receipt = wallet.get_tx_receipt(kwargs["tx_hash"])
            if receipt is None:
                return {"tx_hash": kwargs["tx_hash"], "status": "pending"}
            status_hex = str(receipt.get("status", "0x0")).lower()
            return {
                "tx_hash": kwargs["tx_hash"],
                "status": "success" if status_hex == "0x1" else "failed",
                "block": receipt.get("blockNumber"),
                "gas_used": receipt.get("gasUsed"),
                "explorer": wallet.explorer_url(kwargs["tx_hash"]),
            }
        except Exception as e:
            return {"error": f"Failed to check transaction status: {e}"}

    if tool_name == "request_faucet":
        try:
            result = wallet.request_faucet()
            return {"faucet": "requested", "response": result}
        except Exception as e:
            return {"error": f"Faucet request failed: {e}"}

    if tool_name == "chain_info":
        try:
            return wallet.get_chain_info()
        except Exception as e:
            return {"error": f"Failed to get chain info: {e}"}

    return {"error": f"Unknown tool: {tool_name}"}
