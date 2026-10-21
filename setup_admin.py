#!/usr/bin/env python3
import base64
import getpass
import hashlib
import hmac
import json
import os
import secrets
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "admin_config.json"


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    iterations = 260_000
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return "pbkdf2_sha256${}${}${}".format(
        iterations,
        base64.urlsafe_b64encode(salt).decode("ascii"),
        base64.urlsafe_b64encode(digest).decode("ascii"),
    )


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt, digest = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        expected = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            base64.urlsafe_b64decode(salt.encode("ascii")),
            int(iterations),
        )
        return hmac.compare_digest(expected, base64.urlsafe_b64decode(digest.encode("ascii")))
    except (ValueError, TypeError):
        return False


def main() -> None:
    username = input("Admin username [admin]: ").strip() or "admin"
    password = getpass.getpass("Admin password: ")
    confirm = getpass.getpass("Repeat password: ")
    if not password or password != confirm:
        raise SystemExit("Passwords were empty or did not match.")

    config = {
        "username": username,
        "password_hash": hash_password(password),
        "session_secret": secrets.token_urlsafe(48),
        "host": "127.0.0.1",
        "port": 8021,
    }
    CONFIG.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.chmod(CONFIG, 0o600)
    print(f"Wrote {CONFIG}")


if __name__ == "__main__":
    main()
