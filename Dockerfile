FROM python:3.12-slim

WORKDIR /srv/sms-gateway

# Abhängigkeiten zuerst (besseres Layer-Caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Anwendungscode
COPY app/ ./app/

# Non-root User für Sicherheit
RUN useradd --no-create-home --shell /bin/false gateway
USER gateway

CMD ["python", "-m", "app.main"]
