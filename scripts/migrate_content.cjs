// Optional one-time migration of your existing, trusted assets/content.js.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
const out = path.resolve(root, process.argv[2] || 'markdown-migration');
const context = { window: {} };
vm.runInNewContext(fs.readFileSync(path.join(root, 'assets/content.js'), 'utf8'), context, { timeout: 1000 });
const s = context.window.SITE;
if (!s) throw new Error('assets/content.js must define window.SITE.');
const text = v => String(v ?? '').replace(/[\\`*_\[\]<>$]/g, '\\$&');
const link = (label, url) => url ? `[${text(label)}](<${String(url).replace(/[<>\s]/g, encodeURIComponent)}>)` : text(label);
const body = (...lines) => lines.filter(Boolean).join('\n\n') + '\n';
const entries = (items, detail) => (items || []).map(item => body(
  '### ' + link(item.title, item.url), text(detail(item)), text(item.description)
).trimEnd()).join('\n\n');
const pages = {
  about: body('# About me', text(s.introduction), ...(s.biography || []).map(text),
    '## Research interests', (s.interests || []).map(v => '- ' + text(v)).join('\n'),
    '[More about my research →](research.html)', '## Get in touch',
    'I welcome conversations about mathematics and opportunities for research collaboration.'),
  research: body('# Research', '## Research interests', ...(s.research || []).map(r => body('### ' + text(r.title), text(r.text)).trimEnd()),
    '## Publications and preprints',
    (s.papers || []).slice().sort((a,b) => (b.year || 0) - (a.year || 0)).map(p => body(
      '### ' + text(p.title), text(p.authors), [p.venue, p.year].filter(Boolean).map(text).join(' · '),
      (p.links || []).map(l => link(l.label, l.url)).join(' · ')
    ).trimEnd()).join('\n\n') || 'Publications and preprints will appear here.'),
  teaching: body('# Teaching', text(s.teachingIntro), '## Courses and experience',
    entries(s.courses, item => item.detail) || 'Course details and teaching materials will appear here.'),
  notes: body('# Notes and resources', 'Mathematical notes, expository writing, and useful resources.',
    entries(s.notes, item => item.date) || 'Notes and resources will appear here.'),
};
fs.mkdirSync(out, { recursive: true });
for (const [page, content] of Object.entries(pages)) {
  const file = path.join(out, page + '.md');
  fs.writeFileSync(file, content, { flag: 'wx' });
  console.log(path.relative(root, file));
}
