import os
from dotenv import load_dotenv

# load the .env file
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL not set in .env")

# if PORT not set in .env -> default 8080
PORT = int(os.getenv("PORT", "8080"))
