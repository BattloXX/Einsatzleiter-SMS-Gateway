"""SMS-Versand über das CoNiuGo HTTP-Gateway.

Pro SMS wird eine eigene HTTP-Verbindung geöffnet und danach sofort wieder
geschlossen, damit das Modem nicht blockiert wird.
"""
import logging
from urllib.parse import quote_plus

import httpx

from app.config import settings

logger = logging.getLogger("sms-gateway.modem")


def _render(template: str, to: str, text: str) -> str:
    return template.replace("{to}", quote_plus(to)).replace("{text}", quote_plus(text))


async def send_sms(to: str, text: str, modem_config: dict | None = None) -> tuple[bool, str]:
    """Sendet eine SMS über das Modem.

    modem_config: optionales Dict aus der server-seitigen 'config'-Nachricht,
                  das die ENV-Einstellungen überschreiben kann.
    Rückgabe: (ok, provider_response_oder_fehlermeldung)
    """
    cfg = modem_config or {}
    url = cfg.get("modem_url", settings.MODEM_URL)
    method = cfg.get("modem_method", settings.MODEM_METHOD).upper()
    query_tpl = cfg.get("modem_query", settings.MODEM_QUERY)
    body_tpl = cfg.get("modem_body", settings.MODEM_BODY)
    basic_auth_raw = cfg.get("modem_basic_auth", settings.MODEM_BASIC_AUTH)
    timeout = float(cfg.get("modem_timeout", settings.MODEM_TIMEOUT))
    verify = cfg.get("modem_verify_tls", settings.MODEM_VERIFY_TLS)

    auth = None
    if basic_auth_raw:
        user, _, pw = basic_auth_raw.partition(":")
        auth = (user, pw)

    headers = {"Connection": "close"}

    try:
        async with httpx.AsyncClient(
            auth=auth,
            headers=headers,
            timeout=timeout,
            verify=verify,
        ) as client:
            if method == "GET":
                query_str = _render(query_tpl, to, text)
                sep = "&" if "?" in url else "?"
                full_url = url + sep + query_str
                resp = await client.get(full_url)
            else:
                if body_tpl:
                    body = _render(body_tpl, to, text)
                    resp = await client.post(url, content=body.encode(),
                                             headers={"Content-Type": "application/x-www-form-urlencoded",
                                                      "Connection": "close"})
                else:
                    form_data = {"nr": to, "text": text}
                    resp = await client.post(url, data=form_data)

        ok = resp.status_code < 300
        response_text = resp.text[:200]
        if ok:
            logger.info("SMS an %s versendet (HTTP %s)", _mask(to), resp.status_code)
        else:
            logger.warning("Modem antwortete HTTP %s für %s: %s", resp.status_code, _mask(to), response_text)
        return ok, response_text

    except Exception as exc:
        msg = f"{type(exc).__name__}: {exc}"
        logger.error("Modem-Fehler bei Versand an %s: %s", _mask(to), msg)
        return False, msg


def _mask(number: str) -> str:
    """Maskiert Telefonnummern für Logs (letzte 4 Ziffern sichtbar)."""
    digits = "".join(c for c in number if c.isdigit())
    if len(digits) >= 6:
        return "*" * (len(number) - 4) + number[-4:]
    return "****"
