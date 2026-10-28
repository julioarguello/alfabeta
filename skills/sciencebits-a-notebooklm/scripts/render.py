"""The PDF + Markdown of one topic and language from Science Bits capture zips; build.py runs it.

`L10N` holds the interface texts of each language the provider supports, a capability of this
renderer; the topic's own texts (`unit`, `course`) come only from build.py's --config.
"""
import io, json, os, re, sys, zipfile
from bs4 import BeautifulSoup, NavigableString, Tag
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer,
                                Image, PageBreak, KeepTogether, Flowable)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import registerFontFamily

FONT_DIR = '/usr/share/fonts/truetype/dejavu'
pdfmetrics.registerFont(TTFont('DV', os.path.join(FONT_DIR, 'DejaVuSans.ttf')))
pdfmetrics.registerFont(TTFont('DV-B', os.path.join(FONT_DIR, 'DejaVuSans-Bold.ttf')))
pdfmetrics.registerFont(TTFont('DV-I', os.path.join(FONT_DIR, 'DejaVuSans-Oblique.ttf')))
pdfmetrics.registerFont(TTFont('DV-BI', os.path.join(FONT_DIR, 'DejaVuSans-BoldOblique.ttf')))
registerFontFamily('DV', normal='DV', bold='DV-B', italic='DV-I', boldItalic='DV-BI')

L10N = {
    'es': dict(toc='Índice', lesson='Lección', screen='Pantalla', image='Imagen', question='Pregunta',
               options='Opciones', definition='Definición', button='Contenido al pulsar',
               back='↑ Volver al índice', video='Vídeo (ver en la plataforma)',
               intro='Documento generado a partir del libro digital de Science Bits para estudio personal. '
                     'Cada pantalla incluye la captura original y, debajo, su texto completo.'),
    'eu': dict(toc='Aurkibidea', lesson='Ikasgaia', screen='Pantaila', image='Irudia', question='Galdera',
               options='Aukerak', definition='Definizioa', button='Sakatzean agertzen den edukia',
               back='↑ Aurkibidera itzuli', video='Bideoa (plataforman ikusi)',
               intro='Science Bits liburu digitaletik sortutako dokumentua, ikasketa pertsonalerako. '
                     'Pantaila bakoitzak jatorrizko irudia eta, azpian, testu osoa ditu.'),
    'en': dict(toc='Contents', lesson='Lesson', screen='Screen', image='Image', question='Question',
               options='Options', definition='Definition', button='Content shown on click',
               back='↑ Back to contents', video='Video (watch on the platform)',
               intro='Document generated from the Science Bits digital book for personal study. '
                     'Each screen includes the original capture and, below it, its full text.'),
}
PHASES = {
    'es': ['Empezamos', 'Exploramos', 'Explicamos', 'Elaboramos', 'Evaluamos'],
    'eu': ['Ekin', 'Esploratu', 'Erakutsi', 'Egin', 'Ebaluatu', 'Ebaluazioa'],
    'en': ['Engage', 'Explore', 'Explain', 'Elaborate', 'Evaluate'],
}
SUB = str.maketrans('0123456789+-=()', '₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎')
SUP = str.maketrans('0123456789+-=()', '⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾')


def clean(s):
    return re.sub(r'\s+', ' ', s or '').strip()


# ---------- HTML -> Markdown ----------
def inline_md(node):
    """Inline markdown for a node (bold/italic/sub/sup)."""
    out = []
    for ch in node.children:
        if isinstance(ch, NavigableString):
            out.append(str(ch))
        elif isinstance(ch, Tag):
            if ch.name in ('script', 'style', 'svg'):
                continue
            inner = inline_md(ch)
            if ch.name in ('b', 'strong', 'i', 'em'):
                mk = '**' if ch.name in ('b', 'strong') else '*'
                core = inner.strip()
                if core:
                    lead = ' ' if inner[:1].isspace() else ''
                    trail = ' ' if inner[-1:].isspace() else ''
                    out.append('%s%s%s%s%s' % (lead, mk, core, mk, trail))
                else:
                    out.append(inner)
            elif ch.name == 'sub':
                t = inner.strip(); out.append(t.translate(SUB) if all(c in '0123456789+-=()' for c in t) else '_' + t)
            elif ch.name == 'sup':
                t = inner.strip(); out.append(t.translate(SUP) if all(c in '0123456789+-=()' for c in t) else '^' + t)
            elif ch.name == 'br':
                out.append(' ')
            else:
                out.append(inner)
    return re.sub(r'[ \t\r\n]+', ' ', ''.join(out))


def html_to_blocks(html, L):
    """Return a list of (kind, text) blocks. kind in h, p, q, opt, def, cap, li, row, sub."""
    soup = BeautifulSoup(html, 'html.parser')
    blocks = []

    def walk(el):
        for ch in el.children:
            if not isinstance(ch, Tag):
                continue
            cls = ' '.join(ch.get('class', []))
            if ch.name == 'boliche' and 'akt_subap' in cls:
                sn = ch.find('startnum')
                if sn and clean(sn.get_text()):
                    blocks.append(('sub', clean(sn.get_text())))
                continue
            if ch.name == 'boliche' and 'grupo' in cls:
                items = ch.find_all('boliche', class_=re.compile('grupSelectItem|akt_tx_actiu'))
                if items:
                    for it in items:
                        t = clean(inline_md(it))
                        if t:
                            blocks.append(('opt', t))
                    continue
            if ch.name == 'boliche' and 'akt_tx_boton' in cls:
                t = clean(inline_md(ch))
                if t: blocks.append(('li', t))
                continue
            if ch.name == 'boliche' and 'akt_tx_peticio' in cls:
                t = clean(inline_md(ch))
                if t: blocks.append(('q', t))
                continue
            if ch.name == 'boliche' and 'akt_tx_definicio' in cls:
                t = clean(inline_md(ch))
                if t: blocks.append(('def', t))
                continue
            if ch.name == 'boliche' and re.search(r'Video', cls):
                blocks.append(('vid', L['video']))
            if 'piedefoto' in cls:
                t = clean(inline_md(ch))
                if t: blocks.append(('cap', t))
                continue
            if ch.name in ('h1', 'h2', 'h3', 'h4'):
                t = clean(inline_md(ch))
                if t: blocks.append(('h', t))
                continue
            if ch.name in ('ul', 'ol'):
                for li in ch.find_all('li', recursive=False):
                    t = clean(inline_md(li))
                    if t: blocks.append(('li', t))
                continue
            if ch.name == 'table':
                for tr in ch.find_all('tr'):
                    cells = [clean(inline_md(td)) for td in tr.find_all(['td', 'th'])]
                    if any(cells):
                        blocks.append(('row', ' | '.join(cells)))
                continue
            if ch.name in ('div', 'p') and (ch.name == 'p' or 'p' in ch.get('class', [])) \
                    and not ch.find(['div', 'ul', 'ol', 'table']):
                t = clean(inline_md(ch))
                if t: blocks.append(('p', t))
                continue
            walk(ch)

    walk(soup)
    out, seen = [], set()
    for b in blocks:
        if b[0] in ('p', 'def', 'q', 'cap', 'h') and b in seen:
            continue
        seen.add(b)
        out.append(b)
    return out


def blocks_to_md(blocks, L):
    lines = []
    for k, t in blocks:
        if k == 'sub':
            lines.append('**%s)**' % t)
        elif k == 'h':
            lines.append('##### ' + t)
        elif k == 'q':
            lines.append('**%s:** %s' % (L['question'], t))
        elif k == 'opt':
            lines.append('- [ ] ' + t)
        elif k == 'def':
            lines.append('> **%s:** %s' % (L['definition'], t))
        elif k == 'cap':
            lines.append('*%s: %s*' % (L['image'], t))
        elif k == 'vid':
            lines.append('*[%s]*' % t)
        elif k == 'li':
            lines.append('- ' + t)
        elif k == 'row':
            lines.append('| ' + t + ' |')
        else:
            lines.append(t)
    md = []
    for i, ln in enumerate(lines):
        if i and not (ln.startswith(('- ', '| ')) and lines[i - 1].startswith(('- ', '| '))):
            md.append('')
        md.append(ln)
    return '\n'.join(md)


# ---------- lesson structure ----------
def parse_sections(menu, phases):
    """From the lesson index text, get (phase, [(section name, first screen number)])."""
    for entry in menu:
        e = entry.strip()
        for ph in phases:
            if e.startswith(ph + ' ') and re.search(r'\d', e):
                body = e[len(ph):].strip().replace(' - ', ' ')
                pairs = re.findall(r'(.+?)\s+(\d+)(?=\s|$)', body)
                return ph, [(clean(n).strip('- '), int(i)) for n, i in pairs]
    return None, []


def load_lessons(raw, lang):
    lessons = []
    for n in range(1, 30):
        f = os.path.join(raw, 'sb_%s_L%d.zip' % (lang, n))
        if not os.path.exists(f):
            continue
        z = zipfile.ZipFile(f)
        meta = json.loads(z.read('meta.json'))
        if not meta.get('items'):
            print('WARNING: empty capture', f)
            continue
        phase, sections = parse_sections(meta.get('menu', []), PHASES[lang])
        screens, order = {}, []
        for it in meta['items']:
            if it['page'] not in screens:
                screens[it['page']] = []
                order.append(it['page'])
            screens[it['page']].append(it)
        lessons.append(dict(n=n, title=meta['title'], phase=phase, sections=sections, zip=z,
                            screens=[(pid, screens[pid]) for pid in order]))
    return lessons


def section_for(sections, idx):
    name = None
    for s, start in sections:
        if idx >= start:
            name = s
    return name


def btn_label(st):
    return st['label'].split(':', 1)[-1].strip()


# ---------- build ----------
def build(raw, out, lang, prefix):
    L = L10N[lang]
    lessons = load_lessons(raw, lang)
    if not lessons:
        print('no lessons for', lang)
        return
    os.makedirs(out, exist_ok=True)
    base = os.path.join(out, '%s_%s' % (prefix, lang.upper()))

    # --- Markdown ---
    md = ['# %s' % L['unit'], '', '*%s*' % L['course'], '', L['intro'], '', '## %s' % L['toc'], '']
    for les in lessons:
        md.append('- %s %d: %s%s' % (L['lesson'], les['n'], les['title'],
                                    (' (%s)' % les['phase']) if les['phase'] else ''))
    md.append('')
    records = []
    for les in lessons:
        md += ['---', '', '## %s %d: %s' % (L['lesson'], les['n'], les['title'])]
        if les['phase']:
            md += ['', '*%s*' % les['phase']]
        md.append('')
        cur_sec = None
        for idx, (pid, states) in enumerate(les['screens'], 1):
            sec = section_for(les['sections'], idx)
            if sec and sec != cur_sec:
                md += ['### %s' % sec, '']
                cur_sec = sec
            seen, parts = set(), []
            for st in states:
                blocks = html_to_blocks(st['html'], L) if st.get('html') else \
                    ([('p', clean(st['text']))] if clean(st.get('text')) else [])
                new = [b for b in blocks if b not in seen]
                if st['label'] != 'base':   # drop the button's own label
                    new = [b for b in new if clean(b[1]) != btn_label(st)]
                seen.update(blocks)
                parts.append((st, new))
            md += ['#### %s %d.%d' % (L['screen'], les['n'], idx), '']
            for st, new in parts:
                if st['label'] != 'base' and new:
                    md += ['', '**%s — %s**' % (L['button'], btn_label(st)), '']
                if new:
                    md.append(blocks_to_md(new, L))
            md.append('')
            records.append((les, idx, sec, parts))
    text = '\n'.join(md)
    while '\n\n\n' in text:
        text = text.replace('\n\n\n', '\n\n')
    with open(base + '.md', 'w', encoding='utf-8') as fh:
        fh.write(text)

    # --- PDF ---
    W, H = A4
    margin = 1.6 * cm
    blue, blue2, grey = colors.HexColor('#1f3a68'), colors.HexColor('#2d5aa0'), colors.HexColor('#777777')
    st_title = ParagraphStyle('t', fontName='DV-B', fontSize=24, leading=30, textColor=blue)
    st_sub = ParagraphStyle('s', fontName='DV', fontSize=12, leading=16, textColor=grey)
    st_h1 = ParagraphStyle('h1', fontName='DV-B', fontSize=18, leading=23, textColor=blue, spaceAfter=4)
    st_h2 = ParagraphStyle('h2', fontName='DV-B', fontSize=13, leading=17, textColor=blue2, spaceAfter=4)
    st_h3 = ParagraphStyle('h3', fontName='DV-B', fontSize=10, leading=13, textColor=grey, spaceAfter=4)
    st_p = ParagraphStyle('p', fontName='DV', fontSize=10, leading=14, spaceAfter=4)
    st_q = ParagraphStyle('q', parent=st_p, fontName='DV-B', textColor=blue2)
    st_opt = ParagraphStyle('o', parent=st_p, leftIndent=14, spaceAfter=1)
    st_def = ParagraphStyle('d', parent=st_p, backColor=colors.HexColor('#eef3fb'), borderPadding=5,
                            leftIndent=5, rightIndent=5, spaceBefore=6, spaceAfter=10)
    st_cap = ParagraphStyle('c', parent=st_p, fontName='DV-I', fontSize=9, textColor=grey)
    st_btn = ParagraphStyle('b', parent=st_p, fontName='DV-B', textColor=colors.HexColor('#a0522d'), spaceBefore=10)
    st_toc1 = ParagraphStyle('toc1', parent=st_p, fontName='DV-B', fontSize=11, leading=16, spaceBefore=8)
    st_toc2 = ParagraphStyle('toc2', parent=st_p, fontSize=9.5, leading=13, leftIndent=14, spaceAfter=0)
    st_back = ParagraphStyle('back', parent=st_p, fontSize=8, textColor=blue2, alignment=2)

    def esc(t):
        t = t.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        t = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', t)
        t = re.sub(r'(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])', r'<i>\1</i>', t)
        return t

    class Anchor(Flowable):
        """Registers a named destination + outline (bookmark) entry at this point."""
        def __init__(self, key, title, level):
            super().__init__()
            self.key, self.title, self.level = key, title, level
        def wrap(self, *a):
            return (1, 1)
        def draw(self):
            c = self.canv
            c.bookmarkHorizontal(self.key, 0, 2)
            c.addOutlineEntry(self.title, self.key, level=self.level, closed=self.level > 0)

    story = [Spacer(1, 5 * cm), Paragraph(esc(L['unit']), st_title), Spacer(1, 0.4 * cm),
             Paragraph(esc(L['course']), st_sub), Spacer(1, 1 * cm), Paragraph(esc(L['intro']), st_p),
             PageBreak(), Anchor('toc', L['toc'], 0), Paragraph(esc(L['toc']), st_h1), Spacer(1, 0.3 * cm)]
    for les in lessons:
        story.append(Paragraph('<a href="#L%d" color="#1f3a68">%s %d · %s</a>%s' % (
            les['n'], L['lesson'], les['n'], esc(les['title']),
            (' <font color="#888888" size="9">(%s)</font>' % esc(les['phase'])) if les['phase'] else ''), st_toc1))
        links, last = [], None
        for idx in range(1, len(les['screens']) + 1):
            sec = section_for(les['sections'], idx)
            if sec and sec != last:
                links.append('<a href="#L%d_%d" color="#2d5aa0">%s</a>' % (les['n'], idx, esc(sec)))
                last = sec
        if not links:
            links = ['<a href="#L%d_%d" color="#2d5aa0">%d.%d</a>' % (les['n'], i, les['n'], i)
                     for i in range(1, len(les['screens']) + 1)]
        story.append(Paragraph(' · '.join(links), st_toc2))

    img_w = W - 2 * margin
    cur = None
    for les, idx, sec, parts in records:
        story.append(PageBreak())
        if les is not cur:
            cur = les
            story.append(Anchor('L%d' % les['n'], '%s %d · %s' % (L['lesson'], les['n'], les['title']), 0))
            story.append(Paragraph('%s %d · %s' % (L['lesson'], les['n'], esc(les['title'])), st_h1))
            if les['phase']:
                story.append(Paragraph(esc(les['phase']), st_h3))
        title = '%s %d.%d' % (L['screen'], les['n'], idx) + (' — %s' % sec if sec else '')
        story.append(Anchor('L%d_%d' % (les['n'], idx), title, 1))
        for k, (st, new) in enumerate(parts):
            head = Paragraph(esc(title), st_h2) if k == 0 else \
                Paragraph(esc('%s — %s' % (L['button'], btn_label(st))), st_btn)
            img = Image(io.BytesIO(les['zip'].read(st['file'])))
            img.drawWidth = img_w
            img.drawHeight = img_w * img.imageHeight / img.imageWidth
            story.append(KeepTogether([head, img, Spacer(1, 0.25 * cm)]))
            for kind, t in new:
                if kind == 'sub':
                    story.append(Paragraph('<b>%s)</b>' % esc(t), st_p))
                elif kind == 'q':
                    story.append(Paragraph(esc(t), st_q))
                elif kind == 'opt':
                    story.append(Paragraph('☐ ' + esc(t), st_opt))
                elif kind == 'def':
                    story.append(Paragraph('<b>%s:</b> %s' % (L['definition'], esc(t)), st_def))
                elif kind == 'vid':
                    story.append(Paragraph('[%s]' % esc(t), st_cap))
                elif kind == 'cap':
                    story.append(Paragraph('%s: %s' % (L['image'], esc(t)), st_cap))
                elif kind == 'h':
                    story.append(Paragraph(esc(t), st_h3))
                elif kind in ('li', 'row'):
                    story.append(Paragraph(('• ' if kind == 'li' else '') + esc(t), st_opt))
                else:
                    story.append(Paragraph(esc(t), st_p))
        story.append(Spacer(1, 0.3 * cm))
        story.append(Paragraph('<a href="#toc" color="#2d5aa0">%s</a>' % esc(L['back']), st_back))

    def footer(c, doc):
        c.saveState()
        c.setFont('DV', 8)
        c.setFillColor(colors.HexColor('#888888'))
        c.drawString(margin, 1 * cm, L['unit'])
        c.drawRightString(W - margin, 1 * cm, str(doc.page))
        c.restoreState()

    doc = BaseDocTemplate(base + '.pdf', pagesize=A4, leftMargin=margin, rightMargin=margin,
                          topMargin=margin, bottomMargin=1.6 * cm, title=L['unit'],
                          author='Science Bits (captura para estudio)', subject=L['course'], lang=lang)
    frame = Frame(margin, 1.6 * cm, W - 2 * margin, H - margin - 1.6 * cm, id='f')
    doc.addPageTemplates([PageTemplate(id='p', frames=[frame], onPage=footer)])
    doc.build(story)
    print('built', base + '.pdf', '+ .md,', sum(len(l['screens']) for l in lessons), 'screens,',
          len(lessons), 'lessons')

