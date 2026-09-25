import logging

import requests

from flask import current_app

logger = logging.getLogger(__name__)


def send_sms(to_phone: str, text: str) -> bool:
    """Sparrow SMS gateway (doc 1 §3.3). Dev mode logs when token unset."""
    token = current_app.config.get("SPARROW_SMS_TOKEN")
    from_addr = current_app.config.get("SPARROW_SMS_FROM", "Milan")
    if not token:
        if current_app.config.get("OTP_DEV_ECHO"):
            logger.info("SMS provider is not configured; local echo mode is enabled")
            return True
        logger.warning("SMS provider is not configured; refusing to send")
        return False
    try:
        resp = requests.post(
            "https://sms.sparrowsms.com/v2/sms",
            data={"token": token, "from": from_addr, "to": to_phone, "text": text},
            timeout=10,
        )
        return resp.status_code == 200
    except requests.RequestException:
        logger.exception("Sparrow SMS send failed")
        return False
