# ============================================================
# backend.py - Database Logic for Movie Booking System
# NEW: Per-seat tracking, seat locking, theatre layout,
#      and comprehensive input validation
# ============================================================

import sqlite3
import time
import re
from datetime import datetime

DB_NAME = "movie.db"
LOCK_TTL = 300   # 5 minutes


def get_connection():
    conn = sqlite3.connect(DB_NAME, timeout=10, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def initialize_database():
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id  INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role     TEXT NOT NULL DEFAULT 'user'
        )""")

    c.execute("""
        CREATE TABLE IF NOT EXISTS movies (
            movie_id     INTEGER PRIMARY KEY AUTOINCREMENT,
            movie_name   TEXT NOT NULL,
            release_date TEXT NOT NULL,
            director     TEXT NOT NULL,
            cast         TEXT NOT NULL,
            duration     INTEGER NOT NULL,
            rating       TEXT NOT NULL,
            ticket_price REAL NOT NULL,
            rows         INTEGER NOT NULL DEFAULT 8,
            cols         INTEGER NOT NULL DEFAULT 10
        )""")

    c.execute("""
        CREATE TABLE IF NOT EXISTS seats (
            seat_id    INTEGER PRIMARY KEY AUTOINCREMENT,
            movie_id   INTEGER NOT NULL,
            seat_label TEXT NOT NULL,
            status     TEXT NOT NULL DEFAULT 'available',
            UNIQUE(movie_id, seat_label),
            FOREIGN KEY(movie_id) REFERENCES movies(movie_id) ON DELETE CASCADE
        )""")

    c.execute("""
        CREATE TABLE IF NOT EXISTS seat_locks (
            lock_id    INTEGER PRIMARY KEY AUTOINCREMENT,
            movie_id   INTEGER NOT NULL,
            seat_label TEXT NOT NULL,
            user_id    INTEGER NOT NULL,
            locked_at  REAL NOT NULL,
            UNIQUE(movie_id, seat_label),
            FOREIGN KEY(movie_id) REFERENCES movies(movie_id) ON DELETE CASCADE
        )""")

    c.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            booking_id   INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id      INTEGER NOT NULL,
            movie_id     INTEGER NOT NULL,
            seat_labels  TEXT NOT NULL,
            seats        INTEGER NOT NULL,
            total_amount REAL NOT NULL,
            phone_number TEXT NOT NULL DEFAULT '',
            booking_date TEXT NOT NULL DEFAULT (DATE('now')),
            FOREIGN KEY(user_id)  REFERENCES users(user_id),
            FOREIGN KEY(movie_id) REFERENCES movies(movie_id)
        )""")

    # Migration: add phone_number column to existing databases
    try:
        c.execute("ALTER TABLE bookings ADD COLUMN phone_number TEXT NOT NULL DEFAULT ''")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # Column already exists

    for uname, pwd, role in [("admin", "admin123", "admin"), ("user1", "user123", "user")]:
        c.execute("SELECT 1 FROM users WHERE username=?", (uname,))
        if not c.fetchone():
            c.execute("INSERT INTO users(username,password,role) VALUES(?,?,?)",
                      (uname, pwd, role))

    conn.commit()
    conn.close()


# ─────────────────────────────────────────────
# VALIDATION HELPERS  (all return (bool, value_or_error))
# ─────────────────────────────────────────────

def validate_director_name(name: str):
    """Only letters, spaces, dots, hyphens and apostrophes allowed."""
    name = name.strip()
    if not name:
        return False, "Director name is required."
    if len(name) < 2:
        return False, "Director name must be at least 2 characters."
    if len(name) > 100:
        return False, "Director name must be under 100 characters."
    if not re.match(r"^[A-Za-z][A-Za-z\s.\-']{1,99}$", name):
        return False, (
            "Director name must contain only letters, spaces, dots, hyphens or apostrophes.\n"
            "Numbers and special characters (e.g. @, #, 1234) are not allowed."
        )
    return True, name


def validate_duration(duration_str: str):
    """Duration must be a positive integer representing minutes (e.g. 120)."""
    duration_str = duration_str.strip()
    if not duration_str:
        return False, "Duration (minutes) is required."
    if not re.match(r"^\d+$", duration_str):
        return False, (
            "Duration must be a whole number of minutes (e.g. 120).\n"
            "Text like 'ABCD' or '2h 30m' is not accepted — enter numbers only."
        )
    minutes = int(duration_str)
    if minutes < 1:
        return False, "Duration must be at least 1 minute."
    if minutes > 600:
        return False, "Duration cannot exceed 600 minutes (10 hours)."
    return True, minutes


def validate_release_date(date_str: str):
    """Must be DD-MM-YYYY and a real calendar date."""
    date_str = date_str.strip()
    if not date_str:
        return False, "Release date is required."
    if not re.match(r"^\d{2}-\d{2}-\d{4}$", date_str):
        return False, (
            "Release date must be in DD-MM-YYYY format.\n"
            "Example: 05-12-2024"
        )
    try:
        datetime.strptime(date_str, "%d-%m-%Y")
    except ValueError:
        return False, (
            f"'{date_str}' is not a valid calendar date.\n"
            "Check the day and month values (e.g. month 13 does not exist)."
        )
    return True, date_str


def validate_phone_number(phone: str):
    """10-digit Indian mobile number starting with 6-9."""
    phone = phone.strip()
    if not phone:
        return False, "Phone number is required for booking confirmation."
    if not re.match(r"^\d+$", phone):
        return False, (
            "Phone number must contain digits only.\n"
            "No spaces, dashes, + signs or letters are allowed."
        )
    if len(phone) != 10:
        return False, (
            f"Phone number must be exactly 10 digits "
            f"(you entered {len(phone)} digit{'s' if len(phone) != 1 else ''})."
        )
    if phone[0] not in "6789":
        return False, (
            "Phone number must start with 6, 7, 8 or 9 "
            "(valid Indian mobile number format)."
        )
    return True, phone


def validate_movie_name(name: str):
    name = name.strip()
    if not name:
        return False, "Movie name is required."
    if len(name) > 200:
        return False, "Movie name must be under 200 characters."
    return True, name


def validate_cast(cast: str):
    """
    Cast must contain only alphabets (A–Z, a–z) and spaces.
    Numbers, commas, dots, hyphens, and all other special characters are rejected.
    Empty input is also rejected.
    Multiple actor names should be separated by spaces only
    (e.g. "Prabhas Anushka Shetty").
    """
    cast = cast.strip()

    if not cast:
        return False, "Cast is required."

    if len(cast) > 500:
        return False, "Cast field must be under 500 characters."

    # Strictly only letters and spaces — nothing else
    if not re.fullmatch(r"[A-Za-z][A-Za-z ]*", cast):
        return False, (
            "Cast should contain only alphabets.\n"
            "Numbers and special characters are not allowed.\n"
            "Example: Prabhas Anushka Shetty"
        )

    return True, cast


def validate_rating(rating: str):
    rating = rating.strip()
    if not rating:
        return False, "Rating/Censor certificate is required."
    if not re.match(r"^(U|A|UA|U/A|S)(\s*\d+\+)?$", rating, re.IGNORECASE):
        return False, (
            "Rating must be a valid censor certificate: U, A, U/A, UA or S.\n"
            "Age qualifier is optional (e.g. U/A 16+, A 18+)."
        )
    return True, rating


def validate_price(price_str: str):
    price_str = price_str.strip()
    if not price_str:
        return False, "Ticket price is required."
    try:
        price = float(price_str)
    except ValueError:
        return False, "Ticket price must be a number (e.g. 250 or 299.50)."
    if price <= 0:
        return False, "Ticket price must be greater than ₹0."
    if price > 10000:
        return False, "Ticket price cannot exceed ₹10,000."
    return True, price


def validate_grid(rows_str: str, cols_str: str):
    errors = []
    rows = cols = None
    for val, label, lo, hi in [(rows_str, "Rows", 1, 26), (cols_str, "Columns", 1, 30)]:
        val = str(val).strip()
        if not val:
            errors.append(f"{label} is required.")
            continue
        if not re.match(r"^\d+$", val):
            errors.append(f"{label} must be a whole number.")
            continue
        n = int(val)
        if n < lo or n > hi:
            errors.append(f"{label} must be between {lo} and {hi}.")
            continue
        if label == "Rows":
            rows = n
        else:
            cols = n
    if errors:
        return False, "\n".join(errors), None, None
    return True, "", rows, cols


def validate_all_movie_fields(name, date, director, cast, duration, rating, price, rows, cols):
    """
    Run all movie-field validations at once.
    Returns (True, cleaned_dict) or (False, concatenated_error_string).
    """
    errors = []
    cleaned = {}

    for validator, raw, field_label, key in [
        (validate_movie_name,    name,     "Movie Name",    "name"),
        (validate_release_date,  date,     "Release Date",  "release_date"),
        (validate_director_name, director, "Director",      "director"),
        (validate_cast,          cast,     "Cast",          "cast"),
        (validate_duration,      duration, "Duration",      "duration"),
        (validate_rating,        rating,   "Rating",        "rating"),
        (validate_price,         price,    "Ticket Price",  "price"),
    ]:
        ok, val = validator(str(raw))
        if ok:
            cleaned[key] = val
        else:
            errors.append(f"• {field_label}: {val}")

    ok, msg, r, c = validate_grid(str(rows), str(cols))
    if ok:
        cleaned["rows"] = r
        cleaned["cols"] = c
    else:
        errors.append(f"• Seat Grid: {msg}")

    if errors:
        return False, "\n".join(errors)
    return True, cleaned


# ─────────────────────────────────────────────
# INTERNAL HELPERS
# ─────────────────────────────────────────────

def _expire_locks(cursor, movie_id):
    cutoff = time.time() - LOCK_TTL
    cursor.execute(
        "DELETE FROM seat_locks WHERE movie_id=? AND locked_at<?",
        (movie_id, cutoff))


def _create_seats_for_movie(cursor, movie_id, rows, cols):
    row_letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    for r in range(rows):
        for col in range(1, cols + 1):
            label = f"{row_letters[r]}{col}"
            cursor.execute(
                "INSERT OR IGNORE INTO seats(movie_id, seat_label) VALUES(?,?)",
                (movie_id, label))


# ─────────────────────────────────────────────
# USER OPERATIONS
# ─────────────────────────────────────────────

def login_user(username, password):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=? AND password=?",
              (username, password))
    user = c.fetchone()
    conn.close()
    return user


def register_user(username, password):
    if not username.strip() or not password.strip():
        return False, "Username and password cannot be empty."
    try:
        conn = get_connection()
        conn.execute("INSERT INTO users(username,password,role) VALUES(?,?,?)",
                     (username.strip(), password.strip(), "user"))
        conn.commit()
        conn.close()
        return True, "Registration successful!"
    except sqlite3.IntegrityError:
        return False, "Username already exists."


# ─────────────────────────────────────────────
# MOVIE OPERATIONS
# ─────────────────────────────────────────────

def add_movie(name, release_date, director, cast, duration, rating, price,
              rows=8, cols=10):
    ok, result = validate_all_movie_fields(
        name, release_date, director, cast,
        str(duration), rating, str(price), str(rows), str(cols))
    if not ok:
        return False, result

    d = result
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            INSERT INTO movies(movie_name,release_date,director,cast,
                               duration,rating,ticket_price,rows,cols)
            VALUES(?,?,?,?,?,?,?,?,?)""",
            (d["name"], d["release_date"], d["director"], d["cast"],
             d["duration"], d["rating"], d["price"], d["rows"], d["cols"]))
        movie_id = c.lastrowid
        _create_seats_for_movie(c, movie_id, d["rows"], d["cols"])
        conn.commit()
        conn.close()
        return True, "Movie added successfully!"
    except Exception as e:
        return False, str(e)


def delete_movie(movie_id):
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("DELETE FROM movies WHERE movie_id=?", (movie_id,))
        if c.rowcount == 0:
            conn.close()
            return False, "Movie not found."
        conn.commit()
        conn.close()
        return True, "Movie deleted successfully!"
    except Exception as e:
        return False, str(e)


def update_movie(movie_id, name, release_date, director, cast,
                 duration, rating, price, rows, cols):
    ok, result = validate_all_movie_fields(
        name, release_date, director, cast,
        str(duration), rating, str(price), str(rows), str(cols))
    if not ok:
        return False, result

    d = result
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            UPDATE movies SET movie_name=?,release_date=?,director=?,cast=?,
                              duration=?,rating=?,ticket_price=?,rows=?,cols=?
            WHERE movie_id=?""",
            (d["name"], d["release_date"], d["director"], d["cast"],
             d["duration"], d["rating"], d["price"], d["rows"], d["cols"], movie_id))
        if c.rowcount == 0:
            conn.close()
            return False, "Movie not found."
        conn.commit()
        conn.close()
        return True, "Movie updated successfully!"
    except Exception as e:
        return False, str(e)


def get_all_movies():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM movies")
    rows = c.fetchall()
    conn.close()
    return rows


def search_movies(keyword):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM movies WHERE LOWER(movie_name) LIKE ?",
              (f"%{keyword.lower()}%",))
    rows = c.fetchall()
    conn.close()
    return rows


def get_movie_by_id(movie_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM movies WHERE movie_id=?", (movie_id,))
    row = c.fetchone()
    conn.close()
    return row


def get_movie_stats(movie_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM seats WHERE movie_id=?", (movie_id,))
    total = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM seats WHERE movie_id=? AND status='booked'",
              (movie_id,))
    booked = c.fetchone()[0]
    conn.close()
    return total, booked, total - booked


# ─────────────────────────────────────────────
# SEAT OPERATIONS
# ─────────────────────────────────────────────

def get_seat_map(movie_id, current_user_id=None):
    conn = get_connection()
    c = conn.cursor()
    _expire_locks(c, movie_id)
    conn.commit()

    c.execute("SELECT seat_label, status FROM seats WHERE movie_id=? ORDER BY seat_label",
              (movie_id,))
    seat_rows = c.fetchall()

    c.execute("SELECT seat_label, user_id FROM seat_locks WHERE movie_id=?",
              (movie_id,))
    locks = {row["seat_label"]: row["user_id"] for row in c.fetchall()}
    conn.close()

    result = []
    for s in seat_rows:
        label = s["seat_label"]
        status = s["status"]
        if status == "available" and label in locks:
            if locks[label] == current_user_id:
                status = "locked_by_me"
            else:
                status = "locked_by_other"
        result.append({"label": label, "status": status})
    return result


def lock_seats(movie_id, seat_labels, user_id):
    conn = get_connection()
    c = conn.cursor()
    try:
        _expire_locks(c, movie_id)

        for label in seat_labels:
            c.execute("SELECT status FROM seats WHERE movie_id=? AND seat_label=?",
                      (movie_id, label))
            row = c.fetchone()
            if not row:
                raise ValueError(f"Seat {label} does not exist.")
            if row["status"] == "booked":
                raise ValueError(f"Seat {label} is already booked.")
            c.execute("""SELECT user_id FROM seat_locks
                         WHERE movie_id=? AND seat_label=?""", (movie_id, label))
            lock = c.fetchone()
            if lock and lock["user_id"] != user_id:
                raise ValueError(
                    f"Seat {label} is currently being selected by another user.\n"
                    "Please choose a different seat.")

        now = time.time()
        for label in seat_labels:
            c.execute("""
                INSERT INTO seat_locks(movie_id, seat_label, user_id, locked_at)
                VALUES(?,?,?,?)
                ON CONFLICT(movie_id, seat_label)
                DO UPDATE SET user_id=excluded.user_id, locked_at=excluded.locked_at
            """, (movie_id, label, user_id, now))

        conn.commit()
        return True, ""
    except ValueError as e:
        conn.rollback()
        return False, str(e)
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()


def release_locks(movie_id, user_id):
    conn = get_connection()
    conn.execute("DELETE FROM seat_locks WHERE movie_id=? AND user_id=?",
                 (movie_id, user_id))
    conn.commit()
    conn.close()


def confirm_booking(user_id, movie_id, seat_labels, phone_number):
    """
    Convert locked seats into a confirmed booking.
    phone_number is validated both here (backend safety net) and in the UI.
    Returns (True, booking_id, total_amount) or (False, msg, None).
    """
    ok, phone_or_err = validate_phone_number(phone_number)
    if not ok:
        return False, phone_or_err, None

    conn = get_connection()
    c = conn.cursor()
    try:
        _expire_locks(c, movie_id)

        for label in seat_labels:
            c.execute("""SELECT user_id FROM seat_locks
                         WHERE movie_id=? AND seat_label=?""",
                      (movie_id, label))
            lock = c.fetchone()
            if not lock or lock["user_id"] != user_id:
                raise ValueError(
                    f"Your hold on seat {label} has expired or was lost.\n"
                    "Please re-select your seats.")
            c.execute("SELECT status FROM seats WHERE movie_id=? AND seat_label=?",
                      (movie_id, label))
            row = c.fetchone()
            if not row or row["status"] == "booked":
                raise ValueError(f"Seat {label} is no longer available.")

        c.execute("SELECT ticket_price FROM movies WHERE movie_id=?", (movie_id,))
        movie = c.fetchone()
        if not movie:
            raise ValueError("Movie not found.")
        total = movie["ticket_price"] * len(seat_labels)

        for label in seat_labels:
            c.execute("UPDATE seats SET status='booked' WHERE movie_id=? AND seat_label=?",
                      (movie_id, label))

        for label in seat_labels:
            c.execute("DELETE FROM seat_locks WHERE movie_id=? AND seat_label=?",
                      (movie_id, label))

        c.execute("""
            INSERT INTO bookings(user_id, movie_id, seat_labels, seats, total_amount, phone_number)
            VALUES(?,?,?,?,?,?)""",
            (user_id, movie_id, ",".join(seat_labels), len(seat_labels), total, phone_or_err))
        booking_id = c.lastrowid

        conn.commit()
        return True, booking_id, total

    except ValueError as e:
        conn.rollback()
        return False, str(e), None
    except Exception as e:
        conn.rollback()
        return False, str(e), None
    finally:
        conn.close()


def send_sms_confirmation(phone_number, booking_id, movie_name, seat_labels, total):
    """
    Simulate an SMS confirmation. Swap in Twilio / MSG91 / AWS SNS for production.
    Returns (True, sms_text) always in simulation mode.
    """
    seats_str = ", ".join(seat_labels)
    sms_body = (
        f"[BookMyShow] Booking Confirmed!\n"
        f"ID: #{booking_id} | Movie: {movie_name}\n"
        f"Seats: {seats_str} | Total: Rs.{total:.2f}\n"
        f"Enjoy your show!"
    )
    # ── Production hook ──────────────────────────────────────
    # from twilio.rest import Client
    # client = Client(ACCOUNT_SID, AUTH_TOKEN)
    # client.messages.create(body=sms_body,
    #                        from_='+1XXXXXXXXXX',
    #                        to=f'+91{phone_number}')
    # ─────────────────────────────────────────────────────────
    print(f"[SMS SIM] +91{phone_number}\n{sms_body}\n")
    return True, sms_body


# ─────────────────────────────────────────────
# BOOKING OPERATIONS
# ─────────────────────────────────────────────

def cancel_booking(booking_id):
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM bookings WHERE booking_id=?", (booking_id,))
        booking = c.fetchone()
        if not booking:
            conn.close()
            return False, "Booking ID not found."

        labels = [l.strip() for l in booking["seat_labels"].split(",") if l.strip()]
        movie_id = booking["movie_id"]
        for label in labels:
            c.execute("UPDATE seats SET status='available' WHERE movie_id=? AND seat_label=?",
                      (movie_id, label))
        c.execute("DELETE FROM bookings WHERE booking_id=?", (booking_id,))
        conn.commit()
        conn.close()
        return True, f"Booking #{booking_id} cancelled. Seats {', '.join(labels)} are now available."
    except Exception as e:
        return False, str(e)


def get_user_bookings(user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT b.booking_id, m.movie_name, b.seat_labels,
               b.seats, b.total_amount, b.booking_date, b.phone_number
        FROM bookings b JOIN movies m ON b.movie_id=m.movie_id
        WHERE b.user_id=?
        ORDER BY b.booking_id DESC""", (user_id,))
    rows = c.fetchall()
    conn.close()
    return rows


def get_all_bookings():
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT b.booking_id, u.username, m.movie_name,
               b.seat_labels, b.seats, b.total_amount,
               b.booking_date, b.phone_number
        FROM bookings b
        JOIN users  u ON b.user_id =u.user_id
        JOIN movies m ON b.movie_id=m.movie_id
        ORDER BY b.booking_id DESC""")
    rows = c.fetchall()
    conn.close()
    return rows