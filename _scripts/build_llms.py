#!/usr/bin/env python3
"""Build llms.txt (short guide for AI agents) and llms-full.txt (site content as plain Markdown)
from the site's own pages, so both always match what is published. Run before `quarto render`."""
import json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://philipplutz.org"


def read(name):
    return (ROOT / name).read_text(encoding="utf-8")


def absolute(url):
    if re.match(r"^(https?:|mailto:)", url):
        return url
    url = re.sub(r"\.qmd(#|$)", r".html\1", url)
    return SITE + "/" + url.lstrip("/")


def clean(md):
    """Quarto Markdown/HTML to plain Markdown: drop divs, tags, attributes; keep text, links and emphasis."""
    md = re.sub(r"<!--.*?-->", "", md, flags=re.S)
    md = re.sub(r"<figure.*?</figure>", "", md, flags=re.S)
    md = re.sub(r"<iframe.*?</iframe>", "", md, flags=re.S)
    md = re.sub(r'<a [^>]*class="agenda-tile".*?</a>', "", md, flags=re.S)   # decorative tiles
    md = re.sub(r"<button.*?</button>", "", md, flags=re.S)
    md = re.sub(r'<span class="teach-years">(.*?)</span>', r" (\1)", md)
    md = re.sub(r'<span class="teach-meta">', ". ", md)
    md = re.sub(r'<pre class="bibtex".*?</pre>', "", md, flags=re.S)
    md = re.sub(r"<dt>(.*?)</dt><dd>(.*?)</dd>", lambda m: "%s: %s\n" % (m.group(1), m.group(2).replace("<br>", "; ")), md, flags=re.S)
    md = re.sub(r"<img[^>]*>", "", md)
    md = re.sub(r'<a [^>]*href="([^"]+)"[^>]*>(.*?)</a>', lambda m: "[%s](%s)" % (re.sub(r"<[^>]+>", "", m.group(2)), absolute(m.group(1))), md, flags=re.S)
    md = re.sub(r"<(em|i)>(.*?)</\1>", r"*\2*", md)
    md = re.sub(r"<[^>]+>", "", md)
    md = re.sub(r"\[\]\{[^}]*\}\s*", "", md)                 # []{.ag data-ag="..."}
    md = re.sub(r"\]\(([^)\s]+)\)\{[^}]*\}", lambda m: "](" + absolute(m.group(1)) + ")", md)
    md = re.sub(r"\]\(([^)\s]+)\)", lambda m: "](" + absolute(m.group(1)) + ")", md)
    md = re.sub(r"\s\{[#.][^}]*\}", "", md)                  # heading attributes {#id .class}
    md = re.sub(r"^:::.*$", "", md, flags=re.M)
    md = md.replace("&amp;", "&").replace("&nbsp;", " ")
    md = re.sub(r"[ \t]+\n", "\n", md)
    return re.sub(r"\n{3,}", "\n\n", md).strip()


def front_stripped(text):
    return re.sub(r"^---\n.*?\n---\n", "", text, flags=re.S)


def home():
    t = front_stripped(read("index.qmd"))
    lead = re.search(r'<p class="home-lead">(.*?)</p>', t, re.S).group(1)
    after = t[t.index("</p>", t.index("home-lead")) + 4:]
    bio = after[:after.index("## Research")]
    agendas = []
    for m in re.finditer(r"^### (.+?)\n(.*?)(?=:::\n:::)", t, re.S | re.M):
        body = m.group(2)
        q = re.search(r'<p class="agenda-q">(.*?)</p>', body, re.S)
        text = re.sub(r"<p class=\"agenda-(q|links)\">.*?</p>", "", body, flags=re.S)
        agendas.append((clean(m.group(1)), clean(q.group(1)) if q else "", clean(text)))
    bio = "\n\n".join(p for p in clean(bio).split("\n\n") if not p.startswith(("Feel free", "You'll find")))   # summary and vision; contact line left out
    return clean(lead), bio, agendas


def publications():
    t = front_stripped(read("publications.qmd"))
    t = re.sub(r"<!--.*?-->", "", t, flags=re.S)
    t = re.sub(r"^:::.*?\n:::\n", "", t, flags=re.S | re.M)
    out = []
    for line in t.split("\n"):
        if line.strip().startswith("<details>"):
            continue
        if "<summary>" in line:
            out.append("\n  Abstract: ")
            continue
        if line.strip().startswith("</details>"):
            continue
        out.append(line)
    md = "\n".join(out)
    md = re.sub(r"\n  Abstract: \n", "\n  Abstract: ", md)
    md = re.sub(r"<figure.*?</figure>", "", md, flags=re.S)
    return clean(md)


def page(name):
    return clean(front_stripped(read(name)))


def main():
    lead, bio, agendas = home()
    links = [("Publications", "publications.html", "journal articles, books and book chapters with abstracts, PDFs, DOIs and replication files"),
             ("Projects", "projects.html", "research projects and their funding"),
             ("Data", "data.html", "policy datasets (URAF, MITA, RDP, RESET-OECD), survey modules and replication files"),
             ("Teaching", "teaching.html", "courses, supervision and PhD workshops"),
             ("Engagement", "engagement.html", "media coverage, policy uptake, public talks and blog posts"),
             ("CV", "cv.pdf", "curriculum vitae (PDF)")]
    machine = [("llms-full.txt", "the content of this site as plain Markdown, including every publication with its abstract"),
               ("publications.bib", "BibTeX entries for all journal articles, from Crossref metadata"),
               ("citations.json", "the same publication metadata as JSON, keyed by DOI"),
               ("datasets.bib", "BibTeX entries for the datasets"),
               ("scholar.json", "Google Scholar citation counts, updated monthly"),
               ("mentions.yml", "media and policy mentions of the research")]
    profiles = [("ORCID", "https://orcid.org/0000-0003-2373-0180"),
                ("Google Scholar", "https://scholar.google.com/citations?user=Ml32muAAAAAJ"),
                ("ResearchGate", "https://www.researchgate.net/profile/Philipp-Lutz-2"),
                ("Bluesky", "https://bsky.app/profile/lutzphilipp.bsky.social"),
                ("LinkedIn", "https://www.linkedin.com/in/philipp-lutz-78254489")]

    summary = re.sub(r"^(Welcome!\s*)?I(?:'m| am) a", "Philipp Lutz is a", lead)
    eng = read("cv.qmd")
    mb = re.search(r'<p class="bio-text" lang="en">(.*?)</p>', eng, re.S)
    short_bio = clean(mb.group(1)) if mb else ""
    s = ["# Philipp Lutz", "", "> " + summary, "", bio, "", "## Research agendas", ""]
    s += ["- **%s**: %s" % (h, q) for h, q, _ in agendas]
    if short_bio: s += ["", "## Short bio", "", short_bio]
    s += ["", "## Pages", ""] + ["- [%s](%s/%s): %s" % (n, SITE, u, d) for n, u, d in links]
    s += ["", "## Machine-readable resources", ""] + ["- [%s](%s/%s): %s" % (n, SITE, n, d) for n, d in machine]
    s += ["", "## Profiles", ""] + ["- [%s](%s)" % p for p in profiles]
    s += ["", "## Contact", "", "- Email: p.lutz@vu.nl", ""]
    (ROOT / "llms.txt").write_text("\n".join(s), encoding="utf-8")

    f = ["# Philipp Lutz", "", "Source: %s (generated from the site's pages at each build)" % SITE, "",
         re.sub(r"^(Welcome!\s*)?I(?:'m| am) a", "Philipp Lutz is a", lead), "", bio, "", "## Research agendas", ""]
    for h, q, text in agendas:
        f += ["### " + h, "", "*" + q + "*", "", text, ""]
    f += ["## Publications", "", re.sub(r"^## ", "### ", re.sub(r"^### ", "#### ", publications(), flags=re.M), flags=re.M), "",
          "## Projects", "", re.sub(r"^#", "##", page("projects.qmd"), flags=re.M), "",
          "## Data", "", re.sub(r"^#", "##", page("data.qmd"), flags=re.M), "",
          "## Teaching", "", re.sub(r"^#", "##", page("teaching.qmd"), flags=re.M), ""]
    if short_bio: f[4:4] = ["## Short bio", "", short_bio, ""]
    (ROOT / "llms-full.txt").write_text("\n".join(f), encoding="utf-8")
    print("llms.txt and llms-full.txt written")


if __name__ == "__main__":
    main()
