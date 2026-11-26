import os
from pathlib import Path


def configure_mqtt_auth(client, role):

    if role not in ("publisher", "consumer"):
        raise ValueError("Invalid MQTT client role")

    username = f"maintenance_{role}"
    password = os.getenv(
        f"MQTT_{role.upper()}_PASSWORD"
    )

    if not password:
        raise RuntimeError(
            f"MQTT_{role.upper()}_PASSWORD is not configured"
        )

    client.username_pw_set(username, password)

    # Enable TLS with certificate verification
    certificate = Path(os.getenv("MQTT_CERT_FILE", Path.home() / "mqtt_tls" / "server.crt"))

    if not certificate.is_file():
        raise FileNotFoundError(
            f"MQTT TLS certificate not found: {certificate}"
        )

    client.tls_set(ca_certs=str(certificate))

def broker_address():
    return os.getenv("MQTT_HOST", "localhost"), int(os.getenv("MQTT_PORT", "8883"))


def connect_configured(client, role, *, asynchronous=False):
    configure_mqtt_auth(client, role)
    client.connect_timeout = float(os.getenv("MQTT_CONNECT_TIMEOUT", "8"))
    client.reconnect_delay_set(min_delay=1, max_delay=15)
    host, port = broker_address()
    connect = client.connect_async if asynchronous else client.connect
    connect(host, port, keepalive=30)
