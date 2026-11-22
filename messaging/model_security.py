
import hashlib
import os
from pathlib import Path

EXPECTED_AI4I_SHA256 = (
    "1d5c3c5cb92ca85c3ac52d2385865c203a6013ab6a01691121c6f46791874ab1"
)


def verify_ai4i_model(model_path):
    model_path = Path(model_path)

    if not model_path.is_file():
        raise FileNotFoundError(f"AI4I model not found: {model_path}")

    expected_hash = os.getenv(
        "AI4I_MODEL_SHA256",
        EXPECTED_AI4I_SHA256
    ).lower()

    digest = hashlib.sha256()

    with model_path.open("rb") as file:
        for chunk in iter(lambda: file.read(65536), b""):
            digest.update(chunk)

    if digest.hexdigest() != expected_hash:
        raise ValueError(
            "AI4I model integrity verification failed. "
            "The model file may have been modified."
        )

    return True
