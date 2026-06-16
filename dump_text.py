import glob, re
from pathlib import Path
import fitz

OUT = Path('full_text')
OUT.mkdir(exist_ok=True)

def safe_name(p):
    s = re.sub(r'[^A-Za-z0-9._-]+', '_', p)
    return s[:150]

index = []
for pdf in sorted(glob.glob('**/*.pdf', recursive=True)):
    try:
        doc = fitz.open(pdf)
    except Exception as e:
        index.append((pdf, f'ERROR {e}', 0))
        continue
    parts = []
    for i, page in enumerate(doc):
        parts.append(f'\n===== PAGE {i+1} =====\n')
        try:
            parts.append(page.get_text('text'))
        except Exception:
            parts.append('')
        # try table extraction
        try:
            tabs = page.find_tables()
            for ti, t in enumerate(tabs.tables):
                parts.append(f'\n----- TABLE p{i+1}#{ti+1} -----\n')
                try:
                    rows = t.extract()
                    for r in rows:
                        parts.append(' | '.join('' if c is None else str(c) for c in r))
                except Exception:
                    pass
        except Exception:
            pass
    text = '\n'.join(parts)
    out_name = safe_name(pdf) + '.txt'
    (OUT / out_name).write_text(text, encoding='utf-8')
    index.append((pdf, out_name, len(text)))

with open('full_text/_INDEX.tsv', 'w', encoding='utf-8') as f:
    f.write('pdf\ttxt\tchars\n')
    for pdf, name, n in index:
        f.write(f'{pdf}\t{name}\t{n}\n')
print('done', len(index))
