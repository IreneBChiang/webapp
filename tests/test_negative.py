import time, base64, requests

# authorization
def _auth(email, pwd):
    return {"Authorization": "Basic " + base64.b64encode(f"{email}:{pwd}".encode()).decode()}

# create a random email
def _mk_email(prefix="n"):
    return f"{prefix}{int(time.time()*1000)}@example.com"

# duplicate email -> 400
def test_user_create_duplicate_email(base_url):
    email = _mk_email("dup")
    p = {"first_name":"A","last_name":"B","username":email,"password":"Secret123!"}
    r = requests.post(f"{base_url}/user", json=p)
    assert r.status_code == 201, r.text
    r2 = requests.post(f"{base_url}/user", json=p)
    assert r2.status_code == 400, r2.text

# no authorization to get data -> 401
def test_get_self_requires_auth(base_url):
    email = _mk_email("noauth")
    p = {"first_name":"X","last_name":"Y","username":email,"password":"Secret123!"}
    r = requests.post(f"{base_url}/user", json=p)
    assert r.status_code == 201, r.text
    uid = r.json()["id"]
    r2 = requests.get(f"{base_url}/user/{uid}")  # no header
    assert r2.status_code == 401, r2.text

# quantity = -1 -> 422
def test_product_negative_quantity_rejected(base_url):
    email = _mk_email("negq")
    p = {"first_name":"P","last_name":"Q","username":email,"password":"Secret123!"}
    r = requests.post(f"{base_url}/user", json=p)
    assert r.status_code == 201, r.text
    h = _auth(email, "Secret123!")
    bad = {
        "name": "Bad",
        "description": "neg",
        "sku": f"NEG-{int(time.time()*1000)}",
        "quantity": -1,
        "price": 1.0,
        "manufacturer": "Acme"
    }
    r2 = requests.post(f"{base_url}/product", headers=h, json=bad)
    assert r2.status_code == 422, r2.text

# wrong method -> 405
def test_wrong_method_on_healthz(base_url):
    r = requests.post(f"{base_url}/healthz".replace("/v1",""))
    assert r.status_code == 405, r.text

# other user update data -> 403
def test_access_other_user_product_forbidden_or_hidden(base_url):
    # owner create product
    email1 = _mk_email("own")
    p1 = {"first_name":"O","last_name":"W","username":email1,"password":"Secret123!"}
    r1 = requests.post(f"{base_url}/user", json=p1)
    assert r1.status_code == 201, r1.text
    h1 = _auth(email1, "Secret123!")
    prod = {
        "name": "Box",
        "description": "Owner only",
        "sku": f"SKU-{int(time.time()*1000)}",
        "quantity": 3,
        "price": 2.5,
        "manufacturer": "Acme"
    }
    r2 = requests.post(f"{base_url}/product", headers=h1, json=prod)
    assert r2.status_code == 201, r2.text
    pid = r2.json()["id"]

    # other user update and delete
    email2 = _mk_email("intr")
    p2 = {"first_name":"I","last_name":"N","username":email2,"password":"Secret123!"}
    r3 = requests.post(f"{base_url}/user", json=p2)
    assert r3.status_code == 201, r3.text
    h2 = _auth(email2, "Secret123!")

    # use PUT to update
    updated = {**prod, "quantity": 9}
    r4 = requests.put(f"{base_url}/product/{pid}", headers=h2, json=updated)
    assert r4.status_code == 403, r4.text

    # delete
    r5 = requests.delete(f"{base_url}/product/{pid}", headers=h2)
    assert r5.status_code == 403, r5.text
