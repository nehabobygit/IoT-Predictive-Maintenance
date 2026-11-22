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
    certificate = Path.home() / "mqtt_tls" / "server.crt"

    if not certificate.is_file():
        raise FileNotFoundError(
            f"MQTT TLS certificate not found: {certificate}"
        )

    client.tls_set(ca_certs=str(certificate))