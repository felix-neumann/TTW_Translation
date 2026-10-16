"""Write the translated plugins and the translation databases (xTranslator XML + TSV)."""
import collections
import csv
import json
import os
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from esm import rewrite  # noqa: E402

LABEL = {
    'record_FNV': 'FNV-Original', 'record_FO3': 'FO3-Original',
    'gmst_FNV': 'FNV-Original', 'gmst_FO3': 'FO3-Original',
    'dict_FNV': 'FNV-Woerterbuch', 'dict_FO3': 'FO3-Woerterbuch',
    'norm_FNV': 'FNV-Woerterbuch', 'norm_FO3': 'FO3-Woerterbuch',
    'changed_FNV': 'FNV-Original (EN-Text von TTW/YUP leicht geaendert)',
    'changed_FO3': 'FO3-Original (EN-Text von TTW/YUP leicht geaendert)',
    'gmst_changed_FNV': 'FNV-Original (EN-Text von TTW/YUP leicht geaendert)',
    'gmst_changed_FO3': 'FO3-Original (EN-Text von TTW/YUP leicht geaendert)',
    'new': 'Neu uebersetzt (Claude)',
}


def nl(s):
    return s.replace('\r\n', '\n')


def load_translations(path):
    """claude_translations.json: [{en, de, context, editor_id}]; de = null means keep English."""
    with open(path, encoding='utf-8') as f:
        return {nl(x['en']): x['de'] for x in json.load(f)}


def build(results, src_dir, out_dir, db_dir, translations, log=print):
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(os.path.join(db_dir, 'xTranslator'), exist_ok=True)
    names = {n.lower(): n for n in os.listdir(src_dir) if n.lower().endswith(('.esm', '.esp'))}
    missing = collections.OrderedDict()
    summary = {}
    tsv_path = os.path.join(db_dir, 'TTW_Deutsch_alle_Texte.tsv')
    with open(tsv_path, 'w', encoding='utf-8-sig', newline='') as tsv:
        w = csv.writer(tsv, delimiter='\t', lineterminator='\n')
        w.writerow(['Plugin', 'FormID', 'EditorID', 'Record', 'Feld', 'Index', 'Englisch', 'Deutsch', 'Quelle'])

        def esc(s):
            return nl(s).replace('\n', '\\n').replace('\t', '\\t')

        for lname, v in sorted(results.items()):
            fname = names[lname]
            repl = collections.defaultdict(dict)
            rows = []
            count = collections.Counter((e[3], e[5]) for e, _, _ in v['res'])
            for e, de, m in v['res']:
                t, o, oid, fid, edid, s, i, txt = e
                if m == 'new':
                    key = nl(txt)
                    if key not in translations:
                        missing.setdefault(key, {'en': key, 'de': None, 'context': [], 'editor_id': edid})
                        ctx = f'{t}:{s}'
                        if ctx not in missing[key]['context']:
                            missing[key]['context'].append(ctx)
                        continue
                    de = translations[key]
                    if de is None:
                        continue  # intentionally kept English (IDs, binary data)
                    if '\r\n' in txt:
                        de = nl(de).replace('\n', '\r\n')
                if de is None or de == txt:
                    continue
                if t == 'NOTE' and s == 'TNAM' and len(txt.encode('cp1252')) == 3:
                    continue  # FormID of an audio holotape, not text
                repl[fid][(s, i)] = de.encode('cp1252')
                rows.append((fid, edid, t, s, i, count[(fid, s)] - 1, txt, de, m))
            st = rewrite(os.path.join(src_dir, fname), os.path.join(out_dir, fname), repl)
            summary[fname] = dict(st, entries=len(rows))
            log(f'  {fname}: {st["records"]} Records, {st["fields"]} Textfelder ersetzt')

            root = ET.Element('SSTXMLRessources')
            p = ET.SubElement(root, 'Params')
            for k, val in (('Addon', os.path.splitext(fname)[0]), ('Source', 'english'),
                           ('Dest', 'german'), ('Version', '2')):
                ET.SubElement(p, k).text = val
            c = ET.SubElement(root, 'Content')
            for fid, edid, t, s, i, imax, en, de, m in rows:
                node = ET.SubElement(c, 'String', List='0')
                if m == 'new':
                    node.set('Partial', '1')  # shown as "incomplete" in xTranslator -> easy to review
                ET.SubElement(node, 'EDID').text = edid if edid else '[%08X]' % fid
                rec = ET.SubElement(node, 'REC')
                rec.text = f'{t}:{s}'
                if imax > 0:
                    rec.set('id', str(i))
                    rec.set('idMax', str(imax))
                ET.SubElement(node, 'Source').text = en
                ET.SubElement(node, 'Dest').text = de
                w.writerow([fname, '%08X' % fid, edid, t, s, i, esc(en), esc(de), LABEL[m]])
            ET.indent(root)
            ET.ElementTree(root).write(
                os.path.join(db_dir, 'xTranslator', f'{os.path.splitext(fname)[0]}_english_german.xml'),
                encoding='UTF-8', xml_declaration=True)
    return summary, list(missing.values())
