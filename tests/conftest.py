# conftest.py
import os
import pytest
import pymysql
from dotenv import load_dotenv

# # 讀取 .env
# load_dotenv(".env")

# API base URL
BASE_URL = os.getenv("BASE_URL", "http://localhost:8080/v1")

@pytest.fixture(scope="session")
def base_url():
    return BASE_URL

# # 測試 DB 連線設定
# DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
# DB_PORT = int(os.getenv("DB_PORT", "3306"))
# DB_USER = os.getenv("DB_USER", "root")
# DB_PASSWORD = os.getenv("DB_PASSWORD", "")
# DB_NAME = os.getenv("DB_NAME", "myapp_test")

# # 不清理的表（例如遷移版本表）
# EXCLUDE = {"alembic_version"}

# def _connect():
#     return pymysql.connect(
#         host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD,
#         database=DB_NAME, autocommit=True, charset="utf8mb4"
#     )

# def _list_tables(cur):
#     cur.execute(
#         """
#         SELECT TABLE_NAME
#         FROM information_schema.tables
#         WHERE TABLE_SCHEMA=%s AND TABLE_TYPE='BASE TABLE'
#         """,
#         (DB_NAME,),
#     )
#     return [r[0] for r in cur.fetchall() if r[0] not in EXCLUDE]

# def _truncate_all_tables():
#     # 安全：只允許清理名稱包含 'test' 的資料庫
#     # assert "test" in DB_NAME.lower(), f"Refusing to truncate non-test DB: {DB_NAME}"
#     conn = _connect()
#     try:
#         with conn.cursor() as cur:
#             tables = _list_tables(cur)
#             cur.execute("SET FOREIGN_KEY_CHECKS=0;")
#             for t in tables:
#                 cur.execute(f"TRUNCATE TABLE `{t}`;")
#             cur.execute("SET FOREIGN_KEY_CHECKS=1;")
#     finally:
#         conn.close()

# @pytest.fixture(autouse=True)
# def clean_db():
#     """每個測試前後皆清空所有表。"""
#     # 測試前
#     try:
#         _truncate_all_tables()
#     except Exception:
#         pass
#     yield
#     # 測試後
#     try:
#         _truncate_all_tables()
#     except Exception:
#         pass
