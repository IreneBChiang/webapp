# webapp
Assignment02

## Setup Instructions:
1. Install dependencies
    Create virtual environment
```bash
python3 -m venv .venv
source .venv/bin/activate
```

    Install required packages
```bash
pip install -r requirements.txt
```

2. Create a .env file in the root directory
    DATABASE_URL=mysql+pymysql://youruser:yourpassword@127.0.0.1:3306/assignment02db?charset=utf8mb4
    PORT=8080

3. Setup Database
    Make sure MySQL is running
```bash
sudo service mysql start
```

    Create database(only once)
```bash
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS assignment02db;"
```

4. Run the application(The server will start at: http://127.0.0.1:8080/healthz)
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

5. API testing
    If localhost does not work on your system, please use 127.0.0.1



6. Check db
    If you want to check the db:
    enter MySQL
```bash
    mysql -u root -p
```

    all database
```bash
    SHOW DATABASES;
```

    use assignment02db
```bash
    USE assignment02db;
```

    show all tables
```bash
    SHOW TABLES;
```

    view the table struture(columns and data types)
```bash
    DESCRIBE users;
```

    view data in the table
```bash
    SELECT * FROM users;
```