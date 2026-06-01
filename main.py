import uuid
from datetime import datetime

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import amm
from db import db, init_db

app = FastAPI(title="PredictX", description="Prediction markets on any event")
init_db()

STATIC = __import__("pathlib").Path(__file__).parent / "static"


class CreateMarketBody(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(default="", max_length=2000)
    category: str = Field(default="General", max_length=50)
    end_date: str | None = None


class BetBody(BaseModel):
    user_id: str
    side: str
    amount: float = Field(gt=0, le=10000)


class ResolveBody(BaseModel):
    resolution: str  # yes | no


class UserBody(BaseModel):
    display_name: str = Field(min_length=1, max_length=40)


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


def ensure_user(conn, user_id: str) -> dict:
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if row:
        return dict(row)
    conn.execute(
        "INSERT INTO users (id, display_name) VALUES (?, ?)",
        (user_id, "Trader"),
    )
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return dict(row)


@app.get("/")
async def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/markets")
async def list_markets(status: str | None = None, q: str | None = None):
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
async def create_market(body: CreateMarketBody):
    market_id = f"m-{uuid.uuid4().hex[:10]}"
    with db() as conn:
        conn.execute(
            """
            INSERT INTO markets (id, title, description, category, end_date)
            VALUES (?, ?, ?, ?, ?)
            """,
            (market_id, body.title.strip(), body.description.strip(), body.category.strip(), body.end_date),
        )
        row = conn.execute("SELECT * FROM markets WHERE id = ?", (market_id,)).fetchone()
        return row_to_market(row)


@app.get("/api/markets/{market_id}")
async def get_market(market_id: str):
    with db() as conn:
        row = conn.execute("SELECT * FROM markets WHERE id = ?", (market_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Market not found")
        trades = conn.execute(
            "SELECT side, shares, price, amount, created_at FROM trades WHERE market_id = ? ORDER BY created_at DESC LIMIT 20",
            (market_id,),
        ).fetchall()
        market = row_to_market(row)
        market["recent_trades"] = [dict(t) for t in trades]
        return market


@app.post("/api/markets/{market_id}/bet")
async def place_bet(market_id: str, body: BetBody):
    if body.side not in ("yes", "no"):
        raise HTTPException(400, "side must be 'yes' or 'no'")

    with db() as conn:
        market = conn.execute("SELECT * FROM markets WHERE id = ?", (market_id,)).fetchone()
        if not market:
            raise HTTPException(404, "Market not found")
        if market["status"] != "open":
            raise HTTPException(400, "Market is not open for trading")

        user = ensure_user(conn, body.user_id)
        if user["balance"] < body.amount:
            raise HTTPException(400, f"Insufficient balance (${user['balance']:.2f})")

        try:
            shares, new_yes, new_no, avg_price = amm.buy_shares(
                body.side, body.amount, market["yes_pool"], market["no_pool"]
            )
        except ValueError as e:
            raise HTTPException(400, str(e)) from e

        if shares <= 0:
            raise HTTPException(400, "Trade too small for current liquidity")

        conn.execute("UPDATE users SET balance = balance - ? WHERE id = ?", (body.amount, body.user_id))
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
            (body.user_id, market_id, body.side),
        ).fetchone()

        if existing:
            total_shares = existing["shares"] + shares
            total_cost = existing["cost"] + body.amount
            conn.execute(
                "UPDATE positions SET shares = ?, cost = ? WHERE id = ?",
                (total_shares, total_cost, existing["id"]),
            )
        else:
            conn.execute(
                "INSERT INTO positions (user_id, market_id, side, shares, cost) VALUES (?, ?, ?, ?, ?)",
                (body.user_id, market_id, body.side, shares, body.amount),
            )

        conn.execute(
            """
            INSERT INTO trades (user_id, market_id, side, shares, price, amount)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (body.user_id, market_id, body.side, shares, avg_price, body.amount),
        )

        updated = conn.execute("SELECT * FROM markets WHERE id = ?", (market_id,)).fetchone()
        user_row = conn.execute("SELECT * FROM users WHERE id = ?", (body.user_id,)).fetchone()

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
async def resolve_market(market_id: str, body: ResolveBody):
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


@app.get("/api/users/{user_id}")
async def get_user(user_id: str):
    with db() as conn:
        user = ensure_user(conn, user_id)
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

        return {"id": user["id"], "display_name": user["display_name"], "balance": round(user["balance"], 2), "positions": enriched}


@app.post("/api/users")
async def create_user(body: UserBody):
    user_id = f"u-{uuid.uuid4().hex[:10]}"
    with db() as conn:
        conn.execute(
            "INSERT INTO users (id, display_name) VALUES (?, ?)",
            (user_id, body.display_name.strip()),
        )
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return {"id": row["id"], "display_name": row["display_name"], "balance": row["balance"]}


@app.get("/api/categories")
async def categories():
    with db() as conn:
        rows = conn.execute(
            "SELECT DISTINCT category FROM markets ORDER BY category"
        ).fetchall()
        return [r["category"] for r in rows]


app.mount("/static", StaticFiles(directory=STATIC), name="static")


if __name__ == "__main__":
    import os

    import uvicorn

    port = int(os.environ.get("PORT", "8000"))
    reload = os.environ.get("ENV", "development") != "production"
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=reload)
