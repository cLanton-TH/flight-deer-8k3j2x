import json, check
from datetime import date
base = {"name": "t", "origin": "ICN", "destination": "NRT", "window_from": "2026-11-20", "window_to": "2026-11-23",
        "trip_days": [4], "max_price": 9999999, "baggage": "none"}
out = {}
for adults in (1, 2):
    a = check.normalize({**base, "adults": adults})
    q = check.build_query(a, date(2026, 11, 20), date(2026, 11, 23))
    fl = check.search(q)
    out[adults] = sorted([(f.price, ",".join(f.airlines), "%02d:%02d" % f.flights[0].departure.time) for f in fl])[:8]
open("debug_price.txt", "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))
