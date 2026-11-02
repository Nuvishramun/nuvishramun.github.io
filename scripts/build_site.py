#!/usr/bin/env python3
"""Build the PDF and HTML from the same CV.tex, then stage the static site."""
import argparse
from pathlib import Path
import shutil
import subprocess
from build_cv import build


def build_site(root):
    root = root.resolve()
    tex = root / 'CV.tex'
    if not tex.is_file(): raise ValueError('Put CV.tex in the repository root.')
    if not shutil.which('latexmk'): raise ValueError('latexmk and pdfLaTeX are required; see UPDATE-CV.md.')
    staging, output, tex_build = root/'_site-build', root/'_site', root/'_build/cv'
    if staging.exists(): shutil.rmtree(staging)
    ignored = shutil.ignore_patterns('.git', '.github', '.venv', '__pycache__', '_site', '_site-build', '_build', 'scripts', 'tests', 'node_modules', '*.zip', '*.md', '*.tex', '*.aux', '*.log', '*.out', '*.fls', '*.fdb_latexmk', '.DS_Store')
    shutil.copytree(root, staging, ignore=ignored)
    # Build HTML first so unsupported constructs produce a clear failure.
    build(tex, staging/'cv.html', staging/'cv.html')
    tex_build.mkdir(parents=True, exist_ok=True)
    subprocess.run([
        'latexmk', '-pdf', '-interaction=nonstopmode', '-halt-on-error',
        '-file-line-error', '-pdflatex=pdflatex -no-shell-escape %O %S',
        '-outdir='+str(tex_build), str(tex)
    ], cwd=root, check=True)
    pdf = tex_build/'CV.pdf'
    if not pdf.is_file(): raise ValueError('LaTeX did not produce CV.pdf.')
    (staging/'files').mkdir(exist_ok=True)
    shutil.copyfile(pdf, staging/'files/cv.pdf')
    # Publish a complete pair only after both outputs have succeeded.
    if output.exists(): shutil.rmtree(output)
    staging.rename(output)
    print(f'Built both outputs from {tex}: {output}/cv.html and {output}/files/cv.pdf')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    args=parser.parse_args()
    try: build_site(args.root)
    except (ValueError,OSError,subprocess.CalledProcessError) as error:
        parser.exit(1, f'Site build failed: {error}\n')

if __name__=='__main__': main()
