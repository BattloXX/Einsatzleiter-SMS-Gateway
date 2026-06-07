# Einsatzleiter SMS-Gateway

Docker-Container, der sich mit dem [Einsatzleiter-Hilfswerkzeug](https://github.com/BattloXX/Einsatzleiter-Hilfswerkzeug)
verbindet und SMS über ein **CoNiuGo SMS Gateway LTE** (HTTP-Schnittstelle im LAN) versendet.

## Funktionsweise

Der Container läuft im **Netz des Modems** und verbindet sich **ausgehend** per WebSocket
zur Haupt-App — es wird kein eingehender Port am Modem-Standort benötigt.

- Verbindung bleibt persistent (nahezu live-Versand)
- Pro SMS: eigene HTTP-Verbindung zum Modem → Senden → sofort schließen (Modem wird nicht blockiert)
- Automatischer Reconnect mit exponentiellem Backoff bei Netzproblemen

## Voraussetzungen

- Docker + Docker Compose
- Netzwerkzugang zum CoNiuGo-Modem und zur Einsatzleiter-Haupt-App
- Ein gültiger Connection-Token aus der Haupt-App (siehe unten)

## Setup

### 1. Token in der Haupt-App erzeugen

Auf dem Server der Haupt-App:

```bash
python -m app.cli create-sms-gateway-token --label "Modem Wolfurt"
# Ausgabe: smsgw_xxxxxxxxxxxxxxxxxxxx
# → Diesen Token sicher notieren, er wird nur einmal angezeigt!
```

### 2. Container konfigurieren

```bash
cp .env.example .env
# .env öffnen und GATEWAY_DOMAIN, GATEWAY_TOKEN und MODEM_URL anpassen
```

Mindest-Konfiguration:

```env
GATEWAY_DOMAIN=einsatzleiter.feuerwehr-wolfurt.at
GATEWAY_TOKEN=smsgw_...
MODEM_URL=http://192.168.1.50/cgi-bin/sendsms
```

Alle verfügbaren Einstellungen sind in `.env.example` dokumentiert.

### 3. Container starten

```bash
docker compose up -d
docker compose logs -f
```

## Modem-Konfiguration

Der Container unterstützt jede CoNiuGo-HTTP-Variante über Platzhalter-Templates:

| Variable       | Beschreibung                                         | Standard                     |
|----------------|------------------------------------------------------|------------------------------|
| `MODEM_URL`    | URL des Modems                                       | `http://192.168.1.1/cgi-bin/sendsms` |
| `MODEM_METHOD` | `GET` oder `POST`                                    | `GET`                        |
| `MODEM_QUERY`  | Query-String-Template (`{to}`, `{text}`)             | `nr={to}&text={text}`        |
| `MODEM_BODY`   | Body-Template für POST (leer = Form-Data)            | *(leer)*                     |
| `MODEM_BASIC_AUTH` | HTTP Basic-Auth `benutzer:passwort` (optional)  | *(leer)*                     |
| `MODEM_TIMEOUT` | Timeout in Sekunden                                 | `10.0`                       |
| `MODEM_VERIFY_TLS` | TLS-Zertifikat des Modems prüfen                | `false`                      |

## Protokoll

Das WebSocket-Protokoll zwischen Container und Haupt-App ist in [PROTOCOL.md](PROTOCOL.md) dokumentiert.

## Geplante Erweiterungen

- SMS zur Telefonnummern-Verifizierung
- 2-Faktor-Authentifizierung per SMS
- Info-SMS-Versand
