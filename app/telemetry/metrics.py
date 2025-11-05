# 單一來源，任何地方都從這裡拿 stats
try:
    from statsd import StatsClient
    stats = StatsClient(host="127.0.0.1", port=8125, prefix="api")
except Exception:
    # 沒裝套件或沒有 agent 也不會炸（CI/單元測試安全）
    class _Noop:
        def incr(self, *a, **k): pass
        def timing(self, *a, **k): pass
    stats = _Noop()
