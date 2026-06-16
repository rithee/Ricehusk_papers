import os, re, glob, json, hashlib
from pathlib import Path
import fitz
import pandas as pd

ROOT = Path('.')
OUT = ROOT / 'rice_husk_ash_concrete_extracted_data.xlsx'
SNIP_DIR = ROOT / 'extracted_snippets'
SNIP_DIR.mkdir(exist_ok=True)

REQ_COLS = [
    'source_file','paper_title','year_folder','row_type','mix_id_or_series',
    'cement comp kg/m3','fine agg kg/m3','course agg kg/m3',
    'ricehusk ash % replacement of cement','any other additives used and quality',
    'water cement ratio','comp strength MPA','flexural strength MPA','Split tensile strength MPA',
    'curing age days','extraction_confidence','evidence'
]

KEYWORDS = ['rice husk ash','rha','cement','concrete','mortar','compressive','flexural','split tensile','splitting tensile','mix design','mix proportion','mixture proportion']
BAD_TOPICS = ['asphalt','soil','brick','bioadsorbent','supercapacitor','xylooligosaccharide','biochar from rice husk','brake pad','plants','epoxy composites','silica production']

def clean(s):
    if s is None: return ''
    s = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F]', ' ', str(s))
    return re.sub(r'\s+', ' ', s).strip()

def extract_text(path):
    doc = fitz.open(path)
    pages=[]
    for i, page in enumerate(doc):
        try:
            pages.append(page.get_text('text'))
        except Exception:
            pages.append('')
    meta = doc.metadata or {}
    return '\n'.join(pages), meta, len(doc)

def title_from_text(text, path, meta):
    t = clean(meta.get('title') or '')
    if t and len(t)>8 and not t.lower().startswith('microsoft word'):
        return t[:300]
    # first long line after obvious journal clutter
    lines=[clean(x) for x in text.splitlines()[:80]]
    cand=[]
    for ln in lines:
        if 25 <= len(ln) <= 220 and not re.search(r'^(issn|doi|abstract|received|keywords|vol\.|www\.|http|page|journal)', ln, re.I):
            if any(w in ln.lower() for w in ['rice','husk','ash','concrete','cement','strength','geopolymer','mortar']):
                cand.append(ln)
    return cand[0] if cand else Path(path).stem.replace('_',' ')

def context_around(text, pattern, radius=650):
    m = re.search(pattern, text, flags=re.I)
    if not m: return ''
    a=max(0,m.start()-radius); b=min(len(text),m.end()+radius)
    return clean(text[a:b])

def find_first(patterns, text):
    for pat in patterns:
        m=re.search(pat, text, re.I|re.S)
        if m:
            for g in m.groups():
                if g and re.search(r'\d', g):
                    return clean(g)
    return ''

def find_all_numbers_near(label_patterns, text, unit_required=False, maxn=8):
    vals=[]
    for lp in label_patterns:
        for m in re.finditer(lp, text, re.I):
            win=text[m.start():min(len(text),m.end()+180)]
            nums=re.findall(r'(?<![A-Za-z])\d{1,4}(?:\.\d+)?', win)
            for n in nums:
                try:
                    f=float(n)
                except: continue
                vals.append(n)
    # unique preserving
    out=[]
    for v in vals:
        if v not in out: out.append(v)
    return '; '.join(out[:maxn])

def pct_rha(text):
    vals=[]
    pats=[r'(?:RHA|rice husk ash)[^%\n\.]{0,120}?(\d{1,2}(?:\.\d+)?)\s*%', r'(\d{1,2}(?:\.\d+)?)\s*%[^\n\.]{0,120}?(?:RHA|rice husk ash)']
    for pat in pats:
        for m in re.finditer(pat,text,re.I):
            vals.append(m.group(1))
    # also mix IDs like RHA5/R10 if in mix sections
    out=[]
    for v in vals:
        if v not in out and float(v)<=80: out.append(v)
    return '; '.join(out[:12])

def wc_ratio(text):
    pats=[
        r'(?:w/c|w\/c|water[- ]cement ratio|water to cement ratio|water/cement ratio)[^0-9]{0,60}((?:0\.\d{2,3}|[0-1]\.\d)(?:\s*(?:,|and|to|-)\s*(?:0\.\d{2,3}|[0-1]\.\d))*)',
        r'(?:w/b|w\/b|water[- ]binder ratio|water to binder ratio)[^0-9]{0,60}((?:0\.\d{2,3}|[0-1]\.\d)(?:\s*(?:,|and|to|-)\s*(?:0\.\d{2,3}|[0-1]\.\d))*)',
        r'W/B ratio\s*((?:0\.\d{2,3}|[0-1]\.\d)[^\n]{0,120})'
    ]
    return find_first(pats,text)

def strength_value(kind, text):
    if kind=='comp': labs=[r'compressive strength']
    elif kind=='flex': labs=[r'flexural (?:tensile )?strength', r'modulus of rupture']
    else: labs=[r'split(?:ting)? tensile strength']
    vals=[]
    for lab in labs:
        # values in MPa near label
        for m in re.finditer(lab, text, re.I):
            win=text[m.start():min(len(text),m.end()+350)]
            for n in re.findall(r'(\d{1,3}(?:\.\d+)?)\s*(?:MPa|N/mm2|N/mm²)', win, re.I):
                if 0 < float(n) < 200: vals.append(n)
        # value before label
        for m in re.finditer(r'(\d{1,3}(?:\.\d+)?)\s*(?:MPa|N/mm2|N/mm²)[^\.\n]{0,90}'+lab, text, re.I):
            n=m.group(1)
            if 0<float(n)<200: vals.append(n)
    out=[]
    for v in vals:
        if v not in out: out.append(v)
    return '; '.join(out[:10])

def kg_value(name, text):
    if name=='cement': labels=['cement','OPC','binder']
    elif name=='fine': labels=['fine aggregate','sand']
    else: labels=['coarse aggregate','course aggregate','aggregate']
    vals=[]
    for lab in labels:
        pat = lab + r'[^\n]{0,80}?(\d{2,4}(?:\.\d+)?)\s*(?:kg\s*/?\s*m\s*3|kg/m3|kg/m³|kg m-3|kg\/m³)'
        for m in re.finditer(pat,text,re.I):
            vals.append(m.group(1))
        pat2 = r'(\d{2,4}(?:\.\d+)?)\s*(?:kg\s*/?\s*m\s*3|kg/m3|kg/m³|kg m-3|kg\/m³)[^\n]{0,80}?'+lab
        for m in re.finditer(pat2,text,re.I):
            vals.append(m.group(1))
    out=[]
    for v in vals:
        if v not in out: out.append(v)
    return '; '.join(out[:8])

def other_additives(text):
    adds=[]
    terms=['fly ash','FA','silica fume','GGBS','slag','metakaolin','superplasticizer','SP','marble powder','quarry dust','bagasse ash','coconut shell ash','snail shell ash','corn cob ash','animal bone powder','steel fiber','polypropylene fiber','crumb rubber','recycled aggregate','stone dust','water hyacinth ash','guinea corn husk ash','wood waste ash']
    low=text.lower()
    for term in terms:
        if term.lower() in low:
            # quantity near term
            m=re.search(term.replace(' ','\s+')+r'[^%\n]{0,80}(\d{1,3}(?:\.\d+)?)\s*%', text, re.I)
            if m: adds.append(f'{term} {m.group(1)}%')
            else: adds.append(term)
    out=[]
    for a in adds:
        if a not in out: out.append(a)
    return '; '.join(out[:12])

def table_segments(text):
    # collect chunks around Table/Figure/table captions with relevant terms
    segs=[]
    for m in re.finditer(r'(Table\s*\d+[^\n]{0,160})', text, re.I):
        start=m.start(); end=min(len(text), start+2500)
        nxt=re.search(r'\n\s*(?:Table\s*\d+|Fig\.?\s*\d+|\d+\.\d\s+[A-Z])', text[start+200:end], re.I)
        if nxt: end=start+200+nxt.start()
        seg=clean(text[start:end])
        if any(k in seg.lower() for k in ['mix','cement','aggregate','compressive','flexural','split','tensile','rha','rice husk']):
            segs.append(seg[:1800])
    # fallback contexts
    for pat in [r'mix(?:ture)? proportions?', r'mix design', r'compressive strength', r'flexural strength', r'split(?:ting)? tensile']:
        c=context_around(text,pat,900)
        if c and c not in segs: segs.append(c[:1800])
    return segs[:12]

rows=[]; sources=[]; snippets=[]
for pdf in sorted(glob.glob('**/*.pdf', recursive=True)):
    try:
        text, meta, pages = extract_text(pdf)
    except Exception as e:
        sources.append({'source_file':pdf,'status':f'ERROR {e}','pages':'','paper_title':Path(pdf).stem})
        continue
    title=title_from_text(text,pdf,meta)
    low=text.lower()
    relevance=sum(k in low for k in KEYWORDS)
    is_bad=any(b in Path(pdf).stem.lower() for b in BAD_TOPICS)
    source_status='processed'
    if len(clean(text))<500:
        source_status='no/low extractable text; may need OCR'
    elif relevance<3:
        source_status='processed - likely not relevant to requested concrete dataset'
    sources.append({'source_file':pdf,'status':source_status,'pages':pages,'paper_title':title,'text_chars':len(text),'keyword_score':relevance})
    segs=table_segments(text)
    # save snippets for audit
    if segs:
        snip_path=SNIP_DIR/(hashlib.md5(pdf.encode()).hexdigest()+'.txt')
        snip_path.write_text('\n\n---SEGMENT---\n\n'.join(segs), encoding='utf-8')
    # main study-level row only if potentially relevant and not obviously off-topic
    if relevance>=3 and not is_bad:
        evidence=' | '.join(segs[:3])[:5000]
        row={
            'source_file':pdf,
            'paper_title':title,
            'year_folder':Path(pdf).parts[0] if len(Path(pdf).parts)>1 else '',
            'row_type':'paper-level extracted candidate',
            'mix_id_or_series':'See evidence / source tables',
            'cement comp kg/m3':kg_value('cement', text),
            'fine agg kg/m3':kg_value('fine', text),
            'course agg kg/m3':kg_value('coarse', text),
            'ricehusk ash % replacement of cement':pct_rha(text),
            'any other additives used and quality':other_additives(text),
            'water cement ratio':wc_ratio(text),
            'comp strength MPA':strength_value('comp', text),
            'flexural strength MPA':strength_value('flex', text),
            'Split tensile strength MPA':strength_value('split', text),
            'curing age days':find_first([r'(\d{1,3})\s*days?[^\.\n]{0,80}(?:compressive|flexural|tensile|curing)', r'(?:curing|cured)[^\.\n]{0,80}(\d{1,3})\s*days?'], text),
            'extraction_confidence':'medium' if evidence and (strength_value('comp',text) or kg_value('cement',text) or pct_rha(text)) else 'low',
            'evidence':evidence
        }
        rows.append(row)
    for idx,seg in enumerate(segs,1):
        snippets.append({'source_file':pdf,'paper_title':title,'segment_no':idx,'snippet':seg})

# Ensure requested cols
if not rows:
    rows=[{c:'' for c in REQ_COLS}]
df=pd.DataFrame(rows)
for c in REQ_COLS:
    if c not in df.columns: df[c]=''
df=df[REQ_COLS]

src=pd.DataFrame(sources)
snip=pd.DataFrame(snippets)
readme=pd.DataFrame([
 {'note':'This workbook was generated from all PDF files found under the repository using PyMuPDF text extraction and regex/table-snippet mining.'},
 {'note':'Columns match the requested inputs/outputs. Blank cells mean the value was not reliably machine-extracted from the PDF text.'},
 {'note':'The evidence column and Extraction_Snippets sheet include source text around mix-design/strength tables for verification and manual correction if needed.'},
 {'note':'course agg kg/m3 uses the user requested spelling; it means coarse aggregate kg/m3.'},
 {'note':f'PDFs processed: {len(sources)}; candidate paper-level rows: {len(df)}; snippets: {len(snip)}'}
])
with pd.ExcelWriter(OUT, engine='openpyxl') as writer:
    df.to_excel(writer, index=False, sheet_name='Extracted_Data')
    src.to_excel(writer, index=False, sheet_name='Source_PDFs')
    snip.to_excel(writer, index=False, sheet_name='Extraction_Snippets')
    readme.to_excel(writer, index=False, sheet_name='README')
    # formatting
    for ws in writer.book.worksheets:
        ws.freeze_panes='A2'
        for cell in ws[1]: cell.style='Headline 3'
        for col in ws.columns:
            letter=col[0].column_letter
            if ws.title=='Extracted_Data' and letter in ['P','Q']:
                ws.column_dimensions[letter].width=90
            elif ws.title=='Extraction_Snippets':
                ws.column_dimensions[letter].width=90 if letter=='D' else 30
            else:
                ws.column_dimensions[letter].width=28
print(f'Wrote {OUT.resolve()}')
print(f'PDFs processed: {len(sources)}')
print(f'Candidate rows: {len(df)}')
print(f'Snippets: {len(snip)}')
