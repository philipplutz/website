#!/usr/bin/env python3
"""Update zenodo.json, the download counts shown on the data page.

Runs once a month in the GitHub workflow (no key needed):
    python3 _scripts/update_zenodo.py
Every Zenodo record linked in data.qmd (zenodo.org/records/<id>) is read from the Zenodo API.
The counts cover all versions of a record and use the same figures as the record page
(unique views and downloads, i.e. repeated clicks in one session count once).
If a record cannot be read, its previous counts are kept."""
import datetime, json, os, re, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QMD = os.path.join(ROOT, "data.qmd")
OUT = os.path.join(ROOT, "zenodo.json")


def stats(rid):
    req = urllib.request.Request(f"https://zenodo.org/api/records/{rid}",
                                 headers={"Accept": "application/json", "User-Agent": "philipplutz.org site build"})
    with urllib.request.urlopen(req, timeout=30) as r:
        s = (json.load(r).get("stats") or {}).get("all_versions") or {}
    dl = s.get("unique_downloads", s.get("downloads"))
    vw = s.get("unique_views", s.get("views"))
    if dl is None: raise ValueError("no download statistics")
    return int(dl), (int(vw) if vw is not None else None)


def main():
    old = {}
    if os.path.exists(OUT):
        with open(OUT, encoding="utf-8") as f: old = json.load(f)
    recs = dict(old.get("records") or {})
    ids = sorted(set(re.findall(r"zenodo\.org/records/(\d+)", open(QMD, encoding="utf-8").read())))
    changed = False
    for rid in ids:
        try:
            dl, vw = stats(rid)
        except Exception as e:
            print(f"{rid}: not updated ({e})"); continue
        entry = dict(recs.get(rid) or {}); entry.update({"downloads": dl, "views": vw})
        if entry != recs.get(rid): changed = True
        recs[rid] = entry; print(f"{rid} {entry.get('name', '')}: {dl} downloads")
    if changed:
        old["records"] = recs
        old["updated"] = datetime.date.today().isoformat()
        with open(OUT, "w", encoding="utf-8") as f: json.dump(old, f, indent=2, ensure_ascii=False); f.write("\n")


if __name__ == "__main__":
    main()
