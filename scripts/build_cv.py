#!/usr/bin/env python3
"""Generate responsive CV HTML from files/cv.pdf. No CV content is hard-coded.

Uses text blocks, font sizes, date labels, and PDF link annotations. Best suited
for selectable-text CVs with a single reading column or a narrow date column.
The generated page is not a pixel-for-pixel reproduction of the PDF.
"""
import argparse
from collections import Counter
from html import escape
from pathlib import Path
import re
import unicodedata
from urllib.parse import urlsplit

import pymupdf

DATE = re.compile(r'^(?:(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\.?\s+)?\d{4}(?:\s*[–—-]\s*(?:\d{4}|[Pp]resent))?$')
LABEL = re.compile(r'^(?:[\w -]{2,28}:|https?://|arXiv:)', re.UNICODE)
EMAIL = re.compile(r'^[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}$')


def clean(text):
    return unicodedata.normalize('NFKC', text).replace('\u00ad', '').replace('\ufffd', '?').strip()


def line_text(line):
    return clean(''.join(span['text'] for span in line['spans']))


def join_lines(lines):
    """Reflow wrapped text while repairing ordinary word and URL line breaks."""
    text = ''
    for value in lines:
        value = value.strip()
        if not value:
            continue
        last_word = text.rsplit(' ', 1)[-1]
        next_word = value.split(' ', 1)[0]
        if text.endswith('-') and '://' in last_word:
            text += value  # a literal hyphen inside a URL
        elif (text.endswith('-') and value[0].islower()
              and next_word not in {'and', 'or', 'of', 'to', 'in'}):
            text = text[:-1] + value
        else:
            text += (' ' if text else '') + value
    return text


def safe_uri(uri):
    return urlsplit(uri).scheme.lower() in {'https', 'http', 'mailto'}


def links_for(block, annotations, page):
    """Keep the actual PDF label as well as its target, including wrapped links."""
    box = pymupdf.Rect(block['bbox'])
    found = {}
    for item in annotations:
        uri = item.get('uri', '')
        if uri and safe_uri(uri) and box.intersects(item['from']):
            label = join_lines(page.get_textbox(item['from']).splitlines()).strip()
            found.setdefault(uri, []).append(label)
    return found


def inline_links(text, links):
    """Escape all PDF text, inserting anchors only around matching text labels."""
    matches = []
    for uri, labels in links.items():
        candidates = [uri, *labels, join_lines(labels)]
        if uri.startswith('mailto:'):
            candidates.append(uri[7:])
        elif uri.startswith(('https://', 'http://')):
            candidates.append(uri.split('://', 1)[1].rstrip('/'))
        for label in candidates:
            # Sentence punctuation belongs outside URL links.
            label = label.strip().rstrip('.,;')
            if not label:
                continue
            for match in re.finditer(re.escape(label), text):
                matches.append((match.start(), match.end(), uri))
    # Prefer the complete label over overlapping fragments of a wrapped link.
    selected = []
    for start, end, uri in sorted(matches, key=lambda m: (-(m[1]-m[0]), m[0])):
        if not any(start < b and end > a for a, b, _ in selected):
            selected.append((start, end, uri))
    result, cursor = [], 0
    for start, end, uri in sorted(selected):
        result.append(escape(text[cursor:start]))
        result.append(f'<a href="{escape(uri, quote=True)}">{escape(text[start:end])}</a>')
        cursor = end
    result.append(escape(text[cursor:]))
    return ''.join(result)


def is_bold(line):
    spans = [s for s in line['spans'] if s['text'].strip()]
    return bool(spans) and all('bold' in s['font'].lower() or s['flags'] & 16 for s in spans)


def paragraphs(lines, links=None):
    """Keep labelled fields separate; join ordinary lines into flowing text."""
    groups, current = [], []
    for line in lines:
        text = line_text(line)
        if not text:
            continue
        if current and (LABEL.match(text) or EMAIL.match(text) or is_bold(line)):
            groups.append(join_lines(current))
            current = []
        current.append(text)
        if is_bold(line):
            groups.append(join_lines(current))
            current = []
    if current:
        groups.append(join_lines(current))
    return ''.join('<p>' + inline_links(text, links or {}) + '</p>' for text in groups)


def render_body(pdf_path):
    with pymupdf.open(pdf_path) as doc:
        if doc.needs_pass:
            raise ValueError('The CV PDF is password-protected; provide an unlocked PDF.')
        records, sizes = [], Counter()
        for page in doc:
            annotations = page.get_links()
            for block in page.get_text('dict')['blocks']:
                if block.get('type') != 0:
                    continue
                lines = [line for line in block['lines'] if line_text(line)]
                if not lines:
                    continue
                spans = [s for line in lines for s in line['spans'] if s['text'].strip()]
                text = join_lines([line_text(line) for line in lines])
                # Remove small running footers/page numbers, not ordinary body text.
                size = max(s['size'] for s in spans)
                if block['bbox'][1] > page.rect.height * .94 and size < 10:
                    continue
                block['lines'] = lines
                records.append((block, text, size, links_for(block, annotations, page)))
                for span in spans:
                    sizes[round(span['size'], 1)] += len(span['text'])
        if not records or sum(len(r[1]) for r in records) < 50:
            raise ValueError('No usable selectable text found in files/cv.pdf. Export a text-based PDF; scanned/image-only CVs need OCR first.')
        body_size = sizes.most_common(1)[0][0]
        headings, used_ids = [], set()
        name = ''
        output = []
        section_open = False
        for index, (block, text, size, links) in enumerate(records):
            if index == 0 and size > body_size * 1.6:
                name = text
                output.append('<p class="cv-name">' + escape(text) + '</p>')
                continue
            if text.casefold() in {'curriculum vitae', 'curriculum vitæ', 'cv'}:
                continue
            heading = size > body_size * 1.17 and len(text) < 100 and len(block['lines']) <= 2
            if heading:
                slug = re.sub(r'[^a-z0-9]+', '-', unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode().lower()).strip('-') or 'section'
                base, count = slug, 2
                while slug in used_ids:
                    slug = f'{base}-{count}'
                    count += 1
                used_ids.add(slug)
                if section_open:
                    output.append('</section>')
                output.append(f'<section class="section cv-section" id="{slug}"><h2>{escape(text)}</h2>')
                section_open = True
                headings.append((slug, text))
                continue
            lines = block['lines'][:]
            date = line_text(lines[0]) if DATE.fullmatch(line_text(lines[0])) else ''
            if date:
                lines.pop(0)
                title = line_text(lines.pop(0)) if lines else ''
                title_html = '<h3>' + inline_links(title, links) + '</h3>' if title else ''
                content = title_html + paragraphs(lines, links)
                output.append('<article class="cv-entry"><p class="cv-date">' + escape(date) + '</p><div>' + content)
            else:
                output.append('<article class="cv-pdf-block">' + paragraphs(lines, links))
            output.append('</div></article>' if date else '</article>')
        if section_open:
            output.append('</section>')
        nav = '<nav class="cv-jump" aria-label="CV sections">' + ''.join(
            f'<a href="#{slug}">{escape(title)}</a>' for slug, title in headings
        ) + '</nav>' if headings else ''
        # Put the download and section navigation after the optional name.
        insert = 1 if name else 0
        output.insert(insert, '<p><a class="button" href="files/cv.pdf">Download CV (PDF) ↓</a></p>' + nav)
        return '<div class="cv-detail"><p class="eyebrow">Academic background</p><h1>Curriculum vitae</h1>\n' + '\n'.join(output) + '\n</div>'


def build(pdf, template, output):
    # Extract and validate first; leave the previous HTML untouched on failure.
    body = render_body(pdf)
    source = template.read_text(encoding='utf-8')
    # Match a boolean marker whether it is followed by another attribute or >.
    pattern = r'(<main\b(?=[^>]*\bdata-cv-content(?:\s|>))[^>]*>).*?(</main>)'
    if len(re.findall(pattern, source, flags=re.S)) != 1:
        raise ValueError('cv.html must contain exactly one <main ... data-cv-content> element.')
    rendered = re.sub(pattern, lambda m: m[1] + '\n<!-- Generated from files/cv.pdf. Do not edit CV text here. -->\n' + body + '\n' + m[2], source, count=1, flags=re.S)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding='utf-8')
    print(f'Generated {output} from {pdf}')


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pdf', type=Path, default=root / 'files/cv.pdf')
    parser.add_argument('--template', type=Path, default=root / 'cv.html')
    parser.add_argument('--output', type=Path, default=root / 'cv.html')
    args = parser.parse_args()
    try:
        build(args.pdf, args.template, args.output)
    except (ValueError, OSError, RuntimeError) as error:
        parser.exit(1, f'CV generation failed: {error}\n')


if __name__ == '__main__':
    main()
