"""SQLite persistence. Each ballot is atomic; classroom configurations are immutable."""
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from clustering import DEFAULT_POINTS, validate_config

APP_DIR = Path(__file__).resolve().parent


def data_dir():
    path = Path(os.environ.get("CLUSTERLAB_DATA_DIR", str(APP_DIR / "data")))
    path.mkdir(parents=True, exist_ok=True)
    return path


@contextmanager
def connect():
    db = sqlite3.connect(data_dir() / "classroom.sqlite3", timeout=15)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    try:
        with db:
            yield db
    finally:
        db.close()


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def initialize():
    with connect() as db:
        db.execute("PRAGMA journal_mode=WAL")
        db.executescript("""
        CREATE TABLE IF NOT EXISTS rooms (
          code TEXT PRIMARY KEY, title TEXT NOT NULL, k INTEGER NOT NULL,
          points TEXT NOT NULL, seeds TEXT NOT NULL, is_open INTEGER NOT NULL DEFAULT 1,
          created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS ballots (
          room_code TEXT NOT NULL REFERENCES rooms(code), student_id TEXT NOT NULL,
          salt TEXT NOT NULL, pin_hash TEXT NOT NULL, choices TEXT NOT NULL,
          submitted_at TEXT NOT NULL, updated_at TEXT NOT NULL,
          PRIMARY KEY(room_code, student_id));
        CREATE TABLE IF NOT EXISTS login_attempts (
          subject TEXT PRIMARY KEY, failures INTEGER NOT NULL, locked_until REAL NOT NULL);
        """)
        db.execute("INSERT OR IGNORE INTO rooms VALUES (?,?,?,?,?,?,?)",
                   ("DEMO", "The eight-point experiment", 3, json.dumps(DEFAULT_POINTS), "[0,3,6]", 1, now()))


def admin_password():
    configured = os.environ.get("ADMIN_PASSWORD")
    if configured:
        if len(configured) < 10:
            raise ValueError("ADMIN_PASSWORD must contain at least 10 characters.")
        return configured
    path = data_dir() / "admin-password.txt"
    try:
        with path.open("x", encoding="utf-8") as f:
            f.write(secrets.token_urlsafe(18))
    except FileExistsError:
        pass
    return path.read_text(encoding="utf-8").strip()


def verify_admin(password):
    import time
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT * FROM login_attempts WHERE subject='admin'").fetchone()
        if row and row["locked_until"] > time.time():
            return False, "Too many attempts. Try again in five minutes."
        if hmac.compare_digest(password.encode(), admin_password().encode()):
            db.execute("DELETE FROM login_attempts WHERE subject='admin'")
            return True, ""
        failures = (row["failures"] if row and row["locked_until"] == 0 else 0) + 1
        until = time.time() + 300 if failures >= 5 else 0
        db.execute("INSERT OR REPLACE INTO login_attempts VALUES ('admin',?,?)", (failures, until))
        return False, "Incorrect admin password." if not until else "Too many attempts. Try again in five minutes."


def decode_room(row):
    if not row:
        return None
    result = dict(row)
    result["points"] = json.loads(result["points"])
    result["seeds"] = json.loads(result["seeds"])
    return result


def get_room(code):
    with connect() as db:
        return decode_room(db.execute("SELECT * FROM rooms WHERE code=?", (code.strip().upper(),)).fetchone())


def rooms():
    with connect() as db:
        return [decode_room(r) for r in db.execute("SELECT * FROM rooms ORDER BY created_at DESC, code")]


def create_room(title, points, k, seeds):
    points = validate_config(points, k, seeds).tolist()
    title = title.strip()
    if not title or len(title) > 80:
        raise ValueError("Give the session a title between 1 and 80 characters.")
    with connect() as db:
        for _ in range(10):
            code = "".join(secrets.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(6))
            try:
                db.execute("INSERT INTO rooms VALUES (?,?,?,?,?,?,?)",
                           (code, title, k, json.dumps(points), json.dumps(seeds), 1, now()))
                return code
            except sqlite3.IntegrityError:
                continue
    raise RuntimeError("Couldn't allocate a session code. Please try again.")


def set_open(code, is_open):
    with connect() as db:
        db.execute("UPDATE rooms SET is_open=? WHERE code=?", (int(is_open), code))


def pin_digest(pin, salt):
    return hashlib.pbkdf2_hmac("sha256", pin.encode(), bytes.fromhex(salt), 180000).hex()


def submit_ballot(code, student_id, pin, choices):
    student_id = student_id.strip().casefold()
    if not student_id or len(student_id) > 40:
        raise ValueError("Enter a student code or nickname (1–40 characters).")
    if len(pin) < 6 or len(pin) > 128:
        raise ValueError("Use a private ballot password of 6–128 characters.")
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        room = decode_room(db.execute("SELECT * FROM rooms WHERE code=?", (code,)).fetchone())
        if not room or not room["is_open"]:
            raise ValueError("This session is closed. Your ballot was not saved.")
        if len(choices) != 8 or any(type(c) is not int or c not in range(room["k"]) for c in choices):
            raise ValueError("Assign all eight points to a cluster before submitting.")
        subject = f"ballot:{code}:{student_id}"
        import time
        attempt = db.execute("SELECT * FROM login_attempts WHERE subject=?", (subject,)).fetchone()
        if attempt and attempt["locked_until"] > time.time():
            raise ValueError("Too many password attempts for this student code. Try again in five minutes.")
        previous = db.execute("SELECT * FROM ballots WHERE room_code=? AND student_id=?", (code, student_id)).fetchone()
        if previous and not hmac.compare_digest(pin_digest(pin, previous["salt"]), previous["pin_hash"]):
            failures = (attempt["failures"] if attempt and attempt["locked_until"] == 0 else 0) + 1
            db.execute("INSERT OR REPLACE INTO login_attempts VALUES (?,?,?)",
                       (subject, failures, time.time() + 300 if failures >= 5 else 0))
            db.commit()
            raise ValueError("That student code already has a ballot. Use its original password to update it.")
        salt = previous["salt"] if previous else secrets.token_hex(16)
        stamp = now()
        db.execute("""INSERT INTO ballots VALUES (?,?,?,?,?,?,?)
          ON CONFLICT(room_code,student_id) DO UPDATE SET choices=excluded.choices,updated_at=excluded.updated_at""",
                   (code, student_id, salt, pin_digest(pin, salt), json.dumps(choices),
                    previous["submitted_at"] if previous else stamp, stamp))
        db.execute("DELETE FROM login_attempts WHERE subject=?", (subject,))
    return bool(previous)


def ballots(code):
    with connect() as db:
        rows = db.execute("SELECT student_id, choices, submitted_at, updated_at FROM ballots WHERE room_code=? ORDER BY updated_at DESC", (code,)).fetchall()
    return [{**dict(row), "choices": json.loads(row["choices"])} for row in rows]


def safe_csv(frame):
    """Neutralize spreadsheet formula prefixes in user-controlled text exports."""
    def safe(value):
        if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
            return "'" + value
        return value
    return frame.map(safe).to_csv(index=False).encode("utf-8-sig")
