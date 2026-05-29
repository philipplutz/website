# Migrating to Quarto

You're replacing the al-folio contents in your existing `website` repo with these files.
The repo name stays the same, your site URL stays the same (`philipplutz.github.io/website`),
your photo stays the same — only the engine changes.

## What's in this package

- `_quarto.yml` — site configuration (navbar, theme, URLs)
- `index.qmd` — homepage with bio (replaces `_pages/about.md`)
- `publications.qmd` — publications list (replaces `_bibliography/papers.bib`)
- `projects.qmd` — Dublin Explorer project page
- `cv.qmd` — CV page (links to a PDF you upload separately)
- `styles.css` — YOUR stylesheet, fully editable
- `.github/workflows/publish.yml` — auto-build on every commit
- `.gitignore` — standard ignores

## Migration steps

### 1. Wipe the old al-folio files from your repo

In your repo, you need to delete all the existing al-folio files BEFORE uploading
the Quarto ones. The cleanest way:

Option A — fresh start in the same repo (recommended):
- Go to repo Settings → at the very bottom, "Danger Zone" → "Delete this repository"
- Re-create a new repo with the EXACT same name (`website`)
- This gives you a clean empty repo to upload Quarto into

Option B — delete files individually:
- More tedious. Skip unless you really want to preserve commit history.

Use Option A. The commit history of the al-folio attempt isn't worth keeping.

### 2. Upload the Quarto files

In the new empty `website` repo:
- "Add file" → "Upload files"
- Drag in ALL files from this folder. Including `.github` (you'll need to reveal
  hidden files first: Mac Cmd+Shift+. in Finder; Windows enable Hidden items in View)
- Commit

### 3. Add your photo

- Upload your headshot to the repo root, named exactly `prof_pic.jpg`
- Commit

### 4. Add your CV (optional)

- Upload your CV PDF to the repo root, named exactly `cv.pdf`
- Commit

### 5. Turn on Pages

- Repo Settings → Pages → Source → "Deploy from a branch"
- Branch: `gh-pages` (this branch is created automatically by the workflow on first build)
- Folder: `/ (root)` → Save

Wait for the first build to complete (check the Actions tab). Then your site
should appear at https://philipplutz.github.io/website

## After it's live: editing

The point of Quarto is that you can edit anything yourself.

- Change the bio → edit `index.qmd`, commit
- Add a paper → edit `publications.qmd`, follow the format comment in the file
- Change a colour → edit `styles.css`, uncomment the "accent colour" block
- Add a page → create a new `.qmd` file, add it to the navbar list in `_quarto.yml`

Every commit triggers a rebuild (1–2 minutes). The Actions tab shows progress.

## Placeholders to fill in

Search the files for these and replace:

- In `projects.qmd`: `YOUR-ACCOUNT.shinyapps.io/YOUR-APP-URL` → real Shiny URL
- In `publications.qmd`: verify Dublin paper details (volume/pages/DOI/link)
- The Dublin paper currently lacks a link. Either link to the publisher page when
  available, or to a preprint.

## If you don't like the look

Quarto has ~25 built-in themes. Edit `_quarto.yml`, find the line `theme: cosmo`,
change `cosmo` to one of: flatly, journal, litera, lumen, sandstone, simplex,
yeti, zephyr. Commit. The whole site restyles automatically.
