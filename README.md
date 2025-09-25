# webapp
Assignment01 Health check API

Setup Instructions:
1. Install dependencies
    # Create virtual environment
    python3 -m venv .venv
    source .venv/bin/activate

    # Install required packages
    pip install -r requirements.txt

2. Create a .env file in the root directory
    DATABASE_URL=mysql+pymysql://youruser:yourpassword@127.0.0.1:3306/assignment02db?charset=utf8mb4
    PORT=8080

3. Setup Database
    # Make sure MySQL is running
    sudo service mysql start

    # Create database(only once)
    mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS assignment02db;"

4. Run the application(The server will start at: http://127.0.0.1:8080/healthz)
    uvicorn app.main:app --host 0.0.0.0 --port 8080

5. API testing
    # If localhost does not work on your system, please use 127.0.0.1
    # HTTP/1.1 200 OK
    curl -vvvv http://localhost:8080/healthz

    # HTTP/1.1 400 Bad Request
    curl -vvv -X GET http://localhost:8080/healthz -d "x=1"
    
    curl -vvvv "http://127.0.0.1:8080/healthz?id=1"

    # HTTP/1.1 405 Method Not Allowed
    curl -vvvv -XPUT http://localhost:8080/healthz

    # HTTP/1.1 503 Service Unavailable
    sudo service mysql stop
    curl -vvvv http://localhost:8080/healthz


    If you want to check the db:
    # enter MySQL
    mysql -u root -p

    # all database
    SHOW DATABASES;

    # use healthdb
    USE healthdb;

    # show all tables
    SHOW TABLES;

    # view the table struture(columns and data types)
    DESCRIBE health_checks;

    # view data in the table
    SELECT * FROM health_checks;