#!/usr/bin/env python3
"""Render Markdown pages and dated posts into the existing static site shell."""
from datetime import date
from html import escape
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

from build_cv import pandoc, plain

PAGES = {
    'about': ('About', 'index.html'),
    'research': ('Research', 'research.html'),
    'teaching': ('Teaching', 'teaching.html'),
    'notes': ('Notes', 'notes.html'),
    'blog': ('Blog', 'blog.html'),
    'cv': ('CV', 'cv.html'),
}
MAIN = re.compile(r'(<main\b[^>]*>).*?(</main>)', re.S)
NAV = re.compile(r'(<nav id="navigation"[^>]*>).*?(</nav>)', re.S)
READER = 'markdown+tex_math_dollars'


def read(path):
    return json.loads(pandoc(path.read_text(encoding='utf-8'), '-f', READER, '-t', 'json'))


def meta_text(meta, key):
    node = meta.get(key, {})
    return node.get('c', '') if node.get('t') == 'MetaString' else plain(node).strip()


def html(doc, prefix=''):
    if prefix:
        def rebase(node):
            if isinstance(node, list):
                for item in node: rebase(item)
            elif isinstance(node, dict):
                if node.get('t') in {'Link', 'Image'}:
                    target = node['c'][2][0]
                    if target and not target.startswith(('#', '/', '?')) and not urlsplit(target).scheme:
                        node['c'][2][0] = prefix + target
                rebase(node.get('c'))
        rebase(doc['blocks'])
    return pandoc(json.dumps({**doc, 'meta': {}}), '-f', 'json', '-t', 'html5', '--mathml', '--wrap=none')


def nav_links(page, prefix=''):
    return ''.join(
        f'<a href="{prefix}{filename}"' + (' aria-current="page"' if key == page else '') + f'>{label}</a>'
        for key, (label, filename) in PAGES.items()
    )


def render_page(shell, page, body=None, title=None, prefix=''):
    if body is not None:
        if len(MAIN.findall(shell)) != 1:
            raise ValueError('Page template must contain exactly one main element.')
        shell = MAIN.sub(
            lambda m: re.sub(r'\s+data-page-content\b', '', m[1])[:-1]
            + ' data-page-content>\n' + body + '\n' + m[2], shell, count=1
        )
    shell = re.sub(r'data-page="[^"]+"(?: data-root="[^"]*")?',
                   f'data-page="{page}"' + (f' data-root="{prefix}"' if prefix else ''), shell, count=1)
    shell = NAV.sub(lambda m: m[1] + nav_links(page, prefix) + m[2], shell, count=1)
    if prefix:
        shell = re.sub(r'((?:href|src)=")(assets/)', lambda m: m[1]+prefix+m[2], shell)
    if title:
        shell = re.sub(r'<title>.*?</title>', lambda _: f'<title>{escape(title)}</title>', shell, count=1, flags=re.S)
    return shell


def posts(root, stage, shell):
    published = []
    for source in sorted((root/'posts').glob('*.md')):
        doc = read(source)
        meta = doc['meta']
        draft = meta.get('draft', {})
        if 'draft' in meta and draft.get('t') != 'MetaBool':
            raise ValueError(f'{source.name}: draft must be true or false (unquoted).')
        if draft.get('c'):
            continue
        title, day, summary = (meta_text(meta, k) for k in ('title','date','summary'))
        slug = source.stem
        if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', slug):
            raise ValueError(f'{source.name}: use a lowercase, hyphenated filename.')
        if not title or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', day):
            raise ValueError(f'{source.name}: set title and date (YYYY-MM-DD) in the front matter.')
        try:
            published_on = date.fromisoformat(day)
        except ValueError as error:
            raise ValueError(f'{source.name}: invalid date {day}.') from error
        display_date = f'{published_on.day} {published_on:%B %Y}'
        body = (f'<article class="markdown-content blog-post"><a class="small-link" href="../blog.html">← All posts</a>'
                f'<h1>{escape(title)}</h1><p class="post-date"><time datetime="{day}">{display_date}</time></p>'
                + html(doc, '../') + '</article>')
        target = stage/'blog'/f'{slug}.html'
        target.parent.mkdir(exist_ok=True)
        target.write_text(render_page(shell, 'blog', body, title, '../'), encoding='utf-8')
        published.append((day, slug, title, display_date, summary))
    if not published:
        return '<p class="empty">No posts yet.</p>'
    return '<div class="blog-list">' + ''.join(
        f'<article class="entry"><h2><a href="blog/{slug}.html">{escape(title)}</a></h2>'
        f'<p class="post-date"><time datetime="{day}">{display}</time></p>'
        + (f'<p>{escape(summary)}</p>' if summary else '') + '</article>'
        for day, slug, title, display, summary in sorted(published, reverse=True)
    ) + '</div>'


def build_markdown(root, stage):
    shell = (root/'notes.html').read_text(encoding='utf-8')
    listing = posts(root, stage, shell)
    for page, (label, filename) in PAGES.items():
        target = stage/filename
        template = (root/filename).read_text(encoding='utf-8') if (root/filename).exists() else shell
        if page == 'cv':
            rendered = render_page(template, page, title='Curriculum vitae')
        else:
            source = root/'content'/f'{page}.md'
            if not source.is_file():
                raise ValueError(f'Missing Markdown source: {source}')
            body = '<div class="markdown-content">' + html(read(source)) + (listing if page == 'blog' else '') + '</div>'
            rendered = render_page(template, page, body, label)
        target.write_text(rendered, encoding='utf-8')
