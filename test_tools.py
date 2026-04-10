from unittest.mock import MagicMock

from tools import run_tool


def test_send_sbc_passes_amount_without_float_coercion():
    wallet = MagicMock()
    wallet.send_sbc.return_value = "0xtx"
    wallet.wait_for_tx.return_value = {"status": "0x1"}
    wallet.tx_succeeded.return_value = True
    wallet.explorer_url.return_value = "https://example/tx/0xtx"

    result = run_tool(wallet, "send_sbc", to="0x" + "1" * 40, amount="0.0000009")

    wallet.send_sbc.assert_called_once_with("0x" + "1" * 40, "0.0000009")
    assert result["status"] == "success"
    assert result["tx_hash"] == "0xtx"


def test_request_faucet_wraps_response():
    wallet = MagicMock()
    wallet.request_faucet.return_value = {"tx_hash": "0xabc"}

    result = run_tool(wallet, "request_faucet")

    assert result == {"faucet": "requested", "response": {"tx_hash": "0xabc"}}


def test_unknown_tool_returns_error_dict():
    wallet = MagicMock()
    result = run_tool(wallet, "not_a_real_tool")
    assert "error" in result
