#!/usr/bin/env python3
"""Convert CV.tex to responsive HTML, with explicit cventry/cvline mappings.

Uses Pandoc's LaTeX reader for links, accents, lists, emphasis, and mathematics.
No PDF text extraction or external Python packages are needed.
"""
import argparse
import copy
from html import escape
import json
from pathlib import Path
import re
import shutil
import subprocess


def strip_comments(source):
    output, i = [], 0
    while i < len(source):
        if source[i] == '\\' and i + 1 < len(source):
            output.append(source[i:i+2]); i += 2
        elif source[i] == '%':
            end = source.find('\n', i)
            i = len(source) if end < 0 else end + 1
        else:
            output.append(source[i]); i += 1
    source = ''.join(output)
    return re.sub(r'\\begin\s*\{comment\}.*?\\end\s*\{comment\}', '', source, flags=re.S)


def group_at(source, position):
    while position < len(source) and source[position].isspace():
        position += 1
    if position >= len(source) or source[position] != '{':
        raise ValueError('Expected a braced argument after a CV command.')
    start, depth, i = position + 1, 1, position + 1
    while i < len(source):
        if source[i] == '\\':
            i += 2; continue
        if source[i] == '{': depth += 1
        if source[i] == '}': depth -= 1
        if depth == 0: return source[start:i], i + 1
        i += 1
    raise ValueError('Unclosed braced argument in CV.tex.')


def preprocess(source):
    source = strip_comments(source)
    match = re.search(r'\\begin\s*\{document\}', source)
    end = re.search(r'\\end\s*\{document\}', source)
    if not match or not end:
        raise ValueError('CV.tex must contain a document environment.')
    preamble, body = source[:match.start()], source[match.end():end.start()]
    # enumitem's optional label syntax changes PDF numbering, not list content.
    for opening in (r'\begin{enumerate}', r'\begin{itemize}'):
        cursor = 0
        while True:
            found = body.find(opening, cursor)
            if found < 0: break
            position = found + len(opening)
            while position < len(body) and body[position].isspace(): position += 1
            if position < len(body) and body[position] == '[':
                start, depth = position, 1
                position += 1
                while position < len(body) and depth:
                    if body[position] == '\\': position += 2; continue
                    if body[position] == '[': depth += 1
                    if body[position] == ']': depth -= 1
                    position += 1
                if depth: raise ValueError('Unclosed optional list arguments in CV.tex.')
                body = body[:start] + body[position:]
            cursor = found + len(opening)
    body = re.sub(r'\\hrule(?:\s+(?:height|width|depth)\s*[+-]?\d*\.?\d+\s*(?:pt|mm|cm|in|em|ex))*', '', body)
    replacements, out, i = {}, [], 0
    while i < len(body):
        if body[i] != '\\':
            out.append(body[i]); i += 1; continue
        command = re.match(r'\\([A-Za-z]+|.)', body[i:], re.S)
        if not command:
            out.append(body[i]); i += 1; continue
        name = command[1]; stop = i + len(command[0])
        if name not in {'cventry', 'cvline'}:
            out.append(command[0]); i = stop; continue
        args = []
        for _ in range(4 if name == 'cventry' else 2):
            value, stop = group_at(body, stop); args.append(value)
        marker = f'TEXCVBLOCK{len(replacements):04d}'
        if marker in source: raise ValueError('Reserved TEXCVBLOCK marker found in CV.tex.')
        replacements[marker] = (name, args)
        out.append('\n\\begin{quote}\n' + marker + '\n\\end{quote}\n')
        i = stop
    return preamble, ''.join(out), replacements


def pandoc(text, *options):
    if not shutil.which('pandoc'):
        raise ValueError('Pandoc is required. See UPDATE-CV.md for installation.')
    result = subprocess.run(['pandoc', *options], input=text, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode:
        raise ValueError('Pandoc conversion failed:\n' + result.stderr)
    if result.stderr.strip(): print(result.stderr.strip())
    return result.stdout


def plain(node):
    if isinstance(node, list): return ''.join(plain(n) for n in node)
    if not isinstance(node, dict): return ''
    kind, value = node.get('t'), node.get('c')
    if kind == 'Str': return value
    if kind in {'Space', 'SoftBreak', 'LineBreak'}: return ' '
    if kind in {'Link', 'Image'}: return plain(value[1])
    if kind in {'Span', 'Div'}: return plain(value[1])
    if kind == 'Header': return plain(value[2])
    if kind == 'Math': return value[1]
    return plain(value)


def div(classes, blocks, identifier=''):
    return {'t':'Div', 'c':[[identifier, classes.split(), []], blocks]}


def inlines(blocks):
    result = []
    for block in blocks:
        if result: result.append({'t':'LineBreak'})
        if block['t'] in {'Para', 'Plain'}: result.extend(block['c'])
        elif block['t'] == 'Div': result.extend(inlines(block['c'][1]))
        else: raise ValueError('A CV date/title contains an unsupported block: ' + block['t'])
    return result


def render_body(tex):
    preamble, body, replacements = preprocess(tex.read_text(encoding='utf-8'))
    def read(fragment):
        source = preamble + '\n\\begin{document}\n' + fragment + '\n\\end{document}\n'
        return json.loads(pandoc(source, '-f', 'latex+raw_tex', '-t', 'json'))
    doc = read(body)
    mapped = {}
    for marker, (name, args) in replacements.items():
        fragments = [read(arg)['blocks'] for arg in args]
        if name == 'cventry':
            date, title, institution, details = fragments
            heading = {'t':'Header','c':[3, ['',[],[]], inlines(title)]}
            mapped[marker] = div('cv-entry', [
                div('cv-date', date),
                div('cv-entry-body', [heading, div('cv-org', institution), div('cv-entry-details', details)])
            ])
        else:
            label, value = fragments
            mapped[marker] = div('cv-skill', [div('cv-skill-label', label), div('cv-skill-value', value)])

    def walk(node):
        if isinstance(node, list):
            items = [walk(n) for n in node]
            return [n for n in items if not (isinstance(n,dict) and n.get('t')=='Div' and not n['c'][1])]
        if not isinstance(node, dict): return node
        if node.get('t') == 'BlockQuote':
            marker = plain(node['c']).strip()
            if marker in mapped: return walk(copy.deepcopy(mapped[marker]))
        if node.get('t') in {'RawInline', 'RawBlock'} and node['c'][0] in {'tex','latex'}:
            raw = node['c'][1].strip()
            referee = re.fullmatch(r'\\begin\s*\{flushleft\}(.*?)\\end\s*\{flushleft\}', raw, flags=re.S)
            if referee:
                return div('cv-referee', walk(read(referee[1])['blocks']))
            # These commands affect the PDF's typography/pagination only.
            if re.match(r'^\\(?:fontsize|selectfont|vspace|hspace|hrule|newpage|clearpage|pagebreak|noindent|par\b|color|sffamily|small|large|Large|addvspace)', raw):
                return {'t':'Str','c':''} if node['t']=='RawInline' else div('', [])
            if raw == '\\textperiodcentered':
                return {'t':'Str','c':'·'}
            if raw in {'\\enspace', '\\quad', '\\qquad', '\\thinspace'}:
                return {'t':'Space'}
            if raw in {'\\LaTeX','\\TeX'}:
                return {'t':'Str','c':raw[1:]}
            raise ValueError('Unsupported LaTeX in HTML conversion: ' + raw + '. Add an explicit mapping rather than silently losing content.')
        return {key:walk(value) for key,value in node.items()}
    blocks = walk(doc['blocks'])
    # Presentation-only empty blocks and the redundant PDF subtitle/rule.
    blocks = [b for b in blocks if b['t'] != 'HorizontalRule'
              and not (b['t']=='Para' and (not plain(b).strip() or plain(b).strip().casefold()=='curriculum vitae'))]
    intro, sections, current = [], [], None
    for block in blocks:
        if block['t']=='Header' and block['c'][0] <= 2:
            level, attr, title = block['c']
            block['c'][0] = 2
            current = div('section cv-section', [block], attr[0])
            # The section owns the id; do not duplicate it on its heading.
            block['c'][1][0] = ''
            sections.append(current)
        elif current is None: intro.append(block)
        else: current['c'][1].append(block)
    if intro and intro[0]['t']=='Para': intro[0] = div('cv-name', [intro[0]])
    if not sections: raise ValueError('No sections found in CV.tex.')
    headings = [(s['c'][0][0], plain(s['c'][1][0])) for s in sections]
    nav = '<nav class="cv-jump" aria-label="CV sections">' + ''.join(
        f'<a href="#{escape(key,quote=True)}">{escape(title)}</a>' for key,title in headings) + '</nav>'
    def html(items):
        document = {**doc, 'meta':{}, 'blocks':items}
        return pandoc(json.dumps(document), '-f', 'json', '-t', 'html5', '--mathml', '--wrap=none')
    return ('<div class="cv-detail"><p class="eyebrow">Academic background</p><h1>Curriculum vitae</h1>\n'
            + html(intro) + '<p><a class="button" href="files/cv.pdf">Download CV (PDF) ↓</a></p>\n'
            + nav + '\n' + html(sections) + '\n</div>')


def build(tex, template, output):
    body = render_body(tex)
    source = template.read_text(encoding='utf-8')
    pattern = r'(<main\b(?=[^>]*\bdata-cv-content(?:\s|>))[^>]*>).*?(</main>)'
    if len(re.findall(pattern, source, flags=re.S)) != 1:
        raise ValueError('cv.html must contain exactly one <main ... data-cv-content> element.')
    result = re.sub(pattern, lambda m: m[1]+'\n<!-- Generated from CV.tex. Do not edit CV text here. -->\n'+body+'\n'+m[2], source, count=1, flags=re.S)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(result, encoding='utf-8')
    print(f'Generated {output} from {tex}')


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tex', type=Path, default=root/'CV.tex')
    parser.add_argument('--template', type=Path, default=root/'cv.html')
    parser.add_argument('--output', type=Path, default=root/'cv.html')
    args = parser.parse_args()
    try: build(args.tex, args.template, args.output)
    except (ValueError, OSError) as error: parser.exit(1, f'CV generation failed: {error}\n')

if __name__=='__main__': main()
