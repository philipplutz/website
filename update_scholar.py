#!/usr/bin/env python3
"""Update scholar.json, the Google Scholar citation counts shown on the publications page.

Runs once a month in the GitHub workflow (needs the repository secret SERPAPI_KEY):
    SERPAPI_KEY=... python3 _scripts/update_scholar.py
For a test without the API:
    python3 _scripts/update_scholar.py --from-json saved_serpapi_response.json

Google Scholar has no official API; SerpApi (free plan: 250 searches a month) reads the
profile page. One run uses one search per 100 profile entries.
Each Scholar entry is matched to an entry in publications.qmd by its title. The match is
written with the publication's DOI when it has one, otherwise with its normalised title.
Unmatched Scholar entries (blog posts, translations, data sets) are listed in the output."""
import datetime, json, os, re, sys, unicodedata, urllib.parse, urllib.request

AUTHOR_ID = "Ml32muAAAAAJ"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QMD = os.path.join(ROOT, "publications.qmd")
OUT = os.path.join(ROOT, "scholar.json")


def norm(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "", s.lower())


def main_title(t):  # the part before the first colon or question mark
    return re.split(r"[:?]", t or "", maxsplit=1)[0]


def by_year_of(data):  # citations per year, as shown in the profile's bar chart
    graph = (data.get("cited_by") or {}).get("graph") or []
    return sorted([[int(g["year"]), int(g.get("citations") or 0)] for g in graph if str(g.get("year", "")).isdigit()])


def totals_of(data):  # profile totals: citations, h-index, i10-index (all years)
    out = {}
    for row in (data.get("cited_by") or {}).get("table", []):
        for k, v in row.items():
            if isinstance(v, dict) and "all" in v:
                out[k] = v["all"]
    return out


def fetch(key):
    articles, start, totals, by_year = [], 0, {}, []
    while True:
        q = urllib.parse.urlencode({"engine": "google_scholar_author", "author_id": AUTHOR_ID,
                                    "hl": "en", "num": 100, "start": start, "api_key": key})
        with urllib.request.urlopen("https://serpapi.com/search.json?" + q, timeout=90) as r:
            data = json.load(r)
        if data.get("error"):
            sys.exit("SerpApi error: " + data["error"])
        totals = totals or totals_of(data)
        by_year = by_year if start else by_year_of(data)
        page = data.get("articles", [])
        articles += page
        if len(page) < 100 or start >= 900:
            return articles, totals, by_year
        start += 100


def entries():
    """List items of publications.qmd: citation line (link targets removed), DOI, year."""
    out, cur = [], None
    for line in open(QMD, encoding="utf-8"):
        if line.startswith("- "):
            text = re.sub(r"\]\([^)]*\)", "]", line)            # drop link targets
            text = re.sub(r"\{[^}]*\}", "", text)                # drop attributes such as {.ag}
            year = re.search(r"\((\d{4})[a-z]?\)", text)
            cur = {"text": norm(text), "doi": "", "year": int(year.group(1)) if year else None}
            out.append(cur)
        elif line.startswith(("#", "<details")):
            cur = None
        elif cur is not None and not cur["doi"]:
            m = re.search(r"doi\.org/(10\.\d{4,9}/[^\s)\"]+)", line)
            if m:
                cur["doi"] = m.group(1).rstrip(".,;").lower()
    return out


def match(articles, pubs):
    found, unmatched = {}, []
    for a in articles:
        cites = (a.get("cited_by") or {}).get("value") or 0
        link = (a.get("cited_by") or {}).get("link") or ""
        title = re.sub(r"^\d+\s+", "", a.get("title") or "")     # Scholar prefixes some chapters with their number
        t, mt = norm(title), norm(main_title(title))
        year = int(a["year"]) if str(a.get("year", "")).isdigit() else None
        hits = [p for p in pubs if t and t in p["text"]]
        if not hits and len(mt) >= 25:                           # same main title, different subtitle
            hits = [p for p in pubs if mt in p["text"] and (year is None or p["year"] is None
                                                             or abs(p["year"] - year) <= 1)]
        if len(hits) != 1:
            if cites:
                unmatched.append(f'{cites:>4}  {title}' + ("  [several matches]" if hits else ""))
            continue
        p = hits[0]
        ident = p["doi"] or p["text"][:80]
        prev = found.get(ident)
        if prev is None or cites > prev["cites"]:                # Scholar sometimes lists a work twice
            found[ident] = {"doi": p["doi"], "key": "" if p["doi"] else (t if t in p["text"] else mt),
                            "cites": cites, "link": link}
    return list(found.values()), unmatched


def run():
    if "--from-json" in sys.argv:
        data = json.load(open(sys.argv[sys.argv.index("--from-json") + 1], encoding="utf-8"))
        articles, totals, by_year = data["articles"], totals_of(data), by_year_of(data)
    else:
        key = os.environ.get("SERPAPI_KEY")
        if not key:
            sys.exit("SERPAPI_KEY is not set")
        articles, totals, by_year = fetch(key)
    items, unmatched = match(articles, entries())
    items.sort(key=lambda i: -i["cites"])
    json.dump({"updated": datetime.date.today().isoformat(), "source": "Google Scholar (via SerpApi)",
               "profile": "https://scholar.google.com/citations?user=" + AUTHOR_ID,
               "totals": totals, "by_year": by_year, "items": items},
              open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{len(articles)} Scholar entries, {len(items)} matched to publications.qmd")
    if unmatched:
        print("Cited Scholar entries without a match:\n" + "\n".join(unmatched))


if __name__ == "__main__":
    run()
