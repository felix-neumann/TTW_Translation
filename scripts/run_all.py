"""Complete pipeline: extract -> map -> build -> verify.

Usage:
    python scripts/run_all.py --base "C:/Pfad/zum/Projekt"

The base folder must contain:
    English Files/Fallout 3/*.esm          original English FO3 + DLC
    English Files/Fallout New Vegas/*.esm  original English FNV + DLC
    German Files/Fallout 3/*.esm           original German FO3 + DLC
    German Files/Fallout New Vegas/*.esm   original German FNV + DLC
    To Translate/*.esm|*.esp               the TTW plugins to translate
"""
import argparse
import json
import os
import pickle
import sys
import time
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build as build_mod  # noqa: E402
import mapper  # noqa: E402
from extract import extract_to  # noqa: E402
from verify import verify  # noqa: E402

GAMES = (('FO3', 'Fallout 3'), ('FNV', 'Fallout New Vegas'))


def plugins(folder):
    return sorted(os.path.join(folder, n) for n in os.listdir(folder)
                  if n.lower().endswith(('.esm', '.esp')))


def stage_extract(base, exdir, jobs):
    tasks = []
    for lang, folder in (('en', 'English Files'), ('de', 'German Files')):
        os.makedirs(os.path.join(exdir, lang), exist_ok=True)
        for prefix, game in GAMES:
            for p in plugins(os.path.join(base, folder, game)):
                tasks.append((p, os.path.join(exdir, lang, f'{prefix}_{os.path.basename(p)}.pkl')))
    os.makedirs(os.path.join(exdir, 'ttw'), exist_ok=True)
    for p in plugins(os.path.join(base, 'To Translate')):
        tasks.append((p, os.path.join(exdir, 'ttw', os.path.basename(p) + '.pkl')))
    with ProcessPoolExecutor(jobs) as ex:
        for name, n in ex.map(extract_to, *zip(*tasks)):
            print(f'  {name}: {n} Textfelder')


def main():
    ap = argparse.ArgumentParser(description='TTW deutsche Übersetzung erzeugen')
    ap.add_argument('--base', required=True, help='Projektordner mit English Files / German Files / To Translate')
    ap.add_argument('--work', help='Arbeitsordner für Zwischendaten (Standard: <base>/work)')
    ap.add_argument('--out', help='Ausgabeordner für übersetzte Plugins (Standard: <base>/Output)')
    ap.add_argument('--db', help='Ausgabeordner für XML/TSV (Standard: <repo>/databases)')
    ap.add_argument('--translations', default=os.path.join(HERE, '..', 'translations', 'claude_translations.json'))
    ap.add_argument('--skip-extract', action='store_true', help='vorhandene Extrakte im Arbeitsordner wiederverwenden')
    ap.add_argument('--no-verify', action='store_true')
    ap.add_argument('--jobs', type=int, default=os.cpu_count())
    a = ap.parse_args()
    base = os.path.abspath(a.base)
    work = os.path.abspath(a.work or os.path.join(base, 'work'))
    out = os.path.abspath(a.out or os.path.join(base, 'Output'))
    db = os.path.abspath(a.db or os.path.join(HERE, '..', 'databases'))
    exdir = os.path.join(work, 'extract')
    t0 = time.time()

    if not a.skip_extract:
        print('1/4 Texte extrahieren ...')
        stage_extract(base, exdir, a.jobs)

    print('2/4 Deutsche Texte zuordnen ...')
    results, new = mapper.build(exdir)
    with open(os.path.join(work, 'results.pkl'), 'wb') as f:
        pickle.dump(results, f)
    stats = {}
    for v in results.values():
        for _, _, m in v['res']:
            stats[m] = stats.get(m, 0) + 1
    print('  ', stats)

    print('3/4 Plugins und Datenbanken schreiben ...')
    translations = build_mod.load_translations(a.translations)
    gm = build_mod.german_only_gmsts(os.path.join(base, 'English Files', 'Fallout New Vegas', 'FalloutNV.esm'),
                                     os.path.join(base, 'German Files', 'Fallout New Vegas', 'FalloutNV.esm'),
                                     results)
    inject = {'falloutnv.esm': gm}
    summary, missing = build_mod.build(results, os.path.join(base, 'To Translate'), out, db, translations, inject)
    miss_path = os.path.join(work, 'untranslated.json')
    with open(miss_path, 'w', encoding='utf-8') as f:
        json.dump(missing, f, ensure_ascii=False, indent=1)
    if missing:
        print(f'  ACHTUNG: {len(missing)} neue englische Strings ohne Übersetzung -> {miss_path}')
        print('  Übersetzen, in translations/claude_translations.json einfügen und erneut ausführen.')

    if not a.no_verify:
        print('4/4 Ausgabe prüfen ...')
        bad = 0
        for p in plugins(os.path.join(base, 'To Translate')):
            added = {x[0] for x in inject.get(os.path.basename(p).lower(), [])}
            st, errs = verify(p, os.path.join(out, os.path.basename(p)), added)
            bad += len(errs)
            print(f'  {os.path.basename(p)}: {st["records"]} Records, {st["changed_fields"]} geändert, '
                  f'{len(errs)} Fehler {errs[:3] if errs else ""}')
        if bad:
            sys.exit('Prüfung fehlgeschlagen!')
    print(f'Fertig in {time.time() - t0:.0f} s. Plugins: {out}  Datenbanken: {db}')


if __name__ == '__main__':
    main()
