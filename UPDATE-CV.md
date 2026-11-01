# Maintain only files/cv.pdf

The PDF is now the source of the CV text. GitHub Actions extracts it, generates a responsive HTML CV, and publishes the whole website. You do not need to update the HTML yourself.

## One-time installation on your existing GitHub Pages site

Upload or replace these files, keeping their paths exactly:

- `.github/workflows/pages.yml`
- `scripts/build_cv.py`
- `scripts/build_site.py`
- `scripts/requirements-cv.txt`
- `cv.html`
- `assets/cv.css`
- `assets/main.js`
- `files/cv.pdf`

Keep your existing `assets/content.js`, photographs, `assets/style.css`, and other pages. Keep the shared-theme `assets/theme.js` from the earlier update. Do not overwrite your personal content with the template's placeholder content.

The `.github` folder may be hidden in your file browser. If it does not upload, use GitHub's Add file → Create new file and enter `.github/workflows/pages.yml` as the filename, then paste the supplied workflow.

In the repository, open **Settings → Pages → Build and deployment → Source**, and select **GitHub Actions**. This replaces the previous “Deploy from a branch” setting. Do this once.

The workflow assumes your publishing branch is `main`. If your default branch is `master` or another name, change `branches: [main]` in `.github/workflows/pages.yml` to that name. If you already have another Pages deployment workflow, disable that old deployment so the two workflows do not compete.

Commit the files. In **Actions**, open **Build CV and publish website**. If the first run occurred before you switched the publishing source, run it again with **Run workflow** after changing that setting. Wait for the build and deployment to succeed, then visit the website's CV page.

Official GitHub instructions: https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages

## Every future CV update

1. Export your updated CV as a selectable-text PDF.
2. Replace **`files/cv.pdf`** in the publishing branch and commit.
3. Wait for the **Build CV and publish website** action to finish.

The published HTML and downloadable PDF are updated together. You do not need to change `cv.html`, a JSON file, or a second copy of the CV text. Generation happens inside the deployment; the committed `cv.html` remains an initial snapshot and page shell. It is normal that GitHub's source view of `cv.html` does not show each automatic update.

## What the converter preserves

The converter extracts the PDF's text, dates, headings, and link annotations into flowing HTML. It inherits the website's teal palette and dark mode. Section navigation is generated from headings, so new sections in the PDF can appear without editing a section list. It does not require an API key or AI service.

It is designed for the supplied CV layout: one content column with an optional narrow column of dates. Selectable-text PDF is required; scans or image-only PDFs fail with an explanatory Actions log. It does not reproduce the PDF's exact fonts, pagination, tables, images, or complex mathematical layout. A substantially different multi-column design may need a converter adjustment. Check the CV page after changing the PDF layout.

If extraction/building fails, the workflow will not deploy a partial page; the previous successful deployment stays available.

The PDF's contents are preserved as supplied. Any spelling, dates, or factual corrections should be made in your original CV before exporting the replacement PDF.

## Local preview (optional)

Run these commands inside the website folder:

```sh
python3 -m pip install -r scripts/requirements-cv.txt
python3 scripts/build_site.py
python3 -m http.server 8000 --directory _site
```

Open http://localhost:8000/cv.html. To regenerate the repository's snapshot for offline viewing, run `python3 scripts/build_cv.py` instead. `_site/` is temporary build output and should not be committed or uploaded as source.
