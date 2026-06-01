"""Reset all demo data: open markets, no bets, $1000 per user."""

from db import db, init_db, scalar


def reset_demo_data() -> dict:
    with db() as conn:
        conn.execute("DELETE FROM trades")
        conn.execute("DELETE FROM positions")
        conn.execute("UPDATE users SET balance = 1000")
        conn.execute(
            """
            UPDATE markets
            SET status = 'open',
                resolution = NULL,
                yes_pool = 100,
                no_pool = 100,
                volume = 0
            """
        )
        n_markets = scalar(conn.execute("SELECT COUNT(*) FROM markets").fetchone())
        n_users = scalar(conn.execute("SELECT COUNT(*) FROM users").fetchone())

    return {
        "markets_reset": int(n_markets or 0),
        "users_reset": int(n_users or 0),
        "message": "All markets reopened, bets cleared, every balance set to $1,000.",
    }


if __name__ == "__main__":
    init_db()
    result = reset_demo_data()
    print(result["message"])
    print(f"  Markets: {result['markets_reset']}")
    print(f"  Users: {result['users_reset']}")
