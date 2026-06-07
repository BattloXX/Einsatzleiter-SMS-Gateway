# WebSocket-Protokoll: Einsatzleiter ↔ SMS-Gateway

## Verbindung

Der Container verbindet sich **ausgehend** zur Haupt-App:

```
wss://{GATEWAY_DOMAIN}/ws/sms-gateway?token={GATEWAY_TOKEN}
```

Zusätzlich wird der Token im HTTP-Header `Authorization: Bearer {token}` mitgeschickt.

Der Endpoint in der Haupt-App:
- prüft den Token gegen die DB-Tabelle `sms_gateway_token` (SHA256, aktiv?)
- aktualisiert `last_used_at`
- schließt mit Code `4401`, wenn der Token ungültig oder widerrufen ist

## Nachrichtenformat

Alle Nachrichten sind **JSON-Objekte** mit mindestens dem Feld `type`.

### Client → Server

#### `hello`
Wird direkt nach dem Verbindungsaufbau gesendet.

```json
{
  "type": "hello",
  "role": "sms-gateway",
  "version": "1.0"
}
```

#### `pong`
Antwort auf einen `ping` vom Server.

```json
{ "type": "pong" }
```

#### `sms.result`
Ergebnis eines SMS-Versands. Wird nach jedem `sms.send` gesendet.

```json
{
  "type": "sms.result",
  "id": "uuid-des-jobs",
  "ok": true,
  "provider_response": "OK"
}
```

Bei Fehler:

```json
{
  "type": "sms.result",
  "id": "uuid-des-jobs",
  "ok": false,
  "error": "HTTPError: 503"
}
```

---

### Server → Client

#### `ping`
Heartbeat vom Server (der Client antwortet mit `pong`).  
Der Client sendet auch selbst Pings alle ~20 s, um die Verbindung aktiv zu halten.

```json
{ "type": "ping" }
```

#### `config` _(optional)_
Überschreibt die ENV-seitigen Modem-Einstellungen. Kann bei Verbindungsaufbau oder
jederzeit danach gesendet werden.

```json
{
  "type": "config",
  "modem": {
    "modem_url": "http://192.168.x.x/cgi-bin/sendsms",
    "modem_method": "GET",
    "modem_query": "nr={to}&text={text}",
    "modem_body": "",
    "modem_basic_auth": "",
    "modem_timeout": 10.0,
    "modem_verify_tls": false
  }
}
```

Alle Felder im `modem`-Objekt sind optional; fehlende Felder fallen auf die
ENV-Konfiguration des Containers zurück.

#### `sms.send`
Sendeauftrag an den Gateway.

```json
{
  "type": "sms.send",
  "id": "uuid-des-jobs",
  "to": "+43664123456",
  "text": "Ihr Bestätigungscode: 123456"
}
```

`id` ist ein eindeutiger Job-Bezeichner (UUID empfohlen), der in `sms.result` gespiegelt
wird. Damit können mehrere parallele Jobs zugeordnet werden.

---

## Sequenzdiagramm (Normalfall)

```
Container                    Haupt-App
    |  WS-Verbindung + Token   |
    |------------------------->|  Handshake + Auth
    |                          |
    |-- hello ---------------->|
    |<-- config (optional) ----|
    |                          |
    |   (alle 20 s)            |
    |-- ping ----------------->|
    |<-- pong (oder umgekehrt) |
    |                          |
    |<-- sms.send (job) -------|
    |   [HTTP zum Modem]       |
    |-- sms.result ----------->|
    |                          |
```

## Fehlerbehandlung

| Situation                    | Verhalten Container              |
|------------------------------|----------------------------------|
| Token ungültig               | Server schließt mit Code 4401; Container reconnectet mit Backoff |
| Netzabbruch                  | Reconnect-Loop (1 s → max 30 s) |
| Modem antwortet mit Fehler   | `sms.result { ok: false, error }` wird gesendet |
| Modem nicht erreichbar       | `sms.result { ok: false, error }` wird gesendet |
| SMS-Result-Timeout           | Server markiert Job als fehlgeschlagen |
