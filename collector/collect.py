"""Fare collector. Sources: Travelpayouts Data API (free token) + Google Flights page (experimental).
Writes docs/data/fares.json and docs/data/history.json. Low volume, polite delays."""
import json, os, re, random, time, urllib.parse, urllib.request
import datetime as dt
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "docs" / "data"
TP_TOKEN = os.getenv("TP_TOKEN", "")
TP_MARKER = os.getenv("TP_MARKER", "")
USE_GOOGLE = os.getenv("USE_GOOGLE", "1") == "1"
CUR = {"Canadian dollars": "CAD", "US dollars": "USD", "euros": "EUR",
       "British pounds": "GBP", "Indian rupees": "INR"}


def load(path, default):
    try:
        return json.loads(Path(path).read_text())
    except Exception:
        return default


def from_travelpayouts(r, depart, ret):
    if not TP_TOKEN:
        return []
    q = urllib.parse.urlencode({
        "origin": r["from"], "destination": r["to"], "departure_at": depart,
        "return_at": ret, "currency": r["cur"].lower(), "sorting": "price",
        "limit": 5, "unique": "false", "token": TP_TOKEN})
    req = urllib.request.Request(
        "https://api.travelpayouts.com/aviasales/v3/prices_for_dates?" + q,
        headers={"X-Access-Token": TP_TOKEN})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            rows = json.load(resp).get("data", [])
    except Exception as e:
        print("travelpayouts failed", r["id"], e)
        return []
    out = []
    for x in rows:
        link = "https://www.aviasales.com" + x.get("link", "")
        if TP_MARKER and x.get("link"):
            link += ("&" if "?" in link else "?") + "marker=" + TP_MARKER
        out.append({"source": "Aviasales (cached)", "price": x["price"], "currency": r["cur"],
                    "airline": x.get("airline", ""), "stops": x.get("transfers"), "link": link})
    return out


def from_google(page, r, depart, ret):
    q = f"Flights from {r['from']} to {r['to']} on {depart} through {ret}"
    url = "https://www.google.com/travel/flights?" + urllib.parse.urlencode(
        {"q": q, "curr": r["cur"], "hl": "en"})
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=45000)
        for label in ("Accept all", "Reject all"):
            try:
                page.get_by_role("button", name=label).first.click(timeout=2500)
                break
            except Exception:
                pass
        page.wait_for_timeout(7000)
        labels = page.eval_on_selector_all(
            "[aria-label]", "els => els.map(e => e.getAttribute('aria-label'))")
    except Exception as e:
        print("google failed", r["id"], e)
        return []
    out, seen = [], set()
    for t in labels:
        m = re.match(r"From ([\d,]+) ([A-Za-z ]+?) (round trip|one way)", t or "")
        if not m:
            continue
        price = int(m.group(1).replace(",", ""))
        air = re.search(r"flight with ([^.]+)\.", t)
        stops = re.search(r"(Nonstop|\d+ stops?) flight", t)
        key = (price, air.group(1) if air else "")
        if key in seen:
            continue
        seen.add(key)
        n = None
        if stops:
            n = 0 if stops.group(1) == "Nonstop" else int(stops.group(1).split()[0])
        out.append({"source": "Google Flights", "price": price,
                    "currency": CUR.get(m.group(2), m.group(2)),
                    "airline": air.group(1) if air else "", "stops": n, "link": url})
    return sorted(out, key=lambda o: o["price"])[:3]


def main():
    routes = json.loads((ROOT / "routes.json").read_text())
    old = {x["id"]: x for x in load(DATA / "fares.json", {"routes": []})["routes"]}
    hist = load(DATA / "history.json", {})
    today = dt.date.today()
    page = browser = pw = None
    if USE_GOOGLE:
        try:
            from playwright.sync_api import sync_playwright
            pw = sync_playwright().start()
            browser = pw.chromium.launch()
            page = browser.new_context(locale="en-CA").new_page()
        except Exception as e:
            print("playwright unavailable", e)
    results = []
    for r in routes:
        d = today + dt.timedelta(days=r["ahead"])
        back = d + dt.timedelta(days=r["stay"])
        offers = from_travelpayouts(r, d.isoformat(), back.isoformat())
        if page:
            offers += from_google(page, r, d.isoformat(), back.isoformat())
            time.sleep(random.uniform(4, 9))
        offers = [o for o in offers if o["currency"] == r["cur"]]
        offers.sort(key=lambda o: o["price"])
        entry = {**r, "depart": d.isoformat(), "return": back.isoformat(),
                 "offers": offers[:4], "stale": False}
        if offers:
            hist.setdefault(r["id"], {})[today.isoformat()] = offers[0]["price"]
        elif r["id"] in old:
            entry = {**old[r["id"]], "stale": True}
        results.append(entry)
        print(r["id"], offers[0]["price"] if offers else "no data")
    if browser:
        browser.close()
        pw.stop()
    out = {"updated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="minutes"),
           "routes": results}
    (DATA / "fares.json").write_text(json.dumps(out, indent=1))
    (DATA / "history.json").write_text(json.dumps(hist))


if __name__ == "__main__":
    main()
