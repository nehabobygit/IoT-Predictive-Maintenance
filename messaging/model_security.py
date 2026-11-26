
import hashlib
import os
import pickle
from pathlib import Path

EXPECTED_AI4I_SHA256 = (
    "1d5c3c5cb92ca85c3ac52d2385865c203a6013ab6a01691121c6f46791874ab1"
)


EXPECTED_IMPROVED_SHA256 = "7a001491e738e7a2a2cbe0f6ac47abe582b372cf0f57dc04cd41f4687624a957"


def checked_artifact(model_path, *, expected_default=False):
    model_path = Path(model_path)
    expected = EXPECTED_IMPROVED_SHA256 if model_path.name == "ai4i_improved.pkl" else EXPECTED_AI4I_SHA256
    env = "AI4I_IMPROVED_SHA256" if model_path.name == "ai4i_improved.pkl" else "AI4I_MODEL_SHA256"
    if not expected_default:
        expected = os.getenv(env, expected)
    payload = model_path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != expected.lower():
        raise ValueError("AI4I model integrity verification failed.")
    return payload


def verify_ai4i_model(model_path, *, expected_default=False):
    checked_artifact(model_path, expected_default=expected_default)
    return True


def load_verified_ai4i_model(model_path, model_dir):
    model_path = Path(model_path).resolve()
    if model_path.parent != Path(model_dir).resolve() or model_path.suffix.lower() != ".pkl":
        raise ValueError("AI4I models must be local .pkl files directly inside the configured models directory.")
    return pickle.loads(checked_artifact(model_path))
