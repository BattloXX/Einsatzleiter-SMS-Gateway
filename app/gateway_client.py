"""WebSocket-Client: verbindet sich mit der Einsatzleiter-Haupt-App,
empfängt SMS-Jobs und meldet Ergebnisse zurück.
"""
import asyncio
import json
import logging

import websockets
from websockets.exceptions import ConnectionClosed

from app.config import settings
from app.modem import send_sms
from app.protocol import (
    GATEWAY_ROLE,
    GATEWAY_VERSION,
    MSG_CONFIG,
    MSG_HELLO,
    MSG_PING,
    MSG_PONG,
    MSG_SMS_RESULT,
    MSG_SMS_SEND,
)

logger = logging.getLogger("sms-gateway.client")

# Aktuell aktiver Modem-Config-Override (aus server-seitiger 'config'-Nachricht)
_modem_config: dict | None = None


def _build_ws_url() -> str:
    scheme = "wss" if settings.GATEWAY_USE_TLS else "ws"
    return f"{scheme}://{settings.GATEWAY_DOMAIN}/ws/sms-gateway"


async def _handle_message(ws, raw: str) -> None:
    global _modem_config
    try:
        msg = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Ungültige JSON-Nachricht empfangen: %r", raw[:100])
        return

    msg_type = msg.get("type")

    if msg_type == MSG_PING:
        await ws.send(json.dumps({"type": MSG_PONG}))

    elif msg_type == MSG_CONFIG:
        _modem_config = msg.get("modem", {})
        logger.info("Modem-Konfiguration vom Server erhalten")

    elif msg_type == MSG_SMS_SEND:
        job_id = msg.get("id")
        to = msg.get("to", "")
        text = msg.get("text", "")
        logger.info("SMS-Job %s empfangen", job_id)
        ok, provider_response = await send_sms(to, text, _modem_config)
        result: dict = {"type": MSG_SMS_RESULT, "id": job_id, "ok": ok}
        if not ok:
            result["error"] = provider_response
        else:
            result["provider_response"] = provider_response
        await ws.send(json.dumps(result, ensure_ascii=False))

    else:
        logger.debug("Unbekannter Nachrichtentyp: %s", msg_type)


async def _heartbeat(ws) -> None:
    """Sendet regelmäßig Pings, damit die Verbindung als aktiv gilt."""
    while True:
        await asyncio.sleep(settings.HEARTBEAT_INTERVAL)
        try:
            await ws.send(json.dumps({"type": MSG_PING}))
        except Exception:
            return


async def run_once() -> None:
    """Stellt eine WS-Verbindung her, handelt auth + loop, bis die Verbindung bricht."""
    url = _build_ws_url()
    url_with_token = f"{url}?token={settings.GATEWAY_TOKEN}"

    logger.info("Verbinde mit %s", f"{'wss' if settings.GATEWAY_USE_TLS else 'ws'}://{settings.GATEWAY_DOMAIN}/ws/sms-gateway")

    async with websockets.connect(
        url_with_token,
        ping_interval=None,  # wir machen Heartbeat selbst
        open_timeout=15,
        close_timeout=5,
    ) as ws:
        # Beim Verbinden hello senden
        hello = {"type": MSG_HELLO, "role": GATEWAY_ROLE, "version": GATEWAY_VERSION}
        await ws.send(json.dumps(hello))
        logger.info("Verbunden — warte auf SMS-Jobs")

        heartbeat_task = asyncio.create_task(_heartbeat(ws))
        try:
            async for raw in ws:
                await _handle_message(ws, raw)
        except ConnectionClosed as exc:
            logger.warning("Verbindung getrennt: %s", exc)
        finally:
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass


async def run_forever(stop_event: asyncio.Event) -> None:
    """Reconnect-Loop mit exponentiellem Backoff."""
    delay = settings.RECONNECT_INITIAL_DELAY
    while not stop_event.is_set():
        try:
            await run_once()
        except Exception as exc:
            logger.error("Verbindungsfehler: %s: %s", type(exc).__name__, exc)

        if stop_event.is_set():
            break

        logger.info("Reconnect in %.0f s …", delay)
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=delay)
        except asyncio.TimeoutError:
            pass

        delay = min(delay * 2, settings.RECONNECT_MAX_DELAY)

    logger.info("Gateway-Client beendet")
