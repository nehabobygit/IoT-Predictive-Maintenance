"""Dashboard identities and offline account administration."""
import argparse
from contextlib import closing
from getpass import getpass
import secrets
import sqlite3
import time

from werkzeug.security import generate_password_hash

ROLES = ("admin", "operator", "viewer")
LOGIN_WINDOW = 300
LOGIN_LIMIT = 8


def init_accounts(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS dashboard_users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK (role IN ('admin', 'operator', 'viewer'))
        )
    """)
    if conn.execute("SELECT 1 FROM sqlite_master WHERE name='dashboard_account'").fetchone():
        conn.execute("""
            INSERT OR IGNORE INTO dashboard_users
            SELECT username, password_hash, 'admin' FROM dashboard_account
        """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS dashboard_login_attempts (
            source TEXT PRIMARY KEY, started_at INTEGER NOT NULL, failures INTEGER NOT NULL
        )
    """)


def valid_credentials(username, password):
    return 1 <= len(username) <= 64 and 8 <= len(password) <= 128


def bootstrap(conn, username, password_hash):
    return conn.execute("""
        INSERT INTO dashboard_users (username, password_hash, role)
        SELECT ?, ?, 'admin' WHERE NOT EXISTS (SELECT 1 FROM dashboard_users)
    """, (username, password_hash)).rowcount


def reserve_login(conn, source):
    now = int(time.time())
    cutoff = now - LOGIN_WINDOW
    conn.execute("DELETE FROM dashboard_login_attempts WHERE started_at <= ?", (cutoff,))
    row = conn.execute("SELECT failures FROM dashboard_login_attempts WHERE source = ?", (source,)).fetchone()
    if row and row[0] >= LOGIN_LIMIT:
        return False
    conn.execute("""
        INSERT INTO dashboard_login_attempts VALUES (?, ?, 1)
        ON CONFLICT(source) DO UPDATE SET failures = failures + 1
    """, (source, now))
    return True


def authenticate_form(session, token):
    current = session.get("auth_csrf", "")
    return bool(current) and secrets.compare_digest(current.encode(), token.encode())


def main():
    from messaging.consumer import DB_PATH
    parser = argparse.ArgumentParser(description="Provision an individual dashboard user from the local host.")
    parser.add_argument("username")
    parser.add_argument("role", choices=ROLES)
    args = parser.parse_args()
    username = args.username.strip()
    password = getpass("Password: ")
    if not valid_credentials(username, password) or password != getpass("Confirm password: "):
        parser.error("Use a valid username and matching password of 8 to 128 characters.")
    with closing(sqlite3.connect(DB_PATH)) as conn, conn:
        init_accounts(conn)
        conn.execute("INSERT INTO dashboard_users VALUES (?, ?, ?)",
                     (username, generate_password_hash(password), args.role))
    print("Created", args.role, "account", username)


if __name__ == "__main__":
    main()
