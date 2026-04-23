from fastapi import FastAPI, Request, Form, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import sqlite3
import os
import uuid
import hmac
import hashlib
import base64
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

SECRET_KEY = os.environ.get("SECRET_KEY", "lacupa-secret-key-2024")
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "lacupa2024")
DATA_DIR = Path("/data")
UPLOAD_DIR = DATA_DIR / "uploads"
DB_PATH = DATA_DIR / "booking.db"

DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

BASE_DIR = Path(__file__).parent
app = FastAPI()
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


# ── Database ──────────────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS tables (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            x REAL NOT NULL DEFAULT 50,
            y REAL NOT NULL DEFAULT 50,
            capacity INTEGER NOT NULL DEFAULT 4,
            max_duration_minutes INTEGER NOT NULL DEFAULT 120,
            shape TEXT NOT NULL DEFAULT 'circle'
        );
        CREATE TABLE IF NOT EXISTS reservations (
            id TEXT PRIMARY KEY,
            table_id TEXT NOT NULL,
            customer_name TEXT NOT NULL,
            customer_email TEXT NOT NULL,
            customer_phone TEXT DEFAULT '',
            guest_count INTEGER NOT NULL DEFAULT 2,
            start_datetime TEXT NOT NULL,
            end_datetime TEXT NOT NULL,
            notes TEXT DEFAULT '',
            status TEXT NOT NULL DEFAULT 'confirmed',
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        );
    """)
    conn.commit()
    conn.close()


init_db()


# ── Auth ──────────────────────────────────────────────────────────────────────

def make_token(username: str) -> str:
    expires = (datetime.utcnow() + timedelta(hours=8)).isoformat()
    payload = f"{username}|{expires}"
    sig = hmac.new(SECRET_KEY.encode(), payload.encode(), digestmod=hashlib.sha256).hexdigest()
    return base64.urlsafe_b64encode(f"{payload}|{sig}".encode()).decode()


def verify_token(token: str) -> Optional[str]:
    try:
        raw = base64.urlsafe_b64decode(token + "==").decode()
        parts = raw.split("|")
        if len(parts) != 3:
            return None
        username, expires, sig = parts
        payload = f"{username}|{expires}"
        expected = hmac.new(SECRET_KEY.encode(), payload.encode(), digestmod=hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        if datetime.fromisoformat(expires) < datetime.utcnow():
            return None
        return username
    except Exception:
        return None


def is_admin(request: Request) -> bool:
    token = request.cookies.get("admin_token")
    return bool(token and verify_token(token))


# ── Customer routes ───────────────────────────────────────────────────────────

@app.get("/booking", response_class=HTMLResponse)
async def booking_page(request: Request):
    db = get_db()
    fp = db.execute("SELECT value FROM settings WHERE key='floor_plan'").fetchone()
    db.close()
    floor_plan_url = f"/uploads/{fp['value']}" if fp else None
    return templates.TemplateResponse("booking.html", {
        "request": request,
        "floor_plan_url": floor_plan_url,
    })


@app.get("/booking/api/floor-plan")
async def api_floor_plan():
    db = get_db()
    fp = db.execute("SELECT value FROM settings WHERE key='floor_plan'").fetchone()
    tables = db.execute("SELECT * FROM tables").fetchall()
    db.close()
    return {
        "floor_plan_url": f"/uploads/{fp['value']}" if fp else None,
        "tables": [dict(t) for t in tables],
    }


@app.get("/booking/api/availability")
async def api_availability(date: str, start_time: str):
    try:
        start_dt = datetime.fromisoformat(f"{date}T{start_time}:00")
    except ValueError:
        raise HTTPException(400, "Invalid date/time")

    db = get_db()
    tables = db.execute("SELECT * FROM tables").fetchall()
    result = []
    for t in tables:
        end_dt = start_dt + timedelta(minutes=t["max_duration_minutes"])
        conflict = db.execute(
            "SELECT id FROM reservations WHERE table_id=? AND status='confirmed'"
            " AND start_datetime<? AND end_datetime>?",
            (t["id"], end_dt.isoformat(), start_dt.isoformat()),
        ).fetchone()
        td = dict(t)
        td["available"] = conflict is None
        result.append(td)
    db.close()
    return result


@app.post("/booking/api/reservations")
async def create_reservation(request: Request):
    data = await request.json()
    for field in ["table_id", "customer_name", "customer_email", "date", "start_time", "guest_count"]:
        if not data.get(field):
            raise HTTPException(400, f"Missing: {field}")

    db = get_db()
    table = db.execute("SELECT * FROM tables WHERE id=?", (data["table_id"],)).fetchone()
    if not table:
        db.close()
        raise HTTPException(404, "Table not found")

    start_dt = datetime.fromisoformat(f"{data['date']}T{data['start_time']}:00")
    end_dt = start_dt + timedelta(minutes=table["max_duration_minutes"])

    conflict = db.execute(
        "SELECT id FROM reservations WHERE table_id=? AND status='confirmed'"
        " AND start_datetime<? AND end_datetime>?",
        (data["table_id"], end_dt.isoformat(), start_dt.isoformat()),
    ).fetchone()
    if conflict:
        db.close()
        raise HTTPException(409, "Table not available")

    res_id = str(uuid.uuid4())
    db.execute(
        "INSERT INTO reservations VALUES (?,?,?,?,?,?,?,?,?,'confirmed',?)",
        (
            res_id, data["table_id"], data["customer_name"], data["customer_email"],
            data.get("customer_phone", ""), data["guest_count"],
            start_dt.isoformat(), end_dt.isoformat(),
            data.get("notes", ""), datetime.utcnow().isoformat(),
        ),
    )
    db.commit()
    db.close()
    return {"id": res_id, "end_time": end_dt.strftime("%H:%M")}


# ── Admin routes ──────────────────────────────────────────────────────────────

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str = None):
    if is_admin(request):
        return RedirectResponse("/admin", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request, "error": error})


@app.post("/login")
async def do_login(request: Request, username: str = Form(...), password: str = Form(...)):
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        token = make_token(username)
        resp = RedirectResponse("/admin", status_code=302)
        resp.set_cookie("admin_token", token, httponly=True, max_age=28800)
        return resp
    return templates.TemplateResponse("login.html", {
        "request": request,
        "error": "Falscher Benutzername oder Passwort",
    }, status_code=401)


@app.post("/admin/logout")
async def logout():
    resp = RedirectResponse("/login", status_code=302)
    resp.delete_cookie("admin_token")
    return resp


@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    if not is_admin(request):
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse("admin.html", {"request": request})


@app.post("/admin/api/floor-plan")
async def upload_floor_plan(request: Request, file: UploadFile = File(...)):
    if not is_admin(request):
        raise HTTPException(401)
    ext = Path(file.filename).suffix.lower()
    if ext not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        raise HTTPException(400, "Ungültiges Dateiformat")
    filename = f"floor-plan{ext}"
    with open(UPLOAD_DIR / filename, "wb") as f:
        shutil.copyfileobj(file.file, f)
    db = get_db()
    db.execute("INSERT OR REPLACE INTO settings(key,value) VALUES('floor_plan',?)", (filename,))
    db.commit()
    db.close()
    return {"url": f"/uploads/{filename}"}


@app.get("/admin/api/tables")
async def get_tables(request: Request):
    if not is_admin(request):
        raise HTTPException(401)
    db = get_db()
    rows = db.execute("SELECT * FROM tables").fetchall()
    db.close()
    return [dict(r) for r in rows]


@app.post("/admin/api/tables")
async def save_tables(request: Request):
    if not is_admin(request):
        raise HTTPException(401)
    tables = await request.json()
    db = get_db()
    db.execute("DELETE FROM tables")
    for t in tables:
        t.setdefault("id", str(uuid.uuid4()))
        db.execute(
            "INSERT OR REPLACE INTO tables(id,name,x,y,capacity,max_duration_minutes,shape)"
            " VALUES(:id,:name,:x,:y,:capacity,:max_duration_minutes,:shape)",
            t,
        )
    db.commit()
    db.close()
    return {"saved": len(tables)}


@app.get("/admin/api/reservations")
async def get_reservations(request: Request, date: str = None):
    if not is_admin(request):
        raise HTTPException(401)
    db = get_db()
    if date:
        rows = db.execute(
            "SELECT r.*, t.name as table_name FROM reservations r"
            " JOIN tables t ON r.table_id=t.id"
            " WHERE r.start_datetime LIKE ? ORDER BY r.start_datetime",
            (f"{date}%",),
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT r.*, t.name as table_name FROM reservations r"
            " JOIN tables t ON r.table_id=t.id"
            " ORDER BY r.start_datetime DESC LIMIT 200"
        ).fetchall()
    db.close()
    return [dict(r) for r in rows]


@app.put("/admin/api/reservations/{res_id}")
async def update_reservation(res_id: str, request: Request):
    if not is_admin(request):
        raise HTTPException(401)
    data = await request.json()
    db = get_db()
    db.execute("UPDATE reservations SET status=? WHERE id=?", (data["status"], res_id))
    db.commit()
    db.close()
    return {"ok": True}


@app.delete("/admin/api/reservations/{res_id}")
async def delete_reservation(res_id: str, request: Request):
    if not is_admin(request):
        raise HTTPException(401)
    db = get_db()
    db.execute("DELETE FROM reservations WHERE id=?", (res_id,))
    db.commit()
    db.close()
    return {"ok": True}
