import time, base64, requests

# authorization
def _auth(email, pwd):
    return {"Authorization": "Basic " + base64.b64encode(f"{email}:{pwd}".encode()).decode()}

# create a random email
def _mk_email(prefix="e"):
    return f"{prefix}{int(time.time()*1000)}@example.com"

# test special char
def test_user_create_with_special_char_names(base_url):
    email = _mk_email("edge")
    special = "βé-_嗨' ."
    payload = {"first_name":special, "last_name":special, "username":email, "password":"Secret123!"}
    r = requests.post(f"{base_url}/user", json=payload)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["username"] == email

# test update password -> 204
def test_user_partial_update_password_only(base_url):
    email = _mk_email("pwd")
    p = {"first_name":"Only","last_name":"Pwd","username":email,"password":"Secret123!"}
    r = requests.post(f"{base_url}/user", json=p)
    assert r.status_code == 201
    uid = r.json()["id"]
    h = _auth(email, "Secret123!")
    r2 = requests.put(f"{base_url}/user/{uid}", headers=h, json={"password":"NewSecret456!"})
    assert r2.status_code in (200,204)

# no query in healthz -> 400
def test_healthz_rejects_query_params(base_url):
    r = requests.get(f"{base_url}/healthz".replace("/v1",""), params={"x":"1"})
    assert r.status_code == 400

# none exist user and product -> 403 or 404
def test_get_nonexistent_user_or_product(base_url):
    # create a user first
    email = _mk_email("pwd")
    p = {"first_name":"Only","last_name":"Pwd","username":email,"password":"Secret123!"}
    r = requests.post(f"{base_url}/user", json=p)
    assert r.status_code == 201
    h = _auth(email, "Secret123!")
    # user
    r1 = requests.get(f"{base_url}/user/999999", headers=h)
    assert r1.status_code in (403, 404), r1.text

    # product
    r2 = requests.get(f"{base_url}/product/999999", headers=h)
    assert r2.status_code in (403, 404), r2.text

# lost required field manufacturer -> 422
def test_product_missing_required_field(base_url):
    email = _mk_email("missmanu")
    p = {"first_name":"Miss","last_name":"Manu","username":email,"password":"Secret123!"}
    r = requests.post(f"{base_url}/user", json=p)
    assert r.status_code == 201
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