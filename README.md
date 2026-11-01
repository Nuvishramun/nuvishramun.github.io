# Teal academic website

A responsive academic website with About, Research, Teaching, Notes, and CV pages. It supports light/dark mode, keyboard navigation, mobile layouts, and PDF downloads. Its CV HTML is generated automatically from `files/cv.pdf`.

## Personalise the website

Edit `assets/content.js` for your profile, contact details, links, research, teaching, and notes. Add a photo and set its relative path in that file. Set `cv: "files/cv.pdf"` to include the PDF link in the profile sidebar. Leave your existing personalised file in place when applying this update.

CV text comes from `files/cv.pdf`. Do not maintain a second copy of it in HTML or `assets/content.js`.

## Publish and update

Read **UPDATE-CV.md** for the installation steps. This version uses **GitHub Actions** as the GitHub Pages publishing source. Do not select “Deploy from a branch”: it will skip the PDF conversion.

Once installed, commit a new `files/cv.pdf` and wait for the workflow. Both the HTML CV page and the downloadable PDF update automatically. Site changes to the other pages are deployed by the same workflow.

The full package includes placeholder profile content. If you already have a website, upload only the files listed in UPDATE-CV.md, preserving your `assets/content.js` and other personalised pages.

## File guide

- `files/cv.pdf`: the only maintained source of the CV text
- `cv.html`: initial generated snapshot and shared page shell; updated in the deployment artifact automatically
- `assets/cv.css`: responsive styles for the extracted CV
- `assets/content.js`: your profile and other academic pages
- `assets/style.css`: shared light/dark design and layout
- `assets/main.js`: shared page rendering and controls
- `assets/theme.js`: theme choice, persistence, and synchronization
- `scripts/build_cv.py`: PDF-to-responsive-HTML conversion
- `scripts/build_site.py`: copies the static website and generates the CV for deployment
- `scripts/requirements-cv.txt`: pinned converter dependency
- `.github/workflows/pages.yml`: build and GitHub Pages deployment

The generated CV requires a selectable-text PDF and is designed for the supplied CV layout. The text reflows on small screens; complex layouts and formulas may need adjustment. See UPDATE-CV.md for details and local preview commands.

Google Fonts are optional: system fallbacks keep the site usable without them. No analytics or AI service is used. Inspired by the clean academic profile layout at https://seewoo5.github.io/.
