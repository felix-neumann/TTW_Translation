# TTW German Translation

Werkzeuge und Text-Datenbanken, um **Tale of Two Wastelands (TTW)** mit den **offiziellen deutschen Texten** aus Fallout 3 und Fallout: New Vegas auszustatten.

Die Skripte lesen die englischen und deutschen Original-Plugins beider Spiele, ordnen jedem Text in den TTW-Plugins die passende offizielle deutsche Fassung zu und schreiben übersetzte Plugins. Texte, die es nur in TTW gibt, kommen aus einer eigenen Übersetzungsdatei.

Getestet mit **TTW 3.4** und **YUPTTW 13.9.1**. Benötigt wird nur **Python 3.10 oder neuer**, ohne zusätzliche Pakete.

## Inhalt

| Pfad | Inhalt |
|---|---|
| `scripts/run_all.py` | Komplette Pipeline (Extrahieren → Zuordnen → Schreiben → Prüfen) |
| `scripts/esm.py` | Lesen/Schreiben von FO3/FNV-Plugins (`.esm`/`.esp`) |
| `scripts/extract.py` | Extrahiert alle übersetzbaren Textfelder eines Plugins |
| `scripts/mapper.py` | Entscheidet pro Textfeld, welcher deutsche Text verwendet wird |
| `scripts/build.py` | Schreibt die übersetzten Plugins und die Datenbanken |
| `scripts/verify.py` | Prüft, dass sich im Ausgabe-Plugin nur Textfelder geändert haben |
| `scripts/tools.py` | Hilfen für neue Übersetzungen: Glossar, Prüfung, Zusammenführen |
| `translations/claude_translations.json` | Übersetzungen der Texte, die es nur in TTW/YUP gibt |
| `databases/xTranslator/*.xml` | Übersetzung pro Plugin im xTranslator-XML-Format |
| `databases/TTW_Deutsch_alle_Texte.tsv` | Alle Texte in einer Tabelle (Englisch, Deutsch, Quelle) |

Spiel-Plugins (`.esm`/`.esp`) sind **nicht** im Repo enthalten.

## Ordnerstruktur vorbereiten

Lege einen Projektordner mit folgender Struktur an:

```
Projekt/
├── English Files/
│   ├── Fallout 3/            Fallout3.esm, Anchorage.esm, BrokenSteel.esm, PointLookout.esm, ThePitt.esm, Zeta.esm
│   └── Fallout New Vegas/    FalloutNV.esm, DeadMoney.esm, HonestHearts.esm, OldWorldBlues.esm, LonesomeRoad.esm,
│                             GunRunnersArsenal.esm, CaravanPack.esm, ClassicPack.esm, MercenaryPack.esm, TribalPack.esm
├── German Files/
│   ├── Fallout 3/            dieselben Dateien aus der deutschen Version
│   └── Fallout New Vegas/    dieselben Dateien aus der deutschen Version
└── To Translate/             die TTW-Plugins aus deiner Installation
                              (Fallout3.esm, FalloutNV.esm, alle DLCs, TaleOfTwoWastelands.esm, YUPTTW.esm, ...)
```

Wichtig: In `To Translate` gehören die **von TTW installierten** Versionen der Dateien, nicht die Originale. TTW verändert auch die Master-Dateien der Spiele.

**Weitere Mods (optional):** Plugins anderer Mods kommen nach `To Translate/Mods/`. Sie werden nach den TTW-Dateien übersetzt und landen in `Output/Mods/`. Für sie gilt dieselbe Reihenfolge wie unten beschrieben, ergänzt um unsere TTW-Übersetzung. Ändert eine Mod einen TTW-Record, bekommt sie dieselbe deutsche Fassung wie TTW selbst. Mods, die auf anderen Mods aufbauen (z. B. `WRP - TTW.esp` auf `Weapon Retexture Project.esp`), werden nach ihren Mastern verarbeitet und übernehmen deren Übersetzung. Bereits deutsche Texte in Mods werden in `claude_translations.json` mit `"de": null` markiert und bleiben unverändert.

## Benutzung

```bash
python scripts/run_all.py --base "C:/Pfad/zum/Projekt"
```

Das dauert etwa eine Minute. Ergebnis:

- `Projekt/Output/`: die übersetzten Plugins. Sie ersetzen die gleichnamigen TTW-Dateien im Mod-Manager.
- `Projekt/Output/Mods/`: die übersetzten Mod-Plugins (falls `To Translate/Mods` existiert). Die XMLs dazu liegen in `databases/xTranslator/Mods/`.
- `databases/`: aktualisierte xTranslator-XMLs und TSV.
- `Projekt/work/`: Zwischendaten. Mit `--skip-extract` werden sie bei weiteren Läufen wiederverwendet, das spart Zeit.
- `Projekt/work/untranslated.json`: neue englische Texte ohne Übersetzung (siehe unten).

Weitere Optionen:

```
--out <Ordner>         Ausgabeordner für Plugins       (Standard: <base>/Output)
--db <Ordner>          Ausgabeordner für XML/TSV       (Standard: <repo>/databases)
--work <Ordner>        Ordner für Zwischendaten        (Standard: <base>/work)
--skip-extract         vorhandene Extrakte wiederverwenden
--no-verify            Prüfung am Ende überspringen
--jobs <n>             parallele Prozesse beim Extrahieren
```

Die Originaldateien in `To Translate` werden nie verändert.

## Wie die deutschen Texte ausgewählt werden

Für jedes Textfeld gilt diese Reihenfolge:

1. **Ursprungs-Record:** Gibt es den Record im Originalspiel mit identischem englischem Text, wird dessen offizieller deutscher Text verwendet, egal ob aus FO3 oder FNV. So bleiben Geschlecht ("Soldat" bzw. "Soldatin") und Anrede (du bzw. Sie) korrekt.
2. **Wörterbuch:** Kommt derselbe englische Text anderswo übersetzt vor, wird **FNV vor FO3** bevorzugt. Gesucht wird zuerst im gleichen Record-Typ und Feld, dann überall, dann ohne Beachtung von Leerzeichen und Groß-/Kleinschreibung.
3. **Leicht geänderter Text:** Hat TTW/YUP den englischen Text nur korrigiert (mindestens 80 % ähnlich und gleiche Zahlen), wird die deutsche Fassung des Originals verwendet. Bei umgeschriebenen oder umfunktionierten Records (z. B. Karmatitel, geänderte Prozentwerte) passiert das bewusst nicht.
4. **Neu:** Alle anderen Texte kommen aus `translations/claude_translations.json`.

Dazu kommen **Spieleinstellungen (GMST), die es nur in den deutschen Mastern gibt**: Hauptmenü ("Neu", "Laden", "Optionen", "Abbrechen" ...), Tastenbelegung, Hacking-Bildschirm und Ähnliches. Die englische Version nimmt diese Texte direkt aus der EXE, die deutsche überschreibt sie über die ESM. Ausgewählt wird über die EditorID: alle Text-Einstellungen der deutschen `FalloutNV.esm`, ergänzt um die aus der deutschen `Fallout3.esm`, die FNV nicht hat (Dialog-Knöpfe und Tastennamen der deutschen Tastatur). Ausgenommen sind Einstellungen, die TTW oder YUP selbst setzen; die laufen über die normale Zuordnung. Sie werden als **neue GMST-Records** in die übersetzte `FalloutNV.esm` eingefügt (aktuell 1.265). Viele deutsche GMSTs nutzen FormIDs, die im englischen Master schon anderen Records gehören; diese bekommen neue FormIDs ab `0x180000`. Das ist unproblematisch, weil das Spiel Einstellungen über die EditorID sucht. In der TSV stehen sie mit der Quelle `DE-Original (nur im DE-Master, als neuer Record ergaenzt)`. In den xTranslator-XMLs fehlen sie, weil xTranslator nur vorhandene Texte übersetzt und keine Records hinzufügt.

Technische Details:
- TTW stellt den FO3-Dateien die New-Vegas-Master voran. Deshalb werden FormIDs über ihre Master-Liste auf das Ursprungs-Plugin zurückgerechnet und nicht direkt verglichen.
- Spieleinstellungen (GMST) werden über die EditorID zugeordnet.
- Texte sind in cp1252 kodiert. Einige Records in FalloutNV.esm haben fehlerhafte zlib-Prüfsummen und werden ohne Prüfsummenkontrolle entpackt.
- Unveränderte Records werden Byte für Byte kopiert. Ohne Änderungen ist die Ausgabe identisch mit der Eingabe.
- Die Prüfung am Ende stellt sicher, dass sich nur Textfelder geändert haben und außer den ergänzten GMSTs keine Records hinzugekommen sind.

## Nach einem TTW- oder YUP-Update

1. Neue TTW-Plugins nach `To Translate` kopieren und `run_all.py` ausführen.
2. Meldet das Skript `ACHTUNG: … neue englische Strings ohne Übersetzung`, öffne `work/untranslated.json` und trage bei jedem Eintrag unter `"de"` die Übersetzung ein. Lass `"de": null` stehen, wenn der Text englisch bleiben soll, etwa bei internen Bezeichnern.
3. Offizielle Begriffe findest du mit dem Glossar:
   ```bash
   python scripts/tools.py glossary --work "C:/Pfad/zum/Projekt/work" "^Sniper Rifle$" "Bobblehead"
   ```
4. Übersetzungen übernehmen, prüfen und neu bauen:
   ```bash
   python scripts/tools.py merge "C:/Pfad/zum/Projekt/work/untranslated.json"
   python scripts/tools.py check
   python scripts/run_all.py --base "C:/Pfad/zum/Projekt" --skip-extract
   ```

`tools.py check` prüft, dass alle Übersetzungen in cp1252 darstellbar sind und Platzhalter wie `%.0f`, `%g` oder `%%` erhalten bleiben.

## Die Datenbanken mit xTranslator nutzen

- In xTranslator das Plugin laden, dann **Import → xTranslator XML** und die passende Datei aus `databases/xTranslator/` wählen.
- Von Claude neu übersetzte Texte sind mit `Partial="1"` markiert und erscheinen als "unvollständig". So lassen sie sich gezielt prüfen.
- Danach kann xTranslator die Übersetzung als eigenes `.sst`-Wörterbuch speichern.

In der TSV-Datei zeigt die Spalte `Quelle`, woher jeder Text stammt: `FNV-Original`, `FO3-Original`, `FNV-Woerterbuch`, `FO3-Woerterbuch`, `… (EN-Text von TTW/YUP leicht geaendert)` oder `Neu uebersetzt (Claude)`. Zeilenumbrüche stehen dort als `\n`.

## Deutsche Audiodateien außerhalb der Sprach-Archive

Einige deutsche Aufnahmen übersehen Tools, die nur `sound\voice\` in den Sprach-Archiven austauschen:

| Archiv (TTW) | Was | Pfad | Dateien |
|---|---|---|---|
| `Fallout3 - Sound.bsa` | Intro-Übergänge in Vault 101 ("10 Jahre später" ...) | `sound\fx\qst\qst_fadetowhite_a`–`d.wav` | 4 |
| `Fallout3 - Sound.bsa` | Notrufsignal im Radio | `sound\fx\voc\radio\` | 3 |
| `Fallout3 - Sound.bsa` | Liberty Prime | `sound\fx\voc\robotlibertyprime\combat\` | 32 |
| `BrokenSteel - Sounds.bsa` | Liberty Prime, Übergang | `sound\fx\voc\robotlibertyprime\dlc03\`, `qst_fadetowhite_e.wav` | 11 |
| `PointLookout - Sounds.bsa` | Laute des Kindes | `sound\fx\voc\dlc04malechild\` | 4 |
| `YUPTTW - Sounds.bsa` | von YUP durch englische Aufnahmen ersetzte FNV-Sprachzeilen | `sound\voice\falloutnv.esm\...` | 36 |

Zwei Skripte decken das ab. Benötigt wird [BSArch](https://www.nexusmods.com/newvegas/mods/64745).

**1. Analyse:** `scripts/sound_analyze.py` vergleicht alle Dateien unter `sound\` in den TTW-Archiven mit den deutschen Original-Archiven des jeweiligen Spiels. Bei TTW-eigenen Archiven wird in beiden Spielen gesucht. Ergebnis pro Archiv: identisch, unterschiedlich oder nicht im deutschen Original.

```bash
python scripts/sound_analyze.py --de "<Ordner mit deutschen BSAs>" --ttw "<Ordner mit TTW-BSAs>" --out report.json
```

"Unterschiedlich" heißt nicht automatisch englisch, denn Sprach-Tools kodieren deutsche Dateien oft neu. `scripts/audio_info.py` liefert die Laufzeit von WAV/OGG. Neu kodiertes Deutsch ist genauso lang wie das Original, englische Aufnahmen weichen ab. TTW legt FO3-Stimmtypen zusätzlich als `...dc`-Ordner an (z. B. `femaleadult04dc`); deren deutsches Gegenstück liegt im Ordner ohne `dc`.

**2. Ersetzen:** `scripts/sound_fix.py` übernimmt die deutschen Fassungen in ein TTW-Archiv: Jede Datei, die in beiden vorkommt und sich unterscheidet, optional gefiltert per `--include`/`--exclude` (reguläre Ausdrücke, Kleinschreibung, `/`). Danach wird das Archiv mit denselben Flags neu gepackt und Datei für Datei geprüft.

```bash
python scripts/sound_fix.py --de "<DE FO3>/Fallout - Sound.bsa" --ttw "<TTW>/Fallout3 - Sound.bsa" --bsarch BSArch.exe --out Audio
python scripts/sound_fix.py --de "<DE FO3>/BrokenSteel - Sounds.bsa" --ttw "<TTW>/BrokenSteel - Sounds.bsa" --bsarch BSArch.exe --out Audio --exclude "^sound/fx/amb/"
python scripts/sound_fix.py --de "<DE FO3>/PointLookout - Sounds.bsa" --ttw "<TTW>/PointLookout - Sounds.bsa" --bsarch BSArch.exe --out Audio
python scripts/sound_fix.py --de "<DE FNV>/Fallout - Voices1.bsa" --ttw "<YUP>/YUPTTW - Sounds.bsa" --bsarch BSArch.exe --out Audio --include "^sound/voice/"
```

Bewusst **nicht** ersetzt: Geräusche ohne Sprache, die TTW/YUP nur neu kodiert oder absichtlich getauscht hat (Wasser, Türen, Endgame-Musik, Waffen, Todesschreie). Die neuen BSAs ersetzen in MO2 die gleichnamigen Archive: Mod mit den BSAs **unter** TTW, YUP und deinen Sprach-Mod setzen.

## Ladereihenfolge in einem manuell gepflegten Spielverzeichnis

Fallout 3 und New Vegas ignorieren die Reihenfolge in `plugins.txt`/`loadorder.txt` und sortieren Plugins nach dem **Änderungsdatum** der Dateien (ESM vor ESP). MO2 setzt die Daten in seinem virtuellen Data-Ordner passend zur LOOT-Reihenfolge. Kopierst du Dateien in ein eigenes Spielverzeichnis, z. B. für ein Steam Deck, oder schreibt die Pipeline neue Plugins, stimmen die Daten dort nicht mehr. `scripts/set_load_order.py` setzt sie wie MO2: 01.01.2000 plus ein Tag je Position. Das Skript ändert nur das Datum, nie den Inhalt, und läuft auch unter Linux.

```bash
python scripts/set_load_order.py --loadorder "<MO2>/profiles/Default/loadorder.txt" --data "<Spiel>/Data"
python scripts/set_load_order.py --loadorder ... --data ... --check    # nur prüfen
```

Nach dem Kopieren auf ein anderes Gerät mit `--check` prüfen, ob die Daten erhalten geblieben sind.

## Konvertierte Fallout-3-Plugins: Header-Version

TTW meldet beim Start "Nicht konvertierte Mod!", sobald ein geladenes Plugin eine Header-Version unter 1.3 hat. Fallout-3-Plugins haben 0.94. Die Konvertierung mit FNVEdit (TTW-Master hinzufügen, TTW-Konvertierungsskript) ändert diesen Wert nicht, deshalb lösen auch korrekt konvertierte Plugins die Meldung aus. `scripts/set_header_version.py` setzt die Version auf 1.34. Geändert werden nur die 4 Bytes im Header, Dateigröße und Datum bleiben gleich:

```bash
python scripts/set_header_version.py --backup "<Sicherungsordner>" "<Pfad>/MeinPlugin.esp"
```

Alternativ in FNVEdit vor dem Speichern `File Header → HEDR → Version` auf 1.34 setzen.

## Spielen ohne MO2 (z. B. auf dem Steam Deck)

Wer das Setup aus MO2 in ein eigenes Spielverzeichnis kopiert, etwa um es auf ein Steam Deck zu übertragen, verliert ein paar Dinge, die MO2 im Hintergrund erledigt. Die folgenden Punkte haben wir in der Praxis gefunden. `scripts/check_gamedir.py` prüft sie alle.

```bash
python scripts/check_gamedir.py --game "<...>/Fallout New Vegas" --inis "<...>/My Games/FalloutNV" ^
                                --loadorder "<MO2>/profiles/Default/loadorder.txt"
```

**1. Archiv-Invalidierung.** Mit `bInvalidateOlderFiles=1` gewinnen lose Dateien gegen ein Archiv nur, wenn sie **neuer** sind als das Archiv. Kopierte Archive tragen das Kopierdatum, Mod-Dateien ihr altes Originaldatum. Ohne Invalidierungs-BSA verlieren deshalb Hunderte Mod-Dateien still gegen die Archive. Bei uns waren es 692 aus WRP, TTW Texture Merge, Bueno, NoScopeWobble, Litter Fix und MCM. Ein Symptom waren rote Ausrufezeichen statt Granaten. MO2 trägt die Invalidierungs-BSA selbst ein. Ohne MO2 muss sie in der `Fallout.ini` **und** der `FalloutPrefs.ini` stehen:

```ini
[Archive]
SInvalidationFile=
bInvalidateOlderFiles=1
SArchiveList=Fallout - Invalidation.bsa, Fallout - Textures.bsa, Fallout - Textures2.bsa, Fallout - Meshes.bsa, Fallout - Voices1.bsa, Fallout - Sound.bsa, Fallout - Misc.bsa
```

`Fallout - Invalidation.bsa` (von MO2 angelegt) bzw. `Fallout - AII-FNV!.bsa` muss im `Data`-Ordner liegen und **in der Liste stehen**. Liegt sie nur im Ordner, ist sie wirkungslos. Eine `ArchiveInvalidation.txt` wird damit nicht gebraucht.

**2. Wo die INIs liegen.** Das Spiel liest die INIs nicht aus dem Spielordner:

| Datei | Windows | Steam Deck (Proton) |
|---|---|---|
| `Fallout.ini`, `FalloutPrefs.ini`, `FalloutCustom.ini` | `Dokumente\My Games\FalloutNV\` | `…/compatdata/<ID>/pfx/drive_c/users/steamuser/Documents/My Games/FalloutNV/` |
| `plugins.txt` | `%LOCALAPPDATA%\FalloutNV\` | `…/compatdata/<ID>/pfx/drive_c/users/steamuser/AppData/Local/FalloutNV/` |

Die INIs aus dem MO2-Profil lassen sich übernehmen, mit einer Ausnahme: `SLocalSavePath=__MO_Saves\` ist MO2-intern und muss `Saves\` werden.

**3. Schreibgeschützte `Fallout.ini`.** Fehlt die `Fallout.ini`, erzeugt das Spiel sie als Kopie der `Fallout_default.ini`, teils schreibgeschützt. Darüber kopierte INIs kommen dann nicht an, ohne dass es auffällt: Das Spiel läuft mit Standardwerten, `sLanguage=ENGLISH` und ohne Invalidierungs-BSA.

**4. Vorlagen im Installationsordner absichern.** Damit neu erzeugte INIs gleich stimmen, z. B. bei einem neuen Proton-Ordner oder nach dem Zurücksetzen im Launcher:
- `Fallout_default.ini`: `sLanguage=GERMAN` und den `[Archive]`-Block von oben setzen.
- `low.ini`, `medium.ini`, `high.ini`, `VeryHigh.ini`: Aus ihnen schreibt der Launcher die `FalloutPrefs.ini`. Den `[Archive]`-Block ergänzen und `iTexMipMapSkip=0` setzen, sonst lädt "Niedrig" alle Texturen in halber Auflösung.

**5. Ladereihenfolge.** Plugins werden nach Dateidatum geladen, siehe `set_load_order.py`. Nach jedem Kopieren von Plugins erneut ausführen bzw. mit `--check` prüfen.

**6. Kopieren aufs Deck.** Linux unterscheidet Groß- und Kleinschreibung. Kopiert man über eine bestehende Installation, können doppelte Ordner entstehen (`Meshes` neben `meshes`), außerdem bleiben alte Dateien liegen. Am sichersten kopiert man das Verzeichnis einmal in einen **leeren** Ordner.

**Texture-Packs prüfen:** `scripts/pack_check.py` zeigt für eigene Pack-Mods in MO2, ob Dateien mehrfach geliefert werden, ob Meshes Texturen aus anderen Packs bekommen, ob Texturen fehlen und welche Pack-Dateien gegen `.override`-Archive verlieren.

## Nicht abgedeckt

- Sprachausgabe und Lippensynchronisation
- Texte, die fest in Skripten stehen, sowie Menü- und INI-Dateien von TTW
- Internen Bezeichnern und Referenz-IDs von Audio-Holobändern (diese bleiben bewusst unverändert)

## Rechtliches

Die Spieltexte gehören Bethesda Softworks bzw. ZeniMax Media. Dieses Repo ist nur für den privaten Gebrauch mit legal erworbenen Spielen gedacht. Tale of Two Wastelands und YUP gehören ihren jeweiligen Autoren.
