import time, base64, requests

# authorization
def _auth(email, pwd):
    return {"Authorization": "Basic " + base64.b64encode(f"{email}:{pwd}".encode()).decode()}

# create a random email
def _mk_email(prefix="u"):
    return f"{prefix}{int(time.time()*1000)}@example.com"

# test /healthz -> 200
def test_healthz_ok(base_url):
    r = requests.get(f"{base_url}/healthz".replace("/v1",""))
    assert r.status_code == 200

# use POST create a user -> 201, use GET get data -> 200, use PUT update data -> 204
def test_user_create_success_and_get_self(base_url):
    email = _mk_email("pos")
    payload = {"first_name":"Alice","last_name":"Doe","username":email,"password":"Secret123!"}
    r = requests.post(f"{base_url}/user", json=payload)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["username"] == email
    assert "password" not in body
    uid = body["id"]

    h = _auth(email, "Secret123!")
    r2 = requests.get(f"{base_url}/user/{uid}", headers=h)
    assert r2.status_code == 200
    assert r2.json()["username"] == email

    # username is the same
    new_payload = {"first_name": "Alicia","last_name": "Wang","password": "NewPass456!"}
    r3 = requests.put(f"{base_url}/user/{uid}", headers=h, json=new_payload)
    assert r3.status_code in (200, 204), r3.text

    # new password
    h_new = _auth(email, "NewPass456!")
    r4 = requests.get(f"{base_url}/user/{uid}", headers=h_new)
    assert r4.status_code == 200, r4.text
    user_after = r4.json()

    assert user_after["username"] == email
    assert user_after["first_name"] == "Alicia"
    assert user_after["last_name"] == "Wang"
    assert "password" not in user_after

# POST create product -> 201, GET get data -> 200
# PATCH update data -> 204, DELETE delete product -> 204
def test_product_create_read_update_delete_as_owner(base_url):
    email = _mk_email("owner")
    payload = {"first_name":"Ow","last_name":"Ner","username":email,"password":"Secret123!"}
    r = requests.post(f"{base_url}/user", json=payload)
    assert r.status_code == 201, r.text
    h = _auth(email, "Secret123!")

    # create
    prod = {
        "name": "Pen",
        "description": "Blue",
        "sku": f"SKU-{int(time.time()*1000)}",
        "quantity": 5,
        "price": 1.99,
        "manufacturer": "Acme"
    }
    r1 = requests.post(f"{base_url}/product", headers=h, json=prod)
    assert r1.status_code == 201, r1.text
    pid = r1.json()["id"]

    # read
    r2 = requests.get(f"{base_url}/product/{pid}", headers=h)
    assert r2.status_code == 200
    assert r2.json()["id"] == pid

    # update (use patch)
    r3 = requests.patch(f"{base_url}/product/{pid}", headers=h, json={"quantity": 7})
    assert r3.status_code in (200, 204), r3.text

    # delete
    r4 = requests.delete(f"{base_url}/product/{pid}", headers=h)
    assert r4.status_code in (200, 204), r4.text
