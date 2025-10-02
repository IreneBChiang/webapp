# webapp
Assignment03  
Integration Tests

## Setup Instructions:
1. Install dependencies  

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate
``` 


```bash
# Install required packages
pip install -r requirements.txt
```

2. Create a .env file in the root directory
    DATABASE_URL=mysql+pymysql://youruser:yourpassword@127.0.0.1:3306/assignment02db?charset=utf8mb4
    PORT=8080

3. Setup Database
    
```bash
# Make sure MySQL is running
sudo service mysql start
```

    
```bash
# Create database(only once)
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS assignment02db;"
```

4. Run the application(The server will start at: http://127.0.0.1:8080/)
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

5. API testing
    If localhost does not work on your system, please use 127.0.0.1  
    use postman
    ### User  
    1. create a user account -> 201  
        Method: POST  
        URL: http://localhost:8080/v1/user  
        Body: JSON  
        {  
            "first_name": "Mark",  
            "last_name": "Lee",  
            "username": "marklee@google.com",  
            "password": "mark0802!"  
        }  

<!-- curl -i -X POST http://localhost:8080/v1/user -H "Content-Type: application/json" -d '{"first_name":"Mark","last_name":"Lee","username":"marklee@google.com","password":"mark0802!"}'   -->

    2. duplicate user -> 400  
        send again  

    3. create other user -> 201  
        Method: POST  
        URL: http://localhost:8080/v1/user  
        Body: JSON  
        {  
            "first_name": "Johnny",  
            "last_name": "Suh",  
            "username": "johnny@google.com",  
            "password": "johnny0209!"  
        }  

<!-- curl -i -X POST http://localhost:8080/v1/user -H "Content-Type: application/json" -d '{"first_name":"Johnny","last_name":"Suh","username":"johnny@google.com","password":"johnny0209!"}'   -->


    4. get user account information -> 200  
        Method: GET  
        URL: http://localhost:8080/v1/user/{id}  
        Authorization: Basic Auth  
        Username: marklee@google.com  
        Password: mark0802!  
<!-- 
curl -i -u marklee@google.com:mark0802! http://localhost:8080/v1/user/{id}   -->

    5. get other -> 403  
        Method: GET  
        URL: http://localhost:8080/v1/user/{other's id}  
        Authorization: Basic Auth  
        Username: marklee@google.com  
        Password: mark0802!  

    6. update with extra field -> 400  
        Method: PUT  
        URL: http://localhost:8080/v1/user/{id}  
        Authorization: Basic Auth  
        Body:  
        {  
            "id": 999,  
            "first_name": "NewAlice"  
        }  

<!-- curl -i -X PUT http://localhost:8080/v1/user/{id} -u marklee@google.com:mark0802! -H "Content-Type: application/json" -d '{"id":999,"first_name":"NewAlice"}'   -->


    7. update user's account information -> 204  
        Method: PUT  
        URL: http://localhost:8080/v1/user/{id}  
        Authorization: Basic Auth  
        Username: marklee@google.com  
        Password: mark0802!  
        Body:  
        {  
            "first_name": "MarkNew",  
            "last_name": "LeeNew",  
            "password": "NewSecret123!"  
        }  
 
    ### product  
    8. add a new product -> 201  
        Method: POST  
        URL: http://localhost:8080/v1/product  
        Authorization: Basic Auth  
        Body:  
        {  
            "name": "Mouse",  
            "description": "USB mouse",  
            "sku": "SKU-1",  
            "manufacturer": "Acme",  
            "quantity": 1  
        }  

<!-- curl -i -X POST http://localhost:8080/v1/product -u johnny@google.com:johnny0209! -H "Content-Type: application/json" -d '{"name":"Mouse","description":"USB mouse","sku":"SKU-1","manufacturer":"Acme","quantity":1}'     -->

    9.  get product information -> 200  
        Method: GET   
        URL:http://localhost:8080/v1/product/{id}  

    10. negative quantity -> 422  
        Method: POST  
        URL: http://localhost:8080/v1/product  
        Authorization: Basic Auth  
        Body:  
        {  
            "name": "Wrong",  
            "description": "negative quantity",  
            "sku": "SKU-1",  
            "manufacturer": "Acme",  
            "quantity": -1  
        }  

    11. non-owner update product PUT (update other's product) -> 403  
        Method: PUT  
        URL: http://localhost:8080/v1/product/{id}  
        Authorization: Basic Auth(other)  
        Body:  
        {  
            "name": "Keyboard",  
            "description": "update fail",  
            "sku": "SKU-1",  
            "manufacturer": "Acme",  
            "quantity": 2  
        }  

    12. owner update product PATCH (owner updates product) -> 204  
        Method: PATCH  
        URL: http://localhost:8080/v1/product/{id}  
        Authorization: Basic Auth  
        Body:  
        {  
            "quantity": 5  
        }  

<!-- curl -i -X PATCH http://localhost:8080/v1/product/{id} -u johnny@google.com:johnny0209! -H "Content-Type: application/json" -d '{"quantity":5}'   -->


    13. owner DELETE product -> 204  
        Method: DELETE  
        URL: http://localhost:8080/v1/product/{id}  
        Authorization: Basic Auth  
<!-- 
curl -i -X DELETE http://localhost:8080/v1/product/{id} -u johnny@google.com:johnny0209!   -->





6. Check db
    If you want to check the db:  
    
```bash
# enter MySQL
mysql -u root -p
```

    
```bash
# show all database
SHOW DATABASES;
```

    
```bash
# use assignment02db
USE assignment02db;
```

    
```bash
# show all tables
SHOW TABLES;
```

    
```bash
# view the table struture(columns and data types)
DESCRIBE users;
```

    
```bash
# view data in the table
SELECT * FROM users;
```