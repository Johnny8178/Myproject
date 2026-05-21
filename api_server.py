from datetime import datetime, timedelta
from functools import wraps
import hashlib
import os
import re
import traceback
import uuid

import duckdb
from flask import Flask, jsonify, request, send_file

from analyzer import HongduAnalyzer


app = Flask(__name__)
DB_PATH = "hongdu_analysis.db"
OUTPUT_DIR = "output"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, DB_PATH)
OUTPUT_PATH = os.path.join(BASE_DIR, OUTPUT_DIR)
TOKEN_DAYS = 7
PHONE_REGEX = re.compile(r"^1[3-9]\d{9}$")
PASSWORD_REGEX = re.compile(r"^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{8,}$")


def _db_conn():
    return duckdb.connect(DB_FILE)


def _to_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _norm_symbol(symbol):
    return str(symbol or "").strip()


def _hash_text(text):
    return hashlib.sha256(str(text).encode("utf-8")).hexdigest()


def _password_ok(password, allow_admin=False):
    if allow_admin and password == "admin":
        return True
    return bool(PASSWORD_REGEX.match(password or ""))


def init_tables():
    con = _db_conn()
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            phone TEXT UNIQUE,
            password_hash TEXT,
            role TEXT,
            status TEXT,
            created_at TIMESTAMP,
            last_login_at TIMESTAMP
        );
        """
    )
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS user_sessions (
            session_id TEXT PRIMARY KEY,
            user_id TEXT,
            token_hash TEXT,
            expires_at TIMESTAMP,
            created_at TIMESTAMP,
            ip TEXT,
            user_agent TEXT
        );
        """
    )
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_logs (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            action TEXT,
            target_type TEXT,
            target_id TEXT,
            detail_json TEXT,
            created_at TIMESTAMP,
            ip TEXT
        );
        """
    )
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS trade_records (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            symbol TEXT,
            stock_name TEXT,
            side TEXT,
            quantity BIGINT,
            price DOUBLE,
            amount DOUBLE,
            note TEXT,
            created_at TIMESTAMP
        );
        """
    )
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS portfolio_accounts (
            account_id TEXT PRIMARY KEY,
            owner_user_id TEXT,
            available_cash DOUBLE DEFAULT 0,
            updated_at TIMESTAMP
        );
        """
    )
    account_cols = {row[1] for row in con.execute("PRAGMA table_info('portfolio_accounts')").fetchall()}
    if "owner_user_id" not in account_cols:
        con.execute("ALTER TABLE portfolio_accounts ADD COLUMN owner_user_id TEXT")
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS portfolio_positions (
            account_id TEXT,
            owner_user_id TEXT,
            symbol TEXT,
            stock_name TEXT,
            quantity BIGINT,
            avg_cost DOUBLE,
            stop_loss DOUBLE,
            target_price DOUBLE,
            grid_step_pct DOUBLE,
            grid_buy_shares BIGINT,
            grid_sell_shares BIGINT,
            max_layers INTEGER,
            base_price_mode TEXT,
            cash_reserve_pct DOUBLE,
            position_cap_shares BIGINT,
            updated_at TIMESTAMP,
            PRIMARY KEY (account_id, symbol)
        );
        """
    )
    cols = {row[1] for row in con.execute("PRAGMA table_info('portfolio_positions')").fetchall()}
    migrate = [
        ("owner_user_id", "TEXT"),
        ("grid_step_pct", "DOUBLE DEFAULT 2"),
        ("grid_buy_shares", "BIGINT DEFAULT 100"),
        ("grid_sell_shares", "BIGINT DEFAULT 100"),
        ("max_layers", "INTEGER DEFAULT 6"),
        ("base_price_mode", "TEXT DEFAULT 'current'"),
        ("cash_reserve_pct", "DOUBLE DEFAULT 20"),
        ("position_cap_shares", "BIGINT DEFAULT 100000"),
    ]
    for name, sql_type in migrate:
        if name not in cols:
            con.execute(f"ALTER TABLE portfolio_positions ADD COLUMN {name} {sql_type}")
    _ensure_admin(con)
    con.close()


def _ensure_admin(con):
    row = con.execute("SELECT id FROM users WHERE role='admin' LIMIT 1").fetchone()
    if row:
        return
    now = datetime.now()
    con.execute(
        "INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?)",
        ["u_admin", "admin", _hash_text("admin"), "admin", "active", now, None],
    )


def _audit(user_id, action, target_type="", target_id="", detail=""):
    con = _db_conn()
    con.execute(
        "INSERT INTO audit_logs VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [
            str(uuid.uuid4()),
            user_id or "",
            action,
            target_type,
            target_id,
            str(detail)[:4000],
            datetime.now(),
            request.remote_addr if request else "",
        ],
    )
    con.close()


def _get_token():
    auth = request.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        return auth.split(" ", 1)[1].strip()
    return ""


def _get_user_by_token(token):
    if not token:
        return None
    con = _db_conn()
    now = datetime.now()
    row = con.execute(
        """
        SELECT u.id, u.phone, u.role, u.status
        FROM user_sessions s
        JOIN users u ON u.id = s.user_id
        WHERE s.token_hash = ? AND s.expires_at > ?
        """,
        [_hash_text(token), now],
    ).fetchone()
    con.close()
    if not row:
        return None
    if row[3] != "active":
        return None
    return {"id": row[0], "phone": row[1], "role": row[2], "status": row[3]}


def require_auth(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = _get_user_by_token(_get_token())
        if not user:
            return jsonify({"error": "unauthorized"}), 401
        request.current_user = user
        return fn(*args, **kwargs)

    return wrapper


def require_admin(fn):
    @wraps(fn)
    @require_auth
    def wrapper(*args, **kwargs):
        if request.current_user.get("role") != "admin":
            return jsonify({"error": "forbidden"}), 403
        return fn(*args, **kwargs)

    return wrapper


def _clean_position_item(item):
    symbol = _norm_symbol(item.get("symbol"))
    if not symbol:
        return None
    return {
        "symbol": symbol,
        "stock_name": str(item.get("stock_name", "")).strip(),
        "quantity": max(0, _to_int(item.get("quantity", 0), 0)),
        "avg_cost": max(0.0, _to_float(item.get("avg_cost", 0), 0.0)),
        "stop_loss": max(0.0, _to_float(item.get("stop_loss", 0), 0.0)),
        "target_price": max(0.0, _to_float(item.get("target_price", 0), 0.0)),
        "grid_step_pct": max(0.2, _to_float(item.get("grid_step_pct", 2), 2.0)),
        "grid_buy_shares": max(1, _to_int(item.get("grid_buy_shares", 100), 100)),
        "grid_sell_shares": max(1, _to_int(item.get("grid_sell_shares", 100), 100)),
        "max_layers": max(1, min(20, _to_int(item.get("max_layers", 6), 6))),
        "base_price_mode": str(item.get("base_price_mode", "current")).strip().lower() or "current",
        "cash_reserve_pct": min(90.0, max(0.0, _to_float(item.get("cash_reserve_pct", 20), 20.0))),
        "position_cap_shares": max(1, _to_int(item.get("position_cap_shares", 100000), 100000)),
    }


def _upsert_position_row(con, account_id, owner_user_id, item):
    now = datetime.now()
    con.execute(
        """
        INSERT INTO portfolio_positions (
            account_id, owner_user_id, symbol, stock_name, quantity, avg_cost, stop_loss, target_price,
            grid_step_pct, grid_buy_shares, grid_sell_shares, max_layers, base_price_mode,
            cash_reserve_pct, position_cap_shares, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(account_id, symbol) DO UPDATE SET
            owner_user_id=excluded.owner_user_id,
            stock_name=excluded.stock_name,
            quantity=excluded.quantity,
            avg_cost=excluded.avg_cost,
            stop_loss=excluded.stop_loss,
            target_price=excluded.target_price,
            grid_step_pct=excluded.grid_step_pct,
            grid_buy_shares=excluded.grid_buy_shares,
            grid_sell_shares=excluded.grid_sell_shares,
            max_layers=excluded.max_layers,
            base_price_mode=excluded.base_price_mode,
            cash_reserve_pct=excluded.cash_reserve_pct,
            position_cap_shares=excluded.position_cap_shares,
            updated_at=excluded.updated_at
        """,
        [
            account_id,
            owner_user_id,
            item["symbol"],
            item["stock_name"],
            item["quantity"],
            item["avg_cost"],
            item["stop_loss"],
            item["target_price"],
            item["grid_step_pct"],
            item["grid_buy_shares"],
            item["grid_sell_shares"],
            item["max_layers"],
            item["base_price_mode"],
            item["cash_reserve_pct"],
            item["position_cap_shares"],
            now,
        ],
    )


def replace_positions(owner_user_id, account_id, available_cash, positions):
    con = _db_conn()
    now = datetime.now()
    con.execute(
        "INSERT INTO portfolio_accounts (account_id, owner_user_id, available_cash, updated_at) VALUES (?, ?, ?, ?) "
        "ON CONFLICT(account_id) DO UPDATE SET owner_user_id=excluded.owner_user_id, available_cash=excluded.available_cash, updated_at=excluded.updated_at",
        [account_id, owner_user_id, _to_float(available_cash, 0.0), now],
    )
    cleaned = []
    for p in positions:
        row = _clean_position_item(p)
        if row:
            cleaned.append(row)

    con.execute("BEGIN TRANSACTION")
    con.execute("DELETE FROM portfolio_positions WHERE account_id = ? AND owner_user_id = ?", [account_id, owner_user_id])
    for item in cleaned:
        _upsert_position_row(con, account_id, owner_user_id, item)
    con.execute("COMMIT")
    con.close()
    return cleaned


def load_positions(owner_user_id, account_id):
    con = _db_conn()
    account = con.execute(
        "SELECT account_id, available_cash, updated_at FROM portfolio_accounts WHERE account_id = ? AND owner_user_id = ?",
        [account_id, owner_user_id],
    ).fetchone()
    rows = con.execute(
        """
        SELECT symbol, stock_name, quantity, avg_cost, stop_loss, target_price,
               grid_step_pct, grid_buy_shares, grid_sell_shares, max_layers,
               base_price_mode, cash_reserve_pct, position_cap_shares, updated_at
        FROM portfolio_positions
        WHERE account_id = ? AND owner_user_id = ?
        ORDER BY symbol
        """,
        [account_id, owner_user_id],
    ).fetchall()
    con.close()
    positions = []
    for row in rows:
        positions.append(
            {
                "symbol": row[0],
                "stock_name": row[1] or "",
                "quantity": int(row[2] or 0),
                "avg_cost": float(row[3] or 0.0),
                "stop_loss": float(row[4] or 0.0),
                "target_price": float(row[5] or 0.0),
                "grid_step_pct": float(row[6] or 2.0),
                "grid_buy_shares": int(row[7] or 100),
                "grid_sell_shares": int(row[8] or 100),
                "max_layers": int(row[9] or 6),
                "base_price_mode": row[10] or "current",
                "cash_reserve_pct": float(row[11] or 20.0),
                "position_cap_shares": int(row[12] or 100000),
                "updated_at": str(row[13]) if row[13] else "",
            }
        )
    return {
        "account_id": account[0] if account else account_id,
        "available_cash": float(account[1]) if account else 0.0,
        "updated_at": str(account[2]) if account else "",
        "positions": positions,
    }


def build_grid_advice(metrics, position, available_cash):
    grid_step_pct = max(0.2, _to_float(position.get("grid_step_pct", 2.0), 2.0))
    grid_buy_shares = max(1, _to_int(position.get("grid_buy_shares", 100), 100))
    grid_sell_shares = max(1, _to_int(position.get("grid_sell_shares", 100), 100))
    max_layers = max(1, min(20, _to_int(position.get("max_layers", 6), 6)))
    cash_reserve_pct = min(90.0, max(0.0, _to_float(position.get("cash_reserve_pct", 20), 20.0)))
    position_cap_shares = max(1, _to_int(position.get("position_cap_shares", 1000000), 1000000))
    base_mode = str(position.get("base_price_mode", "current")).strip().lower()

    current_price = metrics["current_price"]
    current_wave = metrics["current_wave"]
    avg_cost = _to_float(position.get("avg_cost", 0), current_price)
    current_qty = max(0, _to_int(position.get("quantity", 0), 0))
    deviation_pct = metrics["deviation_pct"]
    volatility_pct = metrics["volatility_pct"]

    if base_mode == "cost":
        base_price = avg_cost if avg_cost > 0 else current_price
    elif base_mode == "wave":
        base_price = current_wave
    else:
        base_price = current_price

    vol_factor = 1.0 + max(0.0, volatility_pct - 2.0) / 20.0
    dev_factor = 1.0 + min(abs(deviation_pct), 15.0) / 50.0
    recommended_step_pct = min(8.0, max(0.5, grid_step_pct * vol_factor * dev_factor))
    recommended_buy_shares = max(1, int(round(grid_buy_shares * (0.7 if deviation_pct > 8 else 1.0))))
    recommended_sell_shares = max(1, int(round(grid_sell_shares * (1.2 if deviation_pct > 8 else 1.0))))

    levels = []
    total_buy_capital = 0.0
    for i in range(1, max_layers + 1):
        buy_price = base_price * (1 - recommended_step_pct * i / 100.0)
        sell_price = base_price * (1 + recommended_step_pct * i / 100.0)
        buy_capital = buy_price * recommended_buy_shares
        total_buy_capital += buy_capital
        levels.append(
            {
                "level": i,
                "buy_price": round(buy_price, 3),
                "sell_price": round(sell_price, 3),
                "buy_shares": recommended_buy_shares,
                "sell_shares": recommended_sell_shares,
                "buy_capital": round(buy_capital, 2),
            }
        )

    usable_cash = max(0.0, available_cash * (1 - cash_reserve_pct / 100.0))
    risk_flags = []
    if total_buy_capital > usable_cash:
        risk_flags.append("planned grid buys exceed usable cash")
    if current_qty > position_cap_shares:
        risk_flags.append("position shares exceed cap")
    return {
        "base_price": round(base_price, 3),
        "recommended_grid_step_pct": round(recommended_step_pct, 3),
        "recommended_buy_shares": recommended_buy_shares,
        "recommended_sell_shares": recommended_sell_shares,
        "levels": levels,
        "total_buy_capital": round(total_buy_capital, 2),
        "risk_flags": risk_flags,
    }


def _portfolio_asset_snapshot():
    con = _db_conn()
    rows = con.execute(
        """
        SELECT pa.owner_user_id, pa.account_id, pa.available_cash, pp.symbol, pp.quantity, pp.avg_cost
        FROM portfolio_accounts pa
        LEFT JOIN portfolio_positions pp ON pa.account_id = pp.account_id
        ORDER BY pa.owner_user_id
        """
    ).fetchall()
    con.close()
    users = {}
    for row in rows:
        uid = row[0]
        if uid not in users:
            users[uid] = {"available_cash": float(row[2] or 0), "market_value": 0.0}
        qty = _to_int(row[4], 0)
        avg = _to_float(row[5], 0.0)
        users[uid]["market_value"] += qty * avg
    result = []
    for uid, v in users.items():
        result.append(
            {
                "user_id": uid,
                "available_cash": round(v["available_cash"], 2),
                "market_value": round(v["market_value"], 2),
                "total_asset": round(v["available_cash"] + v["market_value"], 2),
            }
        )
    return result


def _single_user_asset_snapshot(user_id):
    con = _db_conn()
    rows = con.execute(
        """
        SELECT pa.available_cash, pp.quantity, pp.avg_cost
        FROM portfolio_accounts pa
        LEFT JOIN portfolio_positions pp ON pa.account_id = pp.account_id
        WHERE pa.owner_user_id = ?
        """,
        [user_id],
    ).fetchall()
    con.close()
    available_cash = 0.0
    market_value = 0.0
    for idx, row in enumerate(rows):
        if idx == 0:
            available_cash = float(row[0] or 0.0)
        qty = _to_int(row[1], 0)
        avg = _to_float(row[2], 0.0)
        market_value += qty * avg
    return {
        "user_id": user_id,
        "available_cash": round(available_cash, 2),
        "market_value": round(market_value, 2),
        "total_asset": round(available_cash + market_value, 2),
    }


init_tables()


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"ok": True, "time": datetime.now().isoformat()})


@app.route("/api/auth/register", methods=["POST"])
def auth_register():
    payload = request.get_json(silent=True) or {}
    phone = str(payload.get("phone", "")).strip()
    password = str(payload.get("password", ""))
    if not PHONE_REGEX.match(phone):
        return jsonify({"error": "invalid phone"}), 400
    if not _password_ok(password):
        return jsonify({"error": "password must contain letters and digits and length>=8"}), 400
    con = _db_conn()
    exists = con.execute("SELECT id FROM users WHERE phone = ?", [phone]).fetchone()
    if exists:
        con.close()
        return jsonify({"error": "phone already exists"}), 409
    user_id = f"u_{uuid.uuid4().hex[:10]}"
    now = datetime.now()
    con.execute(
        "INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?)",
        [user_id, phone, _hash_text(password), "user", "active", now, None],
    )
    con.close()
    _audit(user_id, "REGISTER", "user", user_id, phone)
    return jsonify({"ok": True, "user_id": user_id, "phone": phone})


@app.route("/api/auth/login", methods=["POST"])
def auth_login():
    payload = request.get_json(silent=True) or {}
    phone = str(payload.get("phone", "")).strip()
    password = str(payload.get("password", ""))
    con = _db_conn()
    row = con.execute(
        "SELECT id, password_hash, role, status FROM users WHERE phone = ?",
        [phone],
    ).fetchone()
    if not row:
        con.close()
        return jsonify({"error": "invalid credentials"}), 401
    user_id, pwd_hash, role, status = row
    if status != "active" or _hash_text(password) != pwd_hash:
        con.close()
        return jsonify({"error": "invalid credentials"}), 401
    token = uuid.uuid4().hex + uuid.uuid4().hex
    now = datetime.now()
    con.execute(
        "INSERT INTO user_sessions VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            str(uuid.uuid4()),
            user_id,
            _hash_text(token),
            now + timedelta(days=TOKEN_DAYS),
            now,
            request.remote_addr or "",
            request.headers.get("User-Agent", "")[:500],
        ],
    )
    con.execute("UPDATE users SET last_login_at = ? WHERE id = ?", [now, user_id])
    con.close()
    _audit(user_id, "LOGIN", "user", user_id, "")
    return jsonify({"ok": True, "token": token, "user": {"id": user_id, "phone": phone, "role": role}})


@app.route("/api/auth/logout", methods=["POST"])
@require_auth
def auth_logout():
    token = _get_token()
    con = _db_conn()
    con.execute("DELETE FROM user_sessions WHERE token_hash = ?", [_hash_text(token)])
    con.close()
    _audit(request.current_user["id"], "LOGOUT", "user", request.current_user["id"], "")
    return jsonify({"ok": True})


@app.route("/api/me", methods=["GET"])
@require_auth
def me():
    return jsonify({"ok": True, "user": request.current_user})


@app.route("/api/positions", methods=["GET"])
@require_auth
def get_positions():
    account_id = request.args.get("account_id", "acc_main").strip() or "acc_main"
    data = load_positions(request.current_user["id"], account_id)
    return jsonify(data)


@app.route("/api/positions/upsert", methods=["POST"])
@require_auth
def post_positions():
    payload = request.get_json(silent=True) or {}
    account_id = str(payload.get("account_id", "acc_main")).strip() or "acc_main"
    available_cash = _to_float(payload.get("available_cash", 0), 0.0)
    positions = payload.get("positions", [])
    saved = replace_positions(request.current_user["id"], account_id, available_cash, positions)
    _audit(request.current_user["id"], "UPSERT_POSITIONS", "account", account_id, f"count={len(saved)}")
    return jsonify({"ok": True, "account_id": account_id, "saved_count": len(saved)})


@app.route("/api/portfolio/analyze", methods=["POST"])
@require_auth
def analyze_portfolio():
    payload = request.get_json(silent=True) or {}
    account_id = str(payload.get("account_id", "acc_main")).strip() or "acc_main"
    available_cash = _to_float(payload.get("available_cash", 0), 0.0)
    positions = payload.get("positions", [])
    cleaned_positions = replace_positions(request.current_user["id"], account_id, available_cash, positions)
    if not cleaned_positions:
        return jsonify({"error": "no valid positions provided"}), 400

    analyzer = HongduAnalyzer()
    results = []
    total_market_value = 0.0
    total_unrealized = 0.0
    for p in cleaned_positions:
        symbol = p["symbol"]
        try:
            analyzer.run_focused_logic(symbol)
            metrics = analyzer.get_wave_metrics(symbol, refresh=False)
            if not metrics:
                continue
            phase_position = analyzer.get_phase_position(symbol, refresh=False)
            quantity = p["quantity"]
            avg_cost = p["avg_cost"]
            current_price = metrics["current_price"]
            market_value = current_price * quantity
            unrealized = (current_price - avg_cost) * quantity
            total_market_value += market_value
            total_unrealized += unrealized
            advice = build_grid_advice(metrics, p, available_cash)
            image_name = f"{symbol}_current_analysis.png"
            image_path = os.path.join(OUTPUT_PATH, image_name)
            image_url = f"/api/images/{image_name}?t={int(os.path.getmtime(image_path))}" if os.path.exists(image_path) else ""
            results.append(
                {
                    "symbol": symbol,
                    "stock_name": p["stock_name"],
                    "position_config": p,
                    "quantity": quantity,
                    "avg_cost": avg_cost,
                    "current_price": round(current_price, 3),
                    "market_value": round(market_value, 2),
                    "unrealized_pnl": round(unrealized, 2),
                    "wave_metrics": metrics,
                    "phase_position": phase_position,
                    "grid_advice": advice,
                    "image_url": image_url,
                }
            )
        except Exception as ex:
            traceback.print_exc()
            results.append({"symbol": symbol, "error": str(ex)})
    _audit(request.current_user["id"], "ANALYZE", "account", account_id, f"count={len(cleaned_positions)}")
    return jsonify(
        {
            "ok": True,
            "account_id": account_id,
            "available_cash": available_cash,
            "summary": {
                "positions": len(cleaned_positions),
                "market_value": round(total_market_value, 2),
                "unrealized_pnl": round(total_unrealized, 2),
            },
            "results": results,
        }
    )


@app.route("/api/trades", methods=["POST"])
@require_auth
def create_trade():
    payload = request.get_json(silent=True) or {}
    side = str(payload.get("side", "")).lower()
    if side not in ("buy", "sell"):
        return jsonify({"error": "side must be buy or sell"}), 400
    symbol = _norm_symbol(payload.get("symbol"))
    if not symbol:
        return jsonify({"error": "symbol required"}), 400
    quantity = max(1, _to_int(payload.get("quantity", 0), 0))
    price = max(0.0, _to_float(payload.get("price", 0), 0.0))
    amount = round(quantity * price, 2)
    con = _db_conn()
    trade_id = str(uuid.uuid4())
    con.execute(
        "INSERT INTO trade_records VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            trade_id,
            request.current_user["id"],
            symbol,
            str(payload.get("stock_name", "")),
            side,
            quantity,
            price,
            amount,
            str(payload.get("note", ""))[:300],
            datetime.now(),
        ],
    )
    con.close()
    _audit(request.current_user["id"], "CREATE_TRADE", "trade", trade_id, f"{side}:{symbol}:{quantity}@{price}")
    return jsonify({"ok": True, "trade_id": trade_id, "amount": amount})


@app.route("/api/trades", methods=["GET"])
@require_auth
def list_trades():
    limit = max(1, min(500, _to_int(request.args.get("limit", 100), 100)))
    con = _db_conn()
    rows = con.execute(
        """
        SELECT id, symbol, stock_name, side, quantity, price, amount, note, created_at
        FROM trade_records
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT ?
        """,
        [request.current_user["id"], limit],
    ).fetchall()
    con.close()
    items = []
    for r in rows:
        items.append(
            {
                "id": r[0],
                "symbol": r[1],
                "stock_name": r[2],
                "side": r[3],
                "quantity": int(r[4]),
                "price": float(r[5]),
                "amount": float(r[6]),
                "note": r[7] or "",
                "created_at": str(r[8]),
            }
        )
    return jsonify({"ok": True, "items": items})


@app.route("/api/admin/users", methods=["GET"])
@require_admin
def admin_users():
    con = _db_conn()
    rows = con.execute(
        "SELECT id, phone, role, status, created_at, last_login_at FROM users ORDER BY created_at DESC"
    ).fetchall()
    con.close()
    items = []
    for r in rows:
        items.append(
            {
                "id": r[0],
                "phone": r[1],
                "role": r[2],
                "status": r[3],
                "created_at": str(r[4]) if r[4] else "",
                "last_login_at": str(r[5]) if r[5] else "",
            }
        )
    return jsonify({"ok": True, "items": items})


@app.route("/api/admin/users/<user_id>/password", methods=["PUT"])
@require_admin
def admin_reset_password(user_id):
    payload = request.get_json(silent=True) or {}
    new_password = str(payload.get("password", ""))
    if not _password_ok(new_password, allow_admin=True):
        return jsonify({"error": "password must contain letters and digits and length>=8"}), 400
    con = _db_conn()
    con.execute("UPDATE users SET password_hash = ? WHERE id = ?", [_hash_text(new_password), user_id])
    changed = con.execute("SELECT COUNT(*) FROM users WHERE id = ?", [user_id]).fetchone()[0]
    con.close()
    if not changed:
        return jsonify({"error": "user not found"}), 404
    _audit(request.current_user["id"], "ADMIN_RESET_PASSWORD", "user", user_id, "")
    return jsonify({"ok": True})


@app.route("/api/admin/users/<user_id>", methods=["DELETE"])
@require_admin
def admin_delete_user(user_id):
    if user_id == "u_admin":
        return jsonify({"error": "cannot delete root admin"}), 400
    con = _db_conn()
    con.execute("DELETE FROM user_sessions WHERE user_id = ?", [user_id])
    con.execute("DELETE FROM trade_records WHERE user_id = ?", [user_id])
    con.execute("DELETE FROM portfolio_positions WHERE owner_user_id = ?", [user_id])
    con.execute("DELETE FROM portfolio_accounts WHERE owner_user_id = ?", [user_id])
    con.execute("DELETE FROM users WHERE id = ?", [user_id])
    con.close()
    _audit(request.current_user["id"], "ADMIN_DELETE_USER", "user", user_id, "")
    return jsonify({"ok": True})


@app.route("/api/admin/overview", methods=["GET"])
@require_admin
def admin_overview():
    con = _db_conn()
    trades = con.execute(
        """
        SELECT t.created_at, u.phone, t.symbol, t.stock_name, t.side, t.quantity, t.price, t.amount
        FROM trade_records t
        LEFT JOIN users u ON t.user_id = u.id
        ORDER BY t.created_at DESC
        LIMIT 300
        """
    ).fetchall()
    logs = con.execute(
        """
        SELECT l.created_at, u.phone, l.action, l.target_type, l.target_id, l.detail_json
        FROM audit_logs l
        LEFT JOIN users u ON l.user_id = u.id
        ORDER BY l.created_at DESC
        LIMIT 300
        """
    ).fetchall()
    con.close()
    assets = _portfolio_asset_snapshot()
    return jsonify(
        {
            "ok": True,
            "assets": assets,
            "trades": [
                {
                    "created_at": str(r[0]),
                    "phone": r[1] or "",
                    "symbol": r[2],
                    "stock_name": r[3] or "",
                    "side": r[4],
                    "quantity": int(r[5]),
                    "price": float(r[6]),
                    "amount": float(r[7]),
                }
                for r in trades
            ],
            "logs": [
                {
                    "created_at": str(r[0]),
                    "phone": r[1] or "",
                    "action": r[2],
                    "target_type": r[3],
                    "target_id": r[4],
                    "detail": r[5] or "",
                }
                for r in logs
            ],
        }
    )


@app.route("/api/admin/users/<user_id>/overview", methods=["GET"])
@require_admin
def admin_user_overview(user_id):
    con = _db_conn()
    user = con.execute("SELECT id, phone FROM users WHERE id = ?", [user_id]).fetchone()
    if not user:
        con.close()
        return jsonify({"error": "user not found"}), 404
    trades = con.execute(
        """
        SELECT created_at, symbol, stock_name, side, quantity, price, amount, note
        FROM trade_records
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT 300
        """,
        [user_id],
    ).fetchall()
    logs = con.execute(
        """
        SELECT created_at, action, target_type, target_id, detail_json
        FROM audit_logs
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT 300
        """,
        [user_id],
    ).fetchall()
    con.close()
    asset = _single_user_asset_snapshot(user_id)
    return jsonify(
        {
            "ok": True,
            "user": {"id": user[0], "phone": user[1]},
            "asset": asset,
            "trades": [
                {
                    "created_at": str(r[0]),
                    "symbol": r[1],
                    "stock_name": r[2] or "",
                    "side": r[3],
                    "quantity": int(r[4]),
                    "price": float(r[5]),
                    "amount": float(r[6]),
                    "note": r[7] or "",
                }
                for r in trades
            ],
            "logs": [
                {
                    "created_at": str(r[0]),
                    "action": r[1],
                    "target_type": r[2],
                    "target_id": r[3],
                    "detail": r[4] or "",
                }
                for r in logs
            ],
        }
    )


@app.route("/api/images/<path:filename>")
def serve_image(filename):
    safe_name = os.path.basename(filename)
    file_path = os.path.join(OUTPUT_PATH, safe_name)
    if not os.path.exists(file_path):
        return jsonify({"error": "image not found"}), 404
    return send_file(file_path, mimetype="image/png")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
