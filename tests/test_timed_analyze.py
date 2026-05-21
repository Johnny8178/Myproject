import api_server


def test_timed_analyze_cleans_positions_without_saving(monkeypatch):
    captured = {}

    def fake_analyze_positions(positions, available_cash):
        captured["positions"] = positions
        captured["available_cash"] = available_cash
        return {
            "summary": {"positions": len(positions), "market_value": 0, "unrealized_pnl": 0},
            "results": [{"symbol": positions[0]["symbol"], "grid_advice": {"levels": []}}],
        }

    monkeypatch.setattr(api_server, "analyze_positions", fake_analyze_positions)
    monkeypatch.setattr(api_server, "_audit", lambda *args, **kwargs: None)
    monkeypatch.setattr(api_server, "_get_user_by_token", lambda token: {"id": "u_test", "phone": "13800138000", "role": "user", "status": "active"})

    client = api_server.app.test_client()
    res = client.post(
        "/api/portfolio/timed-analyze",
        headers={"Authorization": "Bearer test-token"},
        json={
            "account_id": "acc_test",
            "available_cash": 12000,
            "positions": [
                {
                    "symbol": "600513",
                    "stock_name": "联环药业",
                    "quantity": 300,
                    "avg_cost": 9.5,
                    "grid_step_pct": 2,
                },
                {"symbol": ""},
            ],
        },
    )

    assert res.status_code == 200
    data = res.get_json()
    assert data["ok"] is True
    assert data["run_at"]
    assert data["summary"]["positions"] == 1
    assert captured["available_cash"] == 12000
    assert captured["positions"][0]["symbol"] == "600513"
    assert captured["positions"][0]["grid_buy_shares"] == 100


def test_register_accepts_username(monkeypatch):
    class FakeCon:
        def __init__(self):
            self.inserted = False

        def execute(self, sql, params=None):
            if "SELECT id FROM users WHERE phone" in sql:
                return self
            if "INSERT INTO users" in sql:
                self.inserted = True
                return self
            return self

        def fetchone(self):
            return None

        def close(self):
            pass

    fake_con = FakeCon()
    monkeypatch.setattr(api_server, "_db_conn", lambda: fake_con)
    monkeypatch.setattr(api_server, "_audit", lambda *args, **kwargs: None)

    client = api_server.app.test_client()
    res = client.post("/api/auth/register", json={"phone": "trader01", "password": "123456"})

    assert res.status_code == 200
    assert res.get_json()["phone"] == "trader01"
    assert fake_con.inserted is True
