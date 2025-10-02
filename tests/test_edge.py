import time, base64, requests

# authorization
def _auth(email, pwd):
    return {"Authorization": "Basic " + base64.b64encode(f"{email}:{pwd}".encode()).decode()}

# create a random email
def _mk_email(prefix="e"):
    return f"{prefix}{int(time.time()*1000)}@example.com"

# no query in healthz -> 400
def test_healthz_rejects_query_params(base_url):
    r = requests.get(f"{base_url}/healthz".replace("/v1",""), params={"x":"1"})
    assert r.status_code == 400, r.text

def test_user_cannot_change_username_or_timestamps(base_url):
    # create user
    email = _mk_email("immut-user")
    payload = {"first_name":"A","last_name":"B","username":email,"password":"Secret123!"}
    r = requests.post(f"{base_url}/user", json=payload)
    assert r.status_code == 201, r.text
    uid = r.json()["id"]
    h = _auth(email, "Secret123!")

    # try to change username / account_created / account_updated
    malicious = {
        "first_name": "Alicia",
        "last_name": "Wang",
        "password": "NewPass456!",
        "username": "hacker@example.com",                 # can not edit
        "account_created": "2000-01-01T00:00:00.000Z",    # can not edit
        "account_updated": "2000-01-01T00:00:00.000Z",    # can not edit
    }
    r2 = requests.put(f"{base_url}/user/{uid}", headers=h, json=malicious)

    assert r2.status_code == 400, r2.text

# none exist user and product -> 403 or 404
def test_get_nonexistent_user_or_product(base_url):
    # create a user first
    email = _mk_email("pwd")
    p = {"first_name":"Only","last_name":"Pwd","username":email,"password":"Secret123!"}
    r = requests.post(f"{base_url}/user", json=p)
    assert r.status_code == 201, r.text
    h = _auth(email, "Secret123!")
    # user
    r2 = requests.get(f"{base_url}/user/999999", headers=h)
    assert r2.status_code in (403, 404), r2.text

    # product
    r3 = requests.get(f"{base_url}/product/999999", headers=h)
    assert r3.status_code in (403, 404), r3.text

# lost required field manufacturer -> 422
def test_product_missing_required_field(base_url):
    email = _mk_email("missmanu")
    p = {"first_name":"Miss","last_name":"Manu","username":email,"password":"Secret123!"}
    r = requests.post(f"{base_url}/user", json=p)
    assert r.status_code == 201, r.text
    h = _auth(email, "Secret123!")

    bad = {
        "name": "Broken",
        "description": "Missing manufacturer",
        "sku": f"SKU-{int(time.time()*1000)}",
        "quantity": 1,
        "price": 5.0
        # no manufacturer 
    }
    r2 = requests.post(f"{base_url}/product", headers=h, json=bad)
    assert r2.status_code == 422, r2.text