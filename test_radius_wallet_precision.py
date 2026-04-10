import pytest

from radius_wallet import RadiusWallet, _to_wei


TEST_PRIVATE_KEY = "0x" + "ab" * 32
RECIPIENT = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"


@pytest.fixture
def wallet():
    return RadiusWallet(TEST_PRIVATE_KEY)


def test_to_wei_rejects_too_many_decimals():
    with pytest.raises(ValueError, match="more than 6 decimal places"):
        _to_wei("0.0000009", 6)


def test_send_sbc_rejects_zero_amount(wallet):
    with pytest.raises(ValueError, match="greater than zero"):
        wallet.send_sbc(RECIPIENT, 0)


def test_send_sbc_rejects_precision_overflow(wallet):
    with pytest.raises(ValueError, match="more than 6 decimal places"):
        wallet.send_sbc(RECIPIENT, "0.0000009")


def test_send_rusd_rejects_zero_amount(wallet):
    with pytest.raises(ValueError, match="greater than zero"):
        wallet.send_rusd(RECIPIENT, 0)
