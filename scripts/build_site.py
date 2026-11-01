#!/usr/bin/env python3
"""Stage static site files and regenerate the CV in the deployment artifact."""
from pathlib import Path
import shutil
from build_cv import build

root = Path(__file__).resolve().parents[1]
output = root / '_site'
if output.exists():
    shutil.rmtree(output)
ignored = shutil.ignore_patterns('.git', '.github', '.venv', '__pycache__', '_site', 'scripts', 'tests', 'node_modules', '*.zip', '*.md', '.DS_Store')
shutil.copytree(root, output, ignore=ignored)
build(root / 'files/cv.pdf', output / 'cv.html', output / 'cv.html')
print(f'Site ready: {output}')
