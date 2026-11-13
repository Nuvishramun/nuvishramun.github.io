"""Compile standalone TikZ sources into portable SVG files."""
from pathlib import Path
import os
import re
import shutil
import subprocess
from tempfile import TemporaryDirectory
from xml.etree import ElementTree


def build_figures(root: Path, staging: Path) -> None:
    sources = sorted((root / 'figures').glob('*.tex'))
    if not sources:
        return
    for command in ('pdflatex', 'pdfinfo', 'pdftocairo'):
        if not shutil.which(command):
            raise ValueError(f'{command} is required for TikZ figures; install TeX Live and poppler-utils.')
    destination = staging / 'assets/figures'
    destination.mkdir(parents=True, exist_ok=True)
    for source in sources:
        if not re.fullmatch(r'[a-z0-9]+(?:[-_][a-z0-9]+)*', source.stem):
            raise ValueError(f'{source.name}: use a lowercase filename with letters, numbers, hyphens or underscores.')
        print(f'Building TikZ figure: {source.name}', flush=True)
        with TemporaryDirectory(prefix='tikz-') as directory:
            pdf = Path(directory) / f'{source.stem}.pdf'
            svg = destination / f'{source.stem}.svg'
            try:
                subprocess.run([
                    'pdflatex', '-no-shell-escape', '-interaction=nonstopmode',
                    '-halt-on-error', '-file-line-error', f'-output-directory={directory}',
                    source.name,
                ], cwd=source.parent, check=True, timeout=120)
                info = subprocess.check_output(['pdfinfo', str(pdf)], text=True, timeout=30, env={**os.environ, 'LC_ALL':'C'})
                if not re.search(r'^Pages:\s+1\s*$', info, re.M):
                    raise ValueError('expected a single-page standalone figure')
                subprocess.run(['pdftocairo', '-svg', str(pdf), str(svg)], check=True, timeout=60)
                tree = ElementTree.parse(svg)
                if any(node.tag.rsplit('}', 1)[-1] == 'image' for node in tree.iter()):
                    raise ValueError('SVG contains a raster image; use vector artwork and avoid effects that rasterise')
            except (ValueError, OSError, subprocess.SubprocessError, ElementTree.ParseError) as error:
                raise ValueError(f'{source.name}: {error}') from error
