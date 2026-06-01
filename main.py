import os
import uuid

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, Field
from starlette.middleware.sessions import SessionMiddleware

import amm
import auth
import config
from db import db, init_db

app = FastAPI(title="PredictX", description="Prediction markets on any event")
app.add_middleware(
    SessionMiddleware,
    secret_key=config.session_secret_key(),
    session_cookie="predictx_session",
    max_age=60 * 60 * 24 * 14,
    same_site="lax",
    https_only=config.is_production(),
)
init_db()

STATIC = __import__("pathlib").Path(__file__).parent / "static"


class SignupBody(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=40)


class LoginBody(BaseModel):
    email: EmailStr
    password: str


class CreateMarketBody(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(default="", max_length=2000)
    category: str = Field(default="General", max_length=50)
    end_date: str | None = None


class BetBody(BaseModel):
    side: str
    amount: float = Field(gt=0, le=10000)


class ResolveBody(BaseModel):
    resolution: str


def row_to_market(row) -> dict:
    yes_p = amm.yes_price(row["yes_pool"], row["no_pool"])
    return {
        "id": row["id"],
        "title": row["title"],
        "description": row["description"],
        "category": row["category"],
        "end_date": row["end_date"],
        "status": row["status"],
        "resolution": row["resolution"],
        "yes_price": round(yes_p, 4),
        "no_price": round(1 - yes_p, 4),
        "yes_pool": round(row["yes_pool"], 2),
        "no_pool": round(row["no_pool"], 2),
        "volume": round(row["volume"], 2),
        "created_at": row["created_at"],
    }


def enrich_positions(conn, user_id: str) -> list[dict]:
    positions = conn.execute(
        """
        SELECT p.*, m.title, m.status, m.resolution, m.yes_pool, m.no_pool
        FROM positions p
        JOIN markets m ON m.id = p.market_id
        WHERE p.user_id = ?
        ORDER BY p.created_at DESC
        """,
        (user_id,),
    ).fetchall()

    enriched = []
    for p in positions:
        yes_p = amm.yes_price(p["yes_pool"], p["no_pool"])
        current = yes_p if p["side"] == "yes" else (1 - yes_p)
        enriched.append(
            {
                "market_id": p["market_id"],
                "title": p["title"],
                "side": p["side"],
                "shares": round(p["shares"], 4),
                "cost": round(p["cost"], 2),
                "avg_price": round(p["cost"] / p["shares"], 4) if p["shares"] else 0,
                "current_price": round(current, 4),
                "status": p["status"],
                "resolution": p["resolution"],
                "value": round(p["shares"] * current, 2),
            }
        )
    return enriched


@app.get("/")
async def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/auth/config")
async def auth_config():
    return {"google_enabled": auth.google_enabled()}


@app.get("/api/auth/me")
async def auth_me(request: Request):
    user = auth.optional_user(request)
    if not user:
        raise HTTPException(401, "Not authenticated")
    with db() as conn:
        user["positions"] = enrich_positions(conn, user["id"])
    return user


@app.post("/api/auth/signup")
async def auth_signup(body: SignupBody, request: Request):
    with db() as conn:
        user = auth.create_local_user(
            conn, body.email, body.password, body.display_name
        )
    auth.login_session(request, user)
    return user


@app.post("/api/auth/login")
async def auth_login(body: LoginBody, request: Request):
    with db() as conn:
        row = auth.get_user_by_email(conn, body.email)
        if not row or not auth.verify_password(body.password, row["password_hash"]):
            raise HTTPException(401, "Invalid email or password")
        if row["auth_provider"] == "google" and not row["password_hash"]:
            raise HTTPException(
                400, "This account uses Google sign-in. Click Continue with Google."
            )
        user = auth.public_user(row)
    auth.login_session(request, user)
    return user


@app.post("/api/auth/logout")
async def auth_logout(request: Request):
    auth.logout_session(request)
    return {"ok": True}


@app.get("/api/auth/google")
async def auth_google(request: Request):
    if not auth.google_enabled():
        raise HTTPException(503, "Google sign-in is not configured")
    redirect_uri = f"{auth.base_url(request)}/api/auth/google/callback"
    return await auth.oauth.google.authorize_redirect(request, redirect_uri)


@app.get("/api/auth/google/callback")
async def auth_google_callback(request: Request):
    if not auth.google_enabled():
        raise HTTPException(503, "Google sign-in is not configured")

    try:
        token = await auth.oauth.google.authorize_access_token(request)
    except Exception as exc:
        return RedirectResponse(url="/?auth_error=google_failed")

    userinfo = token.get("userinfo")
    if not userinfo:
        raise HTTPException(400, "Could not read Google profile")

    google_id = userinfo.get("sub")
    email = userinfo.get("email")
    name = userinfo.get("name") or userinfo.get("given_name") or "Trader"

    if not google_id or not email:
        return RedirectResponse(url="/?auth_error=google_profile")

    with db() as conn:
        user = auth.create_google_user(conn, google_id, email, name)

    auth.login_session(request, user)
    return RedirectResponse(url="/?logged_in=1")


@app.get("/api/markets")
async def list_markets(
    status: str | None = None,
    q: str | None = None,
    user: dict = Depends(auth.get_current_user),
):
    with db() as conn:
        query = "SELECT * FROM markets WHERE 1=1"
        params: list = []
        if status:
            query += " AND status = ?"
            params.append(status)
        if q:
            query += " AND (title LIKE ? OR description LIKE ? OR category LIKE ?)"
            like = f"%{q}%"
            params.extend([like, like, like])
        query += " ORDER BY created_at DESC"
        rows = conn.execute(query, params).fetchall()
        return [row_to_market(r) for r in rows]


@app.post("/api/markets")
async def create_market(
    body: CreateMarketBody, user: dict = Depends(auth.get_current_user)
):
    market_id = f"m-{uuid.uuid4().hex[:10]}"
    with db() as conn:
        conn.execute(
            """
            INSERT INTO markets (id, title, description, category, end_date)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                market_id,
                body.title.strip(),
                body.description.strip(),
                body.category.strip(),
                body.end_date,
            ),
        )
        row = conn.execute("SELECT * FROM markets WHERE id = ?", (market_id,)).fetchone()
        return row_to_market(row)


@app.get("/api/markets/{market_id}")
async def get_market(
    market_id: str, user: dict = Depends(auth.get_current_user)
):
    with db() as conn:
        row = conn.execute("SELECT * FROM markets WHERE id = ?", (market_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Market not found")
        trades = conn.execute(
            """
            SELECT side, shares, price, amount, created_at
            FROM trades WHERE market_id = ?
            ORDER BY created_at DESC LIMIT 20
            """,
            (market_id,),
        ).fetchall()
        market = row_to_market(row)
        market["recent_trades"] = [dict(t) for t in trades]
        return market


@app.post("/api/markets/{market_id}/bet")
async def place_bet(
    market_id: str,
    body: BetBody,
    user: dict = Depends(auth.get_current_user),
):
    if body.side not in ("yes", "no"):
        raise HTTPException(400, "side must be 'yes' or 'no'")

    user_id = user["id"]
    with db() as conn:
        market = conn.execute("SELECT * FROM markets WHERE id = ?", (market_id,)).fetchone()
        if not market:
            raise HTTPException(404, "Market not found")
        if market["status"] != "open":
            raise HTTPException(400, "Market is not open for trading")

        user_row = auth.get_user_by_id(conn, user_id)
        if user_row["balance"] < body.amount:
            raise HTTPException(400, f"Insufficient balance (${user_row['balance']:.2f})")

        try:
            shares, new_yes, new_no, avg_price = amm.buy_shares(
                body.side, body.amount, market["yes_pool"], market["no_pool"]
            )
        except ValueError as e:
            raise HTTPException(400, str(e)) from e

        if shares <= 0:
            raise HTTPException(400, "Trade too small for current liquidity")

        conn.execute(
            "UPDATE users SET balance = balance - ? WHERE id = ?", (body.amount, user_id)
        )
        conn.execute(
            """
            UPDATE markets
            SET yes_pool = ?, no_pool = ?, volume = volume + ?
            WHERE id = ?
            """,
            (new_yes, new_no, body.amount, market_id),
        )

        existing = conn.execute(
            "SELECT * FROM positions WHERE user_id = ? AND market_id = ? AND side = ?",
            (user_id, market_id, body.side),
        ).fetchone()

        if existing:
            conn.execute(
                "UPDATE positions SET shares = ?, cost = ? WHERE id = ?",
                (existing["shares"] + shares, existing["cost"] + body.amount, existing["id"]),
            )
        else:
            conn.execute(
                "INSERT INTO positions (user_id, market_id, side, shares, cost) VALUES (?, ?, ?, ?, ?)",
                (user_id, market_id, body.side, shares, body.amount),
            )

        conn.execute(
            """
            INSERT INTO trades (user_id, market_id, side, shares, price, amount)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, market_id, body.side, shares, avg_price, body.amount),
        )

        updated = conn.execute("SELECT * FROM markets WHERE id = ?", (market_id,)).fetchone()
        user_row = auth.get_user_by_id(conn, user_id)

        return {
            "market": row_to_market(updated),
            "trade": {
                "side": body.side,
                "shares": round(shares, 4),
                "price": round(avg_price, 4),
                "amount": body.amount,
            },
            "balance": round(user_row["balance"], 2),
        }


@app.post("/api/markets/{market_id}/resolve")
async def resolve_market(
    market_id: str,
    body: ResolveBody,
    user: dict = Depends(auth.get_current_user),
):
    if body.resolution not in ("yes", "no"):
        raise HTTPException(400, "resolution must be 'yes' or 'no'")

    with db() as conn:
        market = conn.execute("SELECT * FROM markets WHERE id = ?", (market_id,)).fetchone()
        if not market:
            raise HTTPException(404, "Market not found")
        if market["status"] == "resolved":
            raise HTTPException(400, "Market already resolved")

        winning_side = body.resolution
        positions = conn.execute(
            "SELECT * FROM positions WHERE market_id = ? AND side = ?",
            (market_id, winning_side),
        ).fetchall()

        total_shares = sum(p["shares"] for p in positions)
        total_pool = market["yes_pool"] + market["no_pool"]

        payouts: list[dict] = []
        if total_shares > 0:
            for pos in positions:
                payout = (pos["shares"] / total_shares) * total_pool
                conn.execute(
                    "UPDATE users SET balance = balance + ? WHERE id = ?",
                    (payout, pos["user_id"]),
                )
                payouts.append({"user_id": pos["user_id"], "payout": round(payout, 2)})

        conn.execute(
            "UPDATE markets SET status = 'resolved', resolution = ? WHERE id = ?",
            (winning_side, market_id),
        )

        return {
            "market_id": market_id,
            "resolution": winning_side,
            "total_pool": round(total_pool, 2),
            "payouts": payouts,
        }


@app.get("/api/portfolio")
async def portfolio(user: dict = Depends(auth.get_current_user)):
    with db() as conn:
        row = auth.get_user_by_id(conn, user["id"])
        data = auth.public_user(row)
        data["positions"] = enrich_positions(conn, user["id"])
        return data


@app.get("/api/categories")
async def categories(user: dict = Depends(auth.get_current_user)):
    with db() as conn:
        rows = conn.execute(
            "SELECT DISTINCT category FROM markets ORDER BY category"
        ).fetchall()
        return [r["category"] for r in rows]


app.mount("/static", StaticFiles(directory=STATIC), name="static")


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "8000"))
    reload = os.environ.get("ENV", "development") != "production"
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=reload)
