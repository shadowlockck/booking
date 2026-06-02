import os, sqlite3, json
import bcrypt
from datetime import date, datetime
from contextlib import contextmanager

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "storage", "data")
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "booking.db")

ROLE_ADMIN  = "admin"
ROLE_OWNER  = "owner"
ROLE_GUEST  = "guest"

STATUS_PENDING   = "pending"
STATUS_CONFIRMED = "confirmed"
STATUS_CANCELLED = "cancelled"
STATUS_COMPLETED = "completed"

PAYMENT_PENDING  = "pending"
PAYMENT_PAID     = "paid"
PAYMENT_REFUNDED = "refunded"


@contextmanager
def _conn():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA foreign_keys=ON")
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))


def init_db() -> None:
    with _conn() as con:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                username  TEXT PRIMARY KEY,
                password  TEXT NOT NULL,
                role      TEXT NOT NULL DEFAULT 'guest',
                full_name TEXT DEFAULT '',
                email     TEXT DEFAULT '',
                phone     TEXT DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS listings (
                id              TEXT PRIMARY KEY,
                owner           TEXT NOT NULL,
                title           TEXT NOT NULL,
                city            TEXT NOT NULL,
                address         TEXT NOT NULL,
                property_type   TEXT NOT NULL,
                price_per_night REAL NOT NULL,
                max_guests      INTEGER NOT NULL,
                rooms           INTEGER NOT NULL DEFAULT 1,
                description     TEXT DEFAULT '',
                amenities       TEXT DEFAULT '[]',
                photos          TEXT DEFAULT '[]',
                is_active       INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY (owner) REFERENCES users(username)
            );
            CREATE TABLE IF NOT EXISTS bookings (
                id             TEXT PRIMARY KEY,
                listing_id     TEXT NOT NULL,
                guest_username TEXT NOT NULL,
                check_in       TEXT NOT NULL,
                check_out      TEXT NOT NULL,
                guests_count   INTEGER NOT NULL DEFAULT 1,
                total_price    REAL NOT NULL,
                status         TEXT NOT NULL DEFAULT 'pending',
                payment_status TEXT NOT NULL DEFAULT 'pending',
                created_at     TEXT NOT NULL,
                notes          TEXT DEFAULT '',
                FOREIGN KEY (listing_id)     REFERENCES listings(id),
                FOREIGN KEY (guest_username) REFERENCES users(username)
            );
        """)
        if not con.execute("SELECT 1 FROM users WHERE username='admin'").fetchone():
            con.execute(
                "INSERT INTO users(username,password,role,full_name,email) VALUES(?,?,?,?,?)",
                ("admin", hash_password("admin123"), ROLE_ADMIN, "Адміністратор", "admin@booking.ua"),
            )
        listing_columns = {r["name"] for r in con.execute("PRAGMA table_info(listings)")}
        if "photos" not in listing_columns:
            con.execute("ALTER TABLE listings ADD COLUMN photos TEXT DEFAULT '[]'")

init_db()


def _to_listing(row) -> dict:
    d = dict(row)
    d["amenities"]       = json.loads(d.get("amenities","[]"))
    d["photos"]          = json.loads(d.get("photos","[]") or "[]")
    d["is_active"]       = bool(d["is_active"])
    d["price_per_night"] = float(d["price_per_night"])
    d["max_guests"]      = int(d["max_guests"])
    d["rooms"]           = int(d["rooms"])
    return d

def _to_booking(row) -> dict:
    d = dict(row)
    d["total_price"]  = float(d["total_price"])
    d["guests_count"] = int(d["guests_count"])
    return d


def load_users() -> dict:
    with _conn() as con:
        rows = con.execute("SELECT * FROM users").fetchall()
    return {r["username"]: dict(r) for r in rows}

def get_user(username: str):
    with _conn() as con:
        row = con.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    return dict(row) if row else None

def user_exists(username: str) -> bool:
    with _conn() as con:
        return bool(con.execute("SELECT 1 FROM users WHERE username=?", (username,)).fetchone())

def add_user(username, password, role=ROLE_GUEST,
             full_name="", email="", phone="") -> None:
    with _conn() as con:
        con.execute(
            "INSERT INTO users(username,password,role,full_name,email,phone) VALUES(?,?,?,?,?,?)",
            (username, hash_password(password), role, full_name, email, phone),
        )

def update_user_role(username: str, new_role: str) -> None:
    with _conn() as con:
        con.execute("UPDATE users SET role=? WHERE username=?", (new_role, username))

def delete_user(username: str) -> None:
    with _conn() as con:
        con.execute("""
            DELETE FROM bookings 
            WHERE listing_id IN (SELECT id FROM listings WHERE owner = ?)
        """, (username,))
        
        con.execute("DELETE FROM listings WHERE owner = ?", (username,))
        
        con.execute("DELETE FROM bookings WHERE guest_username = ?", (username,))
        
        con.execute("DELETE FROM users WHERE username = ?", (username,))

def save_users(users: dict) -> None:
    with _conn() as con:
        existing = {r[0] for r in con.execute("SELECT username FROM users")}
        for uname in existing - set(users.keys()):
            con.execute("DELETE FROM bookings WHERE listing_id IN (SELECT id FROM listings WHERE owner = ?)", (uname,))
            con.execute("DELETE FROM listings WHERE owner = ?", (uname,))
            con.execute("DELETE FROM bookings WHERE guest_username = ?", (uname,))
            con.execute("DELETE FROM users WHERE username=?", (uname,))
            
        for uname, u in users.items():
            pwd = u.get("password", "")
            if pwd and not pwd.startswith("$2b$"):
                pwd = hash_password(pwd)
            con.execute("""
                INSERT INTO users(username,password,role,full_name,email,phone)
                VALUES(?,?,?,?,?,?)
                ON CONFLICT(username) DO UPDATE SET
                    password=excluded.password, role=excluded.role,
                    full_name=excluded.full_name, email=excluded.email, phone=excluded.phone
            """, (uname, pwd, u.get("role",ROLE_GUEST),
                  u.get("full_name",""), u.get("email",""), u.get("phone","")))


def load_listings() -> dict:
    with _conn() as con:
        rows = con.execute("SELECT * FROM listings").fetchall()
    return {r["id"]: _to_listing(r) for r in rows}

def save_listings(listings: dict) -> None:
    with _conn() as con:
        existing = {r[0] for r in con.execute("SELECT id FROM listings")}
        for lid in existing - set(listings.keys()):
            con.execute("DELETE FROM bookings WHERE listing_id=?", (lid,))
            con.execute("DELETE FROM listings WHERE id=?", (lid,))
            
        for lid, lst in listings.items():
            con.execute("""
                INSERT INTO listings(id,owner,title,city,address,property_type,
                    price_per_night,max_guests,rooms,description,amenities,photos,is_active)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET
                    owner=excluded.owner, title=excluded.title, city=excluded.city,
                    address=excluded.address, property_type=excluded.property_type,
                    price_per_night=excluded.price_per_night, max_guests=excluded.max_guests,
                    rooms=excluded.rooms, description=excluded.description,
                    amenities=excluded.amenities, photos=excluded.photos,
                    is_active=excluded.is_active
            """, (lid, lst.get("owner",""), lst.get("title",""), lst.get("city",""),
                  lst.get("address",""), lst.get("property_type",""),
                  float(lst.get("price_per_night",0)), int(lst.get("max_guests",1)),
                  int(lst.get("rooms",1)), lst.get("description",""),
                  json.dumps(lst.get("amenities",[]), ensure_ascii=False),
                  json.dumps(lst.get("photos",[]), ensure_ascii=False),
                  int(bool(lst.get("is_active",True)))))


def load_bookings() -> dict:
    with _conn() as con:
        rows = con.execute("SELECT * FROM bookings").fetchall()
    return {r["id"]: _to_booking(r) for r in rows}

def save_bookings(bookings: dict) -> None:
    with _conn() as con:
        existing = {r[0] for r in con.execute("SELECT id FROM bookings")}
        for bid in existing - set(bookings.keys()):
            con.execute("DELETE FROM bookings WHERE id=?", (bid,))
        for bid, b in bookings.items():
            con.execute("""
                INSERT INTO bookings(id,listing_id,guest_username,check_in,check_out,
                    guests_count,total_price,status,payment_status,created_at,notes)
                VALUES(?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET
                    status=excluded.status, payment_status=excluded.payment_status,
                    guests_count=excluded.guests_count, total_price=excluded.total_price,
                    notes=excluded.notes
            """, (bid, b.get("listing_id",""), b.get("guest_username",""),
                  b.get("check_in",""), b.get("check_out",""),
                  int(b.get("guests_count",1)), float(b.get("total_price",0)),
                  b.get("status",STATUS_PENDING), b.get("payment_status",PAYMENT_PENDING),
                  b.get("created_at", datetime.now().isoformat()), b.get("notes","")))

def add_booking(b: dict) -> None:
    with _conn() as con:
        con.execute("""
            INSERT INTO bookings(id,listing_id,guest_username,check_in,check_out,
                guests_count,total_price,status,payment_status,created_at,notes)
            VALUES(?,?,?,?,?,?,?,?,?,?,?)
        """, (b["id"], b["listing_id"], b["guest_username"],
              b["check_in"], b["check_out"], int(b["guests_count"]),
              float(b["total_price"]), b.get("status",STATUS_PENDING),
              b.get("payment_status",PAYMENT_PENDING),
              b.get("created_at", datetime.now().isoformat()), b.get("notes","")))

def update_booking_status(bid: str, status: str, payment_status: str | None = None) -> None:
    with _conn() as con:
        if payment_status is not None:
            con.execute("UPDATE bookings SET status=?,payment_status=? WHERE id=?",
                        (status, payment_status, bid))
        else:
            con.execute("UPDATE bookings SET status=? WHERE id=?", (status, bid))


def generate_id(prefix="") -> str:
    return f"{prefix}{int(datetime.now().timestamp()*1000)}"

def nights_between(check_in: str, check_out: str) -> int:
    return max(1, (date.fromisoformat(check_out) - date.fromisoformat(check_in)).days)

def is_listing_available(listing_id, check_in, check_out, bookings, exclude_id="") -> bool:
    in_  = date.fromisoformat(check_in)
    out_ = date.fromisoformat(check_out)
    for bid, b in bookings.items():
        if bid == exclude_id or b["listing_id"] != listing_id:
            continue
        if b["status"] == STATUS_CANCELLED:
            continue
        if not (out_ <= date.fromisoformat(b["check_in"]) or
                in_  >= date.fromisoformat(b["check_out"])):
            return False
    return True