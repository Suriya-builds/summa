def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_auth_flow(client):
    r = client.post("/api/auth/signup", json={"name": "A", "email": "flow@example.com", "password": "password123"})
    assert r.status_code == 201
    assert "summa_session" in r.headers["set-cookie"] and "HttpOnly" in r.headers["set-cookie"]
    assert client.get("/api/auth/me").json()["user"]["email"] == "flow@example.com"
    client.post("/api/auth/logout")
    assert client.get("/api/auth/me").json() == {"user": None}
    assert client.post("/api/auth/login", json={"email": "flow@example.com", "password": "wrong"}).status_code == 401
    assert client.post("/api/auth/login", json={"email": "flow@example.com", "password": "password123"}).status_code == 200
    assert client.post("/api/auth/signup", json={"name": "A", "email": "flow@example.com", "password": "password123"}).status_code == 409


def test_validation_message_readable(client):
    r = client.post("/api/auth/signup", json={"name": "A", "email": "bad", "password": "short"})
    assert r.status_code == 422 and isinstance(r.json()["detail"], str)


def test_requires_login(client):
    for path in ("/api/transactions", "/api/analytics/summary", "/api/budgets", "/api/scam/alerts"):
        assert client.get(path).status_code == 401


def test_import_dedup_and_kinds(client, user):
    text = (
        "VM-HDFCBK: Sent Rs.250.00 From HDFC Bank A/C *1234 To SWIGGY On 03/10/26 Ref 427612345678\n"
        "VM-HDFCBK: 123456 is your OTP for txn of INR 500.00 at AMAZON. Do not share it with anyone.\n"
        "+919812045567: Dear Customer, your HDFC Bank account will be blocked today. Update your KYC immediately at hdfc-kyc-update.in/verify"
    )
    r = client.post("/api/messages/import", json={"text": text}).json()
    assert (r["transactions"], r["otps"], r["scams"]) == (1, 1, 1)
    again = client.post("/api/messages/import", json={"text": text}).json()
    assert again["duplicates"] == 3 and again["imported"] == 0


def test_scam_debit_lookalike_not_counted(client, user):
    text = "JK-ALERTS: Your a/c XX4821 will be debited Rs 4,999 for annual subscription. If not done by you click rb.gy/stop4999 to cancel"
    r = client.post("/api/messages/import", json={"text": text}).json()
    assert r["transactions"] == 0 and r["scams"] == 1


def test_users_cannot_see_each_other(client):
    client.post("/api/auth/demo")
    txn_id = client.get("/api/transactions").json()["items"][0]["id"]
    client.cookies.clear()
    client.post("/api/auth/signup", json={"name": "B", "email": "iso@example.com", "password": "password123"})
    assert client.get("/api/transactions").json()["total"] == 0
    assert client.patch(f"/api/transactions/{txn_id}", json={"note": "x"}).status_code == 404
    assert client.delete(f"/api/transactions/{txn_id}").status_code == 404


def test_demo_dashboard_numbers_consistent(client):
    client.post("/api/auth/demo")
    s = client.get("/api/analytics/summary").json()
    assert s["has_data"]
    assert round(s["income"] - s["spend"], 2) == s["saved"]
    cat_spend = sum(c["amount"] for c in s["by_category"] if c["counts_as_spend"])
    assert abs(cat_spend - s["spend"]) < 0.01
    assert client.get("/api/scam/alerts").json()["counts"]["dangerous"] >= 5


def test_category_correction_learned(client, user):
    client.post("/api/messages/import", json={"text": "\n".join(
        f"VM-HDFCBK: Sent Rs.{100 + i}.00 From HDFC Bank A/C *1234 To MYSTERY SHOP On 0{i}/10/26 Ref 42761234567{i}" for i in range(1, 4))})
    items = client.get("/api/transactions").json()["items"]
    r = client.patch(f"/api/transactions/{items[0]['id']}", json={"category": "health"}).json()
    assert r["also_updated"] == 2
    client.post("/api/messages/import", json={"text": "VM-HDFCBK: Sent Rs.99.00 From HDFC Bank A/C *1234 To MYSTERY SHOP On 09/10/26 Ref 427612345699"})
    newest = client.get("/api/transactions?q=mystery&sort=date_desc").json()["items"][0]
    assert newest["category"] == "health" and newest["category_source"] == "user"


def test_budgets_put_and_status(client, user):
    client.post("/api/messages/sample")
    r = client.put("/api/budgets", json={"limits": {"food_dining": 1000, "groceries": 0}})
    assert r.status_code == 200
    assert any(i["category"] == "food_dining" and i["limit"] == 1000 for i in r.json()["items"])
    assert client.put("/api/budgets", json={"limits": {"salary": 10}}).status_code == 422


def test_scam_check_and_dismiss(client, user):
    v = client.post("/api/scam/check", json={"text": "Your SBI account is temporarily locked. Install QuickSupport and call 9731000456"}).json()
    assert v["level"] == "dangerous"
    client.post("/api/messages/import", json={"text": "+919812045567: Dear Customer, your HDFC Bank account will be blocked today. Update KYC at hdfc-kyc-update.in"})
    alert = client.get("/api/scam/alerts").json()["items"][0]
    assert client.post(f"/api/scam/alerts/{alert['id']}/dismiss").json()["ok"]
    assert client.get("/api/scam/alerts").json()["items"] == []


def test_csv_export_escapes_formulas(client, user):
    client.post("/api/transactions", json={"date": "2026-10-03", "amount": 50, "direction": "debit", "counterparty": "=HYPERLINK(1)"})
    csv_text = client.get("/api/transactions/export.csv").text
    assert "'=HYPERLINK" in csv_text


def test_cross_site_post_blocked(client, user):
    r = client.post("/api/messages/sample", headers={"Origin": "https://evil.example"})
    assert r.status_code == 403


def test_upload_rejects_binary(client, user):
    r = client.post("/api/messages/import-file", files={"file": ("x.txt", b"\x00\x01\x02abc", "text/plain")})
    assert r.status_code == 415


def test_delete_data(client, user):
    client.post("/api/messages/sample")
    client.delete("/api/account/data")
    assert client.get("/api/account/overview").json()["transactions"] == 0


def test_redaction():
    from app.services.redact import redact_text
    out = redact_text("Call 9876543210, PAN ABCDE1234F, ref 427612345678, Rs 45000 paid, a@b.com")
    assert "9876543210" not in out and "ABCDE1234F" not in out and "427612345678" not in out and "a@b.com" not in out
    assert "45000" in out
