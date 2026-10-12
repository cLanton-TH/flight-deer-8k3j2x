"""alerts.yaml의 조건으로 구글 항공권을 검색하고, 조건에 맞는 항공편이 새로 나오면 휴대폰으로 알림을 보냅니다.

GitHub Actions에서 매시간 실행됩니다. 로컬 실행: pip install -r requirements.txt && python check.py
알림 설정은 환경 변수: NTFY_TOPIC, NTFY_SERVER(선택), TELEGRAM_TOKEN, TELEGRAM_CHAT_ID
"""
import json
import os
import random
import sys
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import yaml
from fast_flights import FlightQuery, Passengers, create_query, fetch_flights_html
from fast_flights.model import Airport, Flights, SimpleDatetime, SingleFlight
from fast_flights.parser import _parse_time
from selectolax.lexbor import LexborHTMLParser

ROOT = Path(__file__).parent
STATE = ROOT / "state.json"
RESULTS = ROOT / "RESULTS.md"
MAX_COMBOS = 40  # 알림 하나당 한 번에 검색할 날짜 조합 최대 개수 (구글 차단 방지)
KST = timezone(timedelta(hours=9))
DOMESTIC = {"GMP", "CJU", "PUS", "TAE", "CJJ", "KWJ", "RSU", "USN", "KPO", "MWX", "YNY", "HIN", "WJU", "KUV"}


def today():
    return datetime.now(KST).date()


def to_date(v):
    return v if isinstance(v, date) else date.fromisoformat(str(v))


def hours(v):
    return (v[0], v[1]) if v else (None, None)


def normalize(raw):
    a = {
        "name": raw["name"],
        "origin": raw["origin"].upper(),
        "destination": raw["destination"].upper(),
        "trip": raw.get("trip", "round-trip"),
        "depart_from": to_date(raw["depart_from"]),
        "depart_to": to_date(raw.get("depart_to", raw["depart_from"])),
        "max_price": int(raw["max_price"]),
        "adults": int(raw.get("adults", 1)),
        "checked_bags": int(raw.get("checked_bags", 0)),
        "carry_on_bags": int(raw.get("carry_on_bags", 0)),
        "max_stops": raw.get("max_stops"),
        "airlines": [str(x).upper() for x in raw.get("airlines") or []] or None,
        "seat": raw.get("seat", "economy"),
        "active": raw.get("active", True),
    }
    nights = raw.get("nights") or [3, 3]
    a["nights_min"], a["nights_max"] = int(nights[0]), int(nights[-1])
    a["dep_h_min"], a["dep_h_max"] = hours(raw.get("depart_hours"))
    a["ret_h_min"], a["ret_h_max"] = hours(raw.get("return_hours"))
    return a


def date_combos(a):
    combos = []
    d = max(a["depart_from"], today())
    while d <= a["depart_to"]:
        if a["trip"] == "one-way":
            combos.append((d, None))
        else:
            for n in range(a["nights_min"], a["nights_max"] + 1):
                combos.append((d, d + timedelta(days=n)))
        d += timedelta(days=1)
    return combos


def build_query(a, dep, ret):
    legs = [FlightQuery(
        date=dep.isoformat(), from_airport=a["origin"], to_airport=a["destination"], airlines=a["airlines"],
        earliest_departure_hour=a["dep_h_min"], latest_departure_hour=a["dep_h_max"],
    )]
    if ret:
        legs.append(FlightQuery(
            date=ret.isoformat(), from_airport=a["destination"], to_airport=a["origin"], airlines=a["airlines"],
            earliest_departure_hour=a["ret_h_min"], latest_departure_hour=a["ret_h_max"],
        ))
    return create_query(
        flights=legs, trip=a["trip"], seat=a["seat"], passengers=Passengers(adults=a["adults"]),
        language="ko", currency="KRW", max_stops=a["max_stops"],
        checked_bags=a["checked_bags"], carry_on_bags=a["carry_on_bags"],
        hide_separate_and_self_transfer=True,
    )


def parse(html):
    """구글 항공편 페이지의 데이터(ds:1)에서 항공편 목록을 꺼냄.

    fast-flights 기본 파서는 '추천 항공편'(payload[2])을 빼먹고, 가격이 없는 항목이 있으면 통째로 실패해서
    두 목록을 모두 읽고 가격 없는 항목은 건너뛰도록 직접 파싱한다.
    """
    script = LexborHTMLParser(html).css_first(r"script.ds\:1")
    if script is None:
        raise ValueError("ds:1 데이터 없음")
    data = script.text().split("data:", 1)[1].rsplit(",", 1)[0]
    if data.endswith("errorHasStatus: true"):
        return []
    payload = json.loads(data)
    flights = []
    for section in (payload[2], payload[3]):
        for k in (section or [None])[0] or []:
            try:
                price = k[1][0][1] if k[1] and k[1][0] else None
                if not price:
                    continue
                f = k[0]
                segs = [SingleFlight(
                    from_airport=Airport(code=s[3], name=s[4]), to_airport=Airport(code=s[6], name=s[5]),
                    departure=SimpleDatetime(date=tuple(s[20]), time=_parse_time(s[8])),
                    arrival=SimpleDatetime(date=tuple(s[21]), time=_parse_time(s[10])),
                    duration=s[11], plane_type=s[17],
                ) for s in f[2]]
                flights.append(Flights(type=f[0], price=price, airlines=f[1], flights=segs, carbon=None))
            except (IndexError, TypeError):
                continue
    return flights


def search(q):
    """검색 결과 목록을 돌려줌. 결과 없음은 [], 차단·오류는 예외."""
    html = fetch_flights_html(q)
    try:
        return parse(html)
    except Exception as e:
        title = html.split("<title>", 1)[-1].split("</title>", 1)[0][:80] if "<title>" in html else html[:80]
        raise RuntimeError(f"구글 응답을 읽지 못함 (페이지 제목: {title!r}): {e!r}") from e


def matches(a, f, check_price=True):
    """구글 필터가 느슨하게 적용될 때를 대비해 한 번 더 확인."""
    if check_price and f.price > a["max_price"]:
        return False
    if a["max_stops"] is not None and len(f.flights) - 1 > a["max_stops"]:
        return False
    h = f.flights[0].departure.time[0]
    if a["dep_h_min"] is not None and h < a["dep_h_min"]:
        return False
    if a["dep_h_max"] is not None and h > a["dep_h_max"]:
        return False
    return True


def describe(f):
    first, last = f.flights[0], f.flights[-1]
    stops = "직항" if len(f.flights) == 1 else f"경유 {len(f.flights) - 1}회"
    h, m = divmod(sum(s.duration or 0 for s in f.flights), 60)
    return (f"{first.from_airport.code} {'%02d:%02d' % first.departure.time} → "
            f"{last.to_airport.code} {'%02d:%02d' % last.arrival.time} · {stops} · 비행 {h}시간 {m}분")


def naver_link(a, dep, ret):
    kind = "domestic" if a["origin"] in DOMESTIC and a["destination"] in DOMESTIC else "international"
    path = f"{a['origin']}-{a['destination']}-{dep:%Y%m%d}"
    if ret:
        path += f"/{a['destination']}-{a['origin']}-{ret:%Y%m%d}"
    fare = {"economy": "Y", "premium-economy": "P", "business": "C", "first": "F"}.get(a["seat"], "Y")
    return f"https://flight.naver.com/flights/{kind}/{path}?adult={a['adults']}&fareType={fare}"


# ---------- 알림 ----------
def send(title, body, click=None):
    sent = []
    topic = os.environ.get("NTFY_TOPIC")
    if topic:
        server = (os.environ.get("NTFY_SERVER") or "https://ntfy.sh").rstrip("/")
        payload = {"topic": topic, "title": title, "message": body, "tags": ["airplane"]}
        if click:
            payload["click"] = click
        req = urllib.request.Request(server, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=20).read()
        sent.append("ntfy")
    token, chat = os.environ.get("TELEGRAM_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if token and chat:
        data = urllib.parse.urlencode({"chat_id": chat, "text": f"{title}\n\n{body}"[:4000],
                                       "disable_web_page_preview": "true"}).encode()
        urllib.request.urlopen(f"https://api.telegram.org/bot{token}/sendMessage", data=data, timeout=20).read()
        sent.append("telegram")
    if not sent:
        print("⚠ 알림 채널이 설정되지 않았습니다 (NTFY_TOPIC 또는 TELEGRAM_TOKEN/TELEGRAM_CHAT_ID).")
    print(f"알림 전송 ({', '.join(sent) or '없음'}): {title}")
    return sent


def notify(a, rows):
    rows = sorted(rows, key=lambda r: r["price"])[:5]
    lines = []
    for r in rows:
        when = f"{r['dep']:%m/%d}" + (f"~{r['ret']:%m/%d}" if r["ret"] else "")
        lines.append(f"• {when}  {r['price']:,}원  {r['airlines']}\n  {r['detail']}\n"
                     f"  구글: {r['link']}\n  네이버: {r['naver']}")
    title = f"✈ {a['name']}: {a['origin']}→{a['destination']} {rows[0]['price']:,}원부터"
    send(title, "\n\n".join(lines), click=rows[0]["link"])


# ---------- 실행 ----------
def run_alert(a, state):
    combos = date_combos(a)
    skipped = max(0, len(combos) - MAX_COMBOS)
    combos = combos[:MAX_COMBOS]
    found, errors, cheapest = [], [], None  # cheapest: 가격 외 조건은 맞는 최저가 (참고용)
    for i, (dep, ret) in enumerate(combos):
        if i:
            time.sleep(random.uniform(2, 5))
        q = build_query(a, dep, ret)
        try:
            flights = search(q)
        except Exception as e:
            errors.append(f"{dep} {ret or ''}: {e}")
            print(f"  실패 {dep} {ret or ''}: {e}")
            continue
        near = [f for f in flights if matches(a, f, check_price=False)]
        if near:
            b = min(near, key=lambda f: f.price)
            if cheapest is None or b.price < cheapest["price"]:
                cheapest = {"dep": dep, "ret": ret, "price": b.price, "airlines": ", ".join(b.airlines),
                            "detail": describe(b), "link": q.url()}
        ok = [f for f in near if f.price <= a["max_price"]]
        print(f"  {dep}~{ret or ''}: 결과 {len(flights)}개, 조건 일치 {len(ok)}개")
        if ok:
            best = min(ok, key=lambda f: f.price)
            found.append({"dep": dep, "ret": ret, "price": best.price, "airlines": ", ".join(best.airlines),
                          "detail": describe(best), "link": q.url(), "naver": naver_link(a, dep, ret)})

    # 처음 발견했거나 이전에 알린 가격보다 싸진 것만 알림
    notified = state.setdefault(a["name"], {})
    new = []
    for r in found:
        key = f"{r['dep']}|{r['ret'] or ''}"
        if key not in notified or r["price"] < notified[key]:
            new.append(r)
            notified[key] = r["price"]
    for key in list(notified):  # 지난 날짜는 정리
        if date.fromisoformat(key.split("|")[0]) < today():
            del notified[key]
    if new:
        notify(a, new)
    return {"combos": len(combos), "skipped": skipped, "found": found, "new": len(new), "errors": errors,
            "cheapest": cheapest}


def write_results(summary):
    now = datetime.now(KST).strftime("%Y-%m-%d %H:%M")
    out = [f"# 최근 검색 결과\n\n마지막 검색: {now} (KST)\n"]
    for name, s in summary.items():
        out.append(f"\n## {name}\n")
        out.append(f"{s['combos']}개 날짜 검색, 조건에 맞는 날짜 {len(s['found'])}개, 새 알림 {s['new']}개"
                   + (f", 실패 {len(s['errors'])}개" if s["errors"] else "")
                   + (f" (조합이 많아 {s['skipped']}개 생략)" if s["skipped"] else "") + "\n")
        c = s["cheapest"]
        if c:
            when = f"{c['dep']}" + (f" ~ {c['ret']}" if c["ret"] else "")
            out.append(f"\n가격 빼고 조건에 맞는 현재 최저가: **{c['price']:,}원** ({when}, {c['airlines']}, {c['detail']}) [구글]({c['link']})\n")
        if s["found"]:
            out.append("\n| 날짜 | 가격 | 항공사 | 항공편 | 링크 |\n|---|---|---|---|---|")
            for r in sorted(s["found"], key=lambda r: r["price"]):
                when = f"{r['dep']}" + (f" ~ {r['ret']}" if r["ret"] else "")
                out.append(f"| {when} | {r['price']:,}원 | {r['airlines']} | {r['detail']} | "
                           f"[구글]({r['link']}) · [네이버]({r['naver']}) |")
        if s["errors"]:
            out.append("\n<details><summary>실패 내역</summary>\n\n" + "\n".join(f"- {e}" for e in s["errors"][:10]) + "\n</details>")
    RESULTS.write_text("\n".join(out) + "\n", encoding="utf-8")


def main():
    if "--test-notify" in sys.argv:
        send("✈ 테스트 알림", "항공권 알림이 잘 연결됐어요.", click="https://www.google.com/travel/flights")
        return
    config = yaml.safe_load((ROOT / "alerts.yaml").read_text(encoding="utf-8")) or {}
    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
    alerts = [normalize(x) for x in config.get("alerts") or [] if x.get("active", True)]
    names = {a["name"] for a in alerts}
    state = {k: v for k, v in state.items() if k in names}

    summary, total, failed = {}, 0, 0
    for a in alerts:
        print(f"[{a['name']}] {a['origin']}→{a['destination']}")
        s = run_alert(a, state)
        summary[a["name"]] = s
        total += s["combos"]
        failed += len(s["errors"])

    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    write_results(summary)
    if total and failed == total:
        print("모든 검색이 실패했습니다. 구글이 요청을 막았을 수 있어요.")
        sys.exit(1)  # 워크플로를 실패로 표시해 GitHub가 메일로 알려주게 함


if __name__ == "__main__":
    main()
