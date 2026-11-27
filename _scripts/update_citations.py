#!/usr/bin/env python3
"""Citation metadata for every DOI on publications.qmd, fetched from Crossref.

Writes (all in the site root):
  citations.json    {doi: {key, bibtex, title, authors, journal, year, volume, issue, pages}}
  publications.bib  all entries, in the order of the publications page
  pub-ld.html       schema.org JSON-LD for the publications page (static, so crawlers see it)

The year comes from the entry on publications.qmd, so it matches the site and the CV
(Crossref dates online-first articles by their first online appearance).

Usage:
  python3 _scripts/update_citations.py                 # refresh all DOIs from Crossref
  python3 _scripts/update_citations.py --missing-only  # fetch only DOIs not yet in citations.json
  python3 _scripts/update_citations.py --from-tsv F    # offline: use a saved Crossref extract
"""
import json, re, sys, time, unicodedata, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QMD = ROOT / "publications.qmd"
OUT_JSON, OUT_BIB, OUT_LD = ROOT / "citations.json", ROOT / "publications.bib", ROOT / "pub-ld.html"
MANUAL = Path(__file__).resolve().parent / "citations_manual.bib"   # thesis and chapters without a Crossref DOI
SITE = "https://philipplutz.org"
PERSON_ID = SITE + "/#person"
UA = "philipplutz.org citation updater (mailto:p.lutz@vu.nl)"
STOP = {"a", "an", "the", "of", "on", "in", "and", "to", "for", "from", "between", "how", "why", "what", "when", "do", "does", "is", "are", "beyond", "towards", "two", "more", "why"}


def entries():
    """(doi, year) for each publication on publications.qmd that has a DOI button, in page order."""
    out, seen = [], set()
    text = QMD.read_text(encoding="utf-8")
    for block in re.split(r"\n(?=- )", text):
        m = re.search(r"\[DOI\]\(\s*(?:https?://)?(?:dx\.)?doi\.org/([^)\s]+)\s*\)", block)
        if not m:
            continue
        doi = m.group(1).strip()
        y = re.search(r"\((\d{4})\)", block)
        if doi.lower() not in seen:
            seen.add(doi.lower())
            out.append((doi, y.group(1) if y else ""))
    return out


def fetch(doi):
    url = "https://api.crossref.org/works/" + urllib.parse.quote(doi, safe="") + "?mailto=p.lutz@vu.nl"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        m = json.load(r)["message"]
    first = lambda k: (m.get(k) or [""])[0]
    return {
        "type": m.get("type", ""), "title": first("title"), "subtitle": first("subtitle"),
        "authors": [{"given": a.get("given", ""), "family": a.get("family", "")} for a in m.get("author", [])],
        "journal": first("container-title"), "volume": m.get("volume", ""), "issue": m.get("issue", ""),
        "pages": m.get("page", ""), "article_number": m.get("article-number", ""), "publisher": m.get("publisher", ""),
    }


def from_tsv(path):
    """Saved extract: doi ¦ type ¦ title ¦ subtitle ¦ given|family;... ¦ journal ¦ date ¦ volume ¦ issue ¦ page ¦ article-number ¦ publisher"""
    out = {}
    for line in Path(path).read_text(encoding="utf-8").strip().split("\n"):
        f = line.split(" ¦ ")
        out[f[0]] = {"type": f[1], "title": f[2], "subtitle": f[3],
                     "authors": [dict(zip(("given", "family"), a.split("|"))) for a in f[4].split(";") if a],
                     "journal": f[5], "volume": f[7], "issue": f[8], "pages": f[9], "article_number": f[10], "publisher": f[11]}
    return out


def ascii_fold(s):
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()


def tex(s):
    s = s.replace("’", "'").replace("‘", "'").replace("‐", "-").replace("–", "--")
    return re.sub(r"([&%$#_])", r"\\\1", s)


PROPER = {"Europe", "European", "Europeans", "EU", "Dublin", "Swiss", "Switzerland", "OECD", "MITA", "Brexit",
          "Germany", "German", "Germans", "UN", "UNHCR"}


def protect(title):
    """Brace words that must keep their capitals when a style sentence-cases titles.
    Sentence-case titles: every capitalised word after the first word of the title or a subtitle
    (these are proper nouns). Title-case titles: acronyms and known proper nouns only."""
    words = re.findall(r"[A-Za-z][\w'\u2019-]*", title)
    long_words = [w for w in words if len(w) > 3]
    title_case = long_words and sum(w[0].isupper() for w in long_words) / len(long_words) > 0.6
    out, start = [], True
    for tok in re.split(r"(\s+)", title):
        if tok.strip():
            core = re.match(r"^([^?!:.,;]*)(.*)$", tok)
            word, tail = core.group(1), core.group(2)
            bare = re.sub(r"[^A-Za-z]", "", word)
            acronym = len(bare) >= 2 and bare.isupper()
            if title_case:
                keep = acronym or word.rstrip("'s").rstrip("\u2019s") in PROPER or word in PROPER
            else:
                keep = (not start) and re.match(r"[A-Z]", word) is not None
            if keep and word:
                tok = "{" + word + "}" + tail
            start = bool(re.search(r"[:?!.]$", tok))
        out.append(tok)
    return "".join(out)


def bibtex(key, doi, year, r):
    title = r["title"] + (": " + r["subtitle"] if r.get("subtitle") else "")
    authors = " and ".join(tex(a["family"]) + ", " + tex(a["given"]) if a.get("given") else tex(a["family"]) for a in r["authors"])
    f = [("author", authors), ("title", protect(tex(title))), ("journal", tex(r["journal"])), ("year", year)]
    if r.get("volume"):                       # online-first articles: no volume, and their page numbers are provisional
        f.append(("volume", r["volume"]))
        if r.get("issue"):
            f.append(("number", r["issue"]))
        if r.get("pages"):
            f.append(("pages", r["pages"].replace("-", "--")))
        elif r.get("article_number"):
            f.append(("pages", r["article_number"]))
    f += [("doi", doi), ("url", "https://doi.org/" + doi)]
    body = ",\n".join("  {} = {{{}}}".format(k, v) for k, v in f if v)
    return "@article{%s,\n%s\n}" % (key, body)


def make_key(r, year, used):
    fam = ascii_fold((r["authors"] or [{"family": "Anon"}])[0]["family"])
    fam = re.sub(r"[^A-Za-z]", "", fam)
    words = [w for w in re.findall(r"[a-z]+", ascii_fold(r["title"]).lower()) if w not in STOP]
    key = fam + year + (words[0] if words else "")
    base, n = key, 0
    while key in used:
        n += 1
        key = base + "abcdefghij"[n - 1]
    used.add(key)
    return key


def jsonld(items):
    graph = []
    for doi, c in items:
        art = {"@type": "ScholarlyArticle", "@id": "https://doi.org/" + doi, "headline": c["title"][:110],
               "name": c["title"], "url": "https://doi.org/" + doi, "sameAs": "https://doi.org/" + doi,
               "identifier": {"@type": "PropertyValue", "propertyID": "DOI", "value": doi},
               "datePublished": c["year"],
               "author": [({"@id": PERSON_ID} if a["family"] == "Lutz" and a["given"].startswith("Philipp")
                           else {"@type": "Person", "givenName": a["given"], "familyName": a["family"],
                                 "name": (a["given"] + " " + a["family"]).strip()}) for a in c["authors"]],
               "isPartOf": {"@type": "Periodical", "name": c["journal"]}}
        if c.get("volume"):
            art["isPartOf"] = {"@type": "PublicationVolume", "volumeNumber": c["volume"],
                               "isPartOf": {"@type": "Periodical", "name": c["journal"]}}
            if c.get("pages") and "-" in c["pages"]:
                art["pageStart"], art["pageEnd"] = c["pages"].split("-", 1)
        graph.append(art)
    data = {"@context": "https://schema.org",
            "@graph": [{"@type": "Person", "@id": PERSON_ID, "name": "Philipp Lutz", "url": SITE + "/"}] + graph}
    return '<script type="application/ld+json">\n' + json.dumps(data, ensure_ascii=False, indent=1) + "\n</script>\n"


def main():
    old = json.loads(OUT_JSON.read_text(encoding="utf-8")) if OUT_JSON.exists() else {}
    tsv = from_tsv(sys.argv[sys.argv.index("--from-tsv") + 1]) if "--from-tsv" in sys.argv else None
    missing_only = "--missing-only" in sys.argv
    used, items, out = set(), [], {}
    for doi, year in entries():
        rec = None
        if tsv is not None:
            rec = tsv.get(doi)
        elif missing_only and doi in old:
            rec = old[doi].get("crossref")
        else:
            try:
                rec = fetch(doi)
                time.sleep(0.2)
            except Exception as e:                    # keep the previous record if Crossref is unreachable
                print("Crossref failed for", doi, "-", e)
                rec = old.get(doi, {}).get("crossref")
        if not rec:
            print("No metadata for", doi)
            continue
        key = make_key(rec, year, used)
        c = {"key": key, "bibtex": bibtex(key, doi, year, rec), "title": rec["title"] + (": " + rec["subtitle"] if rec.get("subtitle") else ""),
             "authors": rec["authors"], "journal": rec["journal"], "year": year, "volume": rec.get("volume", ""),
             "issue": rec.get("issue", ""), "pages": rec.get("pages", "") if rec.get("volume") else "", "crossref": rec}
        out[doi] = c
        items.append((doi, c))
    manual = []
    if MANUAL.exists():
        for e in re.findall(r"(@\w+\{[^,]+,.*?\n\})", MANUAL.read_text(encoding="utf-8"), re.S):
            key = re.match(r"@\w+\{([^,]+),", e).group(1)
            out["key:" + key] = {"key": key, "bibtex": e}
            manual.append(e)
    OUT_JSON.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    OUT_BIB.write_text("% Publications of Philipp Lutz. Source: https://philipplutz.org/publications.html\n"
                       "% Journal articles: Crossref metadata. Thesis and book chapters: from the publications page.\n\n" +
                       "\n\n".join(c["bibtex"] for _, c in items) + "\n\n" + "\n\n".join(manual) + "\n", encoding="utf-8")
    OUT_LD.write_text(jsonld(items), encoding="utf-8")
    print("Wrote", len(items), "Crossref entries and", len(manual), "manual entries")


if __name__ == "__main__":
    main()
