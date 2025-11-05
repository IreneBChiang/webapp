from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import DATABASE_URL

# declare ORM Base Class
Base = declarative_base()

# DB 連線(pre_ping improve stability -> ping before connect)
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# communicate with db -> use Session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 下面是最小新增：DB query 計時 -> StatsD 
# 我們自己做一個極簡的 StatsD sender（避免從 main 匯入造成循環）
import socket
from time import perf_counter

_STATSD_ADDR = ("127.0.0.1", 8125)
def _statsd_timing(metric: str, value_ms: int):
    try:
        msg = f"{metric}:{value_ms}|ms".encode("utf-8")
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(msg, _STATSD_ADDR)
    except Exception:
        # 不讓任何 telemetry 影響主流程
        pass

# 在每次 SQL 執行前後掛事件，量時間並送出 metrics
@event.listens_for(engine, "before_cursor_execute")
def _before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    conn.info.setdefault("_query_start_time", []).append(perf_counter())

@event.listens_for(engine, "after_cursor_execute")
def _after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    try:
        start = conn.info["_query_start_time"].pop(-1)
    except Exception:
        return
    dur_ms = int((perf_counter() - start) * 1000)
    # 自訂指標名稱：db.query.duration_ms
    _statsd_timing("db.query.duration_ms", dur_ms)
