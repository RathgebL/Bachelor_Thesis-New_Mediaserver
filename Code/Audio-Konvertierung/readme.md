# WAV → FLAC Konverter für die HfM Karlsruhe

Ein Python-Skript zur automatisierten Konvertierung und Metadaten-Anreicherung von WAV-Dateien für die Bibliothek der Hochschule für Musik Karlsruhe.  
Die FLAC-Dateien werden dabei inklusive Tags und eingebettetem Coverbild erzeugt.  
Metadaten wie Komponist, Werk, Album, Satznummer, Box-Titel und Booklet-URL werden automatisch aus der bestehenden Ordnerstruktur und den Dateinamen abgeleitet.

---

## Funktionsumfang

- Automatische Konvertierung von `.wav` nach `.flac` mittels `ffmpeg`
- Automatische Metadaten-Erkennung aus Ordnerstruktur und Dateinamen:
  - Komponist, Werk, Titel, Album, Satznummer, Disc-Nummer, Box-Set, Booklet-URL
- Automatische Cover-Einbettung  
  - bevorzugt `booklet/booklet-b.jpg` oder `.jpeg`  
  - Fallback: `booklet/booklet.jpg` oder `.jpeg`
- Natürliche Tracknummern-Zuordnung (sortiert pro Werk/Ordner)
- Unicode- und Text-Normalisierung (z. B. für Umlaute und Opus-/Nr./Vol.-Formate)
- Mehrkern-Verarbeitung (ThreadPoolExecutor) für parallele Konvertierung
- Fortschrittsanzeige mit `tqdm`
- Dry-Run-Modus (Simulation ohne Dateierzeugung für Testläufe)
- Terminal- oder GUI-Modus (Dateiauswahl über Eingabe oder Dialogfenster)
- Zeitgestempelter Ausgabeordner (`YYYY-MM-DD_HH-MM`), damit keine bestehenden Dateien überschrieben werden
- Automatische Booklet-Verknüpfung:  
  `bookleturl` und `subtitle` erhalten die URL `http://medien.hfm.eu/booklets/<Komponist>-<Album>.pdf`

---

## Voraussetzungen

- Python 3.9 oder neuer  
- Installierte Systemabhängigkeit: [`ffmpeg`](https://ffmpeg.org/download.html)
- Python-Pakete (siehe `requirements.txt`):

```bash
pip install -r requirements.txt --upgrade
```

### Empfohlene Pakete
```txt
mutagen
tqdm
```
(`tkinter` ist bei Standard-Python-Installationen bereits enthalten)

---

## Nutzung

Script starten:

```bash
python3 wav2flac-work.py
```

Beim Start erfolgt eine interaktive Abfrage:

1. **Ausführungsmodus**
   - `y` → Terminalmodus (Pfadangaben manuell eingeben)  
   - `n` oder Enter → GUI-Modus (Ordnerauswahl per Dialog)

2. **Dry-Run**
   - `y` → Simulation, keine Dateien werden erstellt  
   - `n` oder Enter → echte Konvertierung

Danach werden der Eingabe- und Ausgabeordner gewählt.  
Der Ausgabeordner wird automatisch mit Zeitstempel erzeugt, z. B.:

```
/Volumes/Archiv/FLAC-Ausgabe/2025-10-11_14-20_EinzelCDs/
```

---

## Beispielhafte Eingabestruktur

```
2025-09-15/
├── EinzelCDs/
│   └── Brahms,Johannes-21_Lieder/
│       └── Brahms,Johannes-Über_die_Heide,_op._86_No._4/
│           └── Brahms-Über_die_Heide,_op._86_No._4.wav
└── Boxen/
    └── Bach,Johann_Sebastian-WEIHNACHTSORATORIUM/
        ├── Bach,Johann_Sebastian-WEIHNACHTSORATORIUM._CD1/
        │   └── Bach,Johann_Sebastian-Kantate_Nr._1_(Am_ersten_Weihnachtsfeiertage)
        │       └── Bach,Johann_Sebastian-Kantate_Nr._1_(Am_ersten_Weihnachtsfeiertage).wav
        └── Bach,Johann_Sebastian-WEIHNACHTSORATORIUM._CD2/
            └── Bach,Johann_Sebastian-Kantate_Nr._2_(Am_zweiten_Weihnachtsfeiertage)
                └── Bach,Johann_Sebastian-Kantate_Nr._2_(Am_zweiten_Weihnachtsfeiertage).wav
```

### Ausgabe (automatisch erzeugt)

```
FLAC-Ausgabe/2025-09-15-to-2025-10-11_14-20/
├── EinzelCDs/
│   └── Brahms,Johannes-21_Lieder/
│       └── Brahms,Johannes-Über_die_Heide,_op._86_No._4/
│           └── Brahms-Über_die_Heide,_op._86_No._4.flac
└── Boxen/
    └── Bach,Johann_Sebastian-WEIHNACHTSORATORIUM/
        ├── Bach,Johann_Sebastian-WEIHNACHTSORATORIUM._CD1/
        │   └── Bach,Johann_Sebastian-Kantate_Nr._1_(Am_ersten_Weihnachtsfeiertage)
        │       └── Bach,Johann_Sebastian-Kantate_Nr._1_(Am_ersten_Weihnachtsfeiertage).flac
        └── Bach,Johann_Sebastian-WEIHNACHTSORATORIUM._CD2/
            └── Bach,Johann_Sebastian-Kantate_Nr._2_(Am_zweiten_Weihnachtsfeiertage)
                └── Bach,Johann_Sebastian-Kantate_Nr._2_(Am_zweiten_Weihnachtsfeiertage).flac
```

---

## Bekannte Einschränkungen

- Nur `.jpg` und `.jpeg`-Cover werden erkannt (keine `.png`- oder `.tif`-Dateien)
- Booklet-URL ist fest codiert (`http://medien.hfm.eu/booklets/…`)
- Metadaten wie Dirigent, Genre oder Jahr sind derzeit nicht belegt
- Unbekannte Dateinamensmuster erzeugen Warnungen im Terminal
- `ffmpeg` muss im System-PATH verfügbar sein

---

## Interne Logik (Kurzüberblick)

| Komponente | Zweck |
|-------------|-------|
| `classify_path()` | Erkennung, ob „Einzel-CD“ oder „Box-Set“ |
| `parse_single()` / `parse_box()` | Extrahieren von Metadaten aus Pfad und Dateinamen |
| `assign_tracknumbers()` | Fortlaufende Tracknummern pro Werkordner |
| `convert_wav_to_flac()` | ffmpeg-basierte Umwandlung |
| `write_flac_tags()` | Schreiben der FLAC-Metadaten (mutagen) |
| `embed_cover()` | Einbettung des Covers aus dem jeweiligen `booklet`-Unterordner |
| `ThreadPoolExecutor` + `tqdm` | Parallele Verarbeitung mit Fortschrittsanzeige |

---

## Lizenz

Dieses Projekt steht unter der MIT-Lizenz.  
Siehe [LICENSE](LICENSE) für weitere Details.