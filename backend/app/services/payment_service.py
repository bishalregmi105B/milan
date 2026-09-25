import hashlib
import hmac
import logging
import uuid as uuid_module

from flask import current_app

logger = logging.getLogger(__name__)


class PaymentAdapter:
    provider: str = "base"

    def initiate(self, amount_npr: int, user) -> dict:
        raise NotImplementedError

    def verify_webhook(self, payload: dict, signature: str | None) -> bool:
        raise NotImplementedError


class EsewaAdapter(PaymentAdapter):
    """eSewa ePay v2: HMAC-SHA256 over a signed field string, base64-encoded."""

    provider = "esewa"

    @property
    def PRODUCT_CODE(self) -> str:
        # EPAYTEST is eSewa's sandbox product code; set ESEWA_MERCHANT_CODE in prod.
        return current_app.config.get("ESEWA_MERCHANT_CODE") or "EPAYTEST"

    def _signature_message(self, total_amount: int, transaction_uuid: str) -> str:
        return (
            f"total_amount={total_amount},transaction_uuid={transaction_uuid},"
            f"product_code={self.PRODUCT_CODE}"
        )

    def initiate(self, amount_npr: int, user) -> dict:
        import base64

        transaction_uuid = uuid_module.uuid4().hex
        message = self._signature_message(amount_npr, transaction_uuid)
        secret = (current_app.config.get("ESEWA_SECRET_KEY")
                  or current_app.config.get("SECRET_KEY", "")).encode()
        signature = base64.b64encode(
            hmac.new(secret, message.encode(), hashlib.sha256).digest()
        ).decode()
        return {
            "provider": self.provider,
            "redirect_url": "https://rc-epay.esewa.com.np/api/epay/main/v2/form",
            "params": {
                "amount": amount_npr,
                "tax_amount": 0,
                "total_amount": amount_npr,
                "transaction_uuid": transaction_uuid,
                "product_code": self.PRODUCT_CODE,
                "signature": signature,
                "signed_field_names": "total_amount,transaction_uuid,product_code",
            },
        }

    def verify_webhook(self, payload: dict, signature: str | None) -> bool:
        if not signature:
            return False
        import base64

        signed_fields = payload.get("signed_field_names", "")
        field_values = []
        for name in signed_fields.split(","):
            value = payload.get(name)
            if value is None:
                return False
            field_values.append(f"{name}={value}")
        message = ",".join(field_values)
        secret = (current_app.config.get("ESEWA_SECRET_KEY")
                  or current_app.config.get("SECRET_KEY", "")).encode()
        expected = base64.b64encode(
            hmac.new(secret, message.encode(), hashlib.sha256).digest()
        ).decode()
        return hmac.compare_digest(expected, signature)


class KhaltiAdapter(PaymentAdapter):
    provider = "khalti"

    def initiate(self, amount_npr: int, user) -> dict:
        return {
            "provider": self.provider,
            "checkout_url": "https://a.khalti.com/api/v2/epayment/initiate/",
            "amount_paisa": amount_npr * 100,
        }

    def verify_webhook(self, payload: dict, signature: str | None) -> bool:
        return _hmac_ok(payload, signature)


class FonepayAdapter(PaymentAdapter):
    provider = "fonepay"

    def initiate(self, amount_npr: int, user) -> dict:
        return {
            "provider": self.provider,
            "redirect_url": "https://fonepay.com/api/merchantRequest",
            "merchant_id": current_app.config.get("FONEPAY_MERCHANT_ID", ""),
        }

    def verify_webhook(self, payload: dict, signature: str | None) -> bool:
        return _hmac_ok(payload, signature)


class ConnectIpsAdapter(PaymentAdapter):
    provider = "connectips"

    def initiate(self, amount_npr: int, user) -> dict:
        return {
            "provider": self.provider,
            "redirect_url": "https://connectips.com.np/cipgateway",
            "merchant_id": current_app.config.get("CONNECTIPS_MERCHANT_ID", ""),
        }

    def verify_webhook(self, payload: dict, signature: str | None) -> bool:
        return _hmac_ok(payload, signature)


def _hmac_ok(payload: dict, signature: str | None) -> bool:
    secret = current_app.config.get("SECRET_KEY", "").encode()
    if not secret or not signature:
        logger.warning("webhook rejected: missing secret or signature")
        return False
    body = str(payload).encode()
    expected = hmac.new(secret, body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


ADAPTERS: dict[str, type[PaymentAdapter]] = {
    "esewa": EsewaAdapter,
    "khalti": KhaltiAdapter,
    "fonepay": FonepayAdapter,
    "connectips": ConnectIpsAdapter,
}


def get_adapter(provider: str) -> PaymentAdapter:
    adapter_cls = ADAPTERS.get(provider)
    if adapter_cls is None:
        raise ValueError(f"unsupported payment provider: {provider}")
    return adapter_cls()


SUBSCRIPTION_TIERS_NPR = {"basic": 299, "plus": 699, "premium": 1299}
