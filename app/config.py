"""Konfiguration aus Umgebungsvariablen."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Verbindung zur Haupt-App (wird dem Container mitgegeben)
    GATEWAY_DOMAIN: str  # z.B. "einsatzleiter.feuerwehr-wolfurt.at"
    GATEWAY_TOKEN: str   # smsgw_... Token aus app.cli create-sms-gateway-token
    GATEWAY_USE_TLS: bool = True  # False nur für lokale Entwicklung (ws:// statt wss://)

    # Reconnect
    RECONNECT_INITIAL_DELAY: float = 1.0   # Sekunden
    RECONNECT_MAX_DELAY: float = 30.0
    HEARTBEAT_INTERVAL: float = 20.0       # Ping-Intervall in Sekunden
    SMS_RESULT_TIMEOUT: float = 15.0       # Wie lange auf sms.result warten

    # Modem (CoNiuGo HTTP-Gateway – voll konfigurierbar)
    # Platzhalter: {to} = Empfängernummer (URL-encodiert), {text} = Nachricht (URL-encodiert)
    MODEM_URL: str = "http://192.168.1.1/cgi-bin/sendsms"
    MODEM_METHOD: str = "GET"   # GET oder POST
    # Für GET: Query-String-Template (ohne führendes '?')
    MODEM_QUERY: str = "nr={to}&text={text}"
    # Für POST: Body-Template (leer = kein Body, Query wird als Form-Body gesendet)
    MODEM_BODY: str = ""
    # Optional: Basic-Auth im Format "benutzer:passwort" (leer = keine Auth)
    MODEM_BASIC_AUTH: str = ""
    MODEM_TIMEOUT: float = 10.0
    MODEM_VERIFY_TLS: bool = True


settings = Settings()
