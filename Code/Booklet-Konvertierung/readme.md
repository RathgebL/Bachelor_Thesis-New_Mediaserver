# JPG → PDF Booklet-Generator für die HfM Karlsruhe

Ein Python-Skript zur automatisierten Erstellung von PDF-Booklets aus JPEG-Bildern.  
Das Tool wurde für die Medienserver-Umgebung der Hochschule für Musik Karlsruhe entwickelt und wandelt Booklet-Ordner mit Bilddateien (`.jpg` / `.jpeg`) automatisch in sauber benannte PDF-Dateien um.

---

## Funktionsumfang

- Automatische Erkennung aller Booklet-Ordner (rekursiv)
- Zusammenführung von JPEG-Seiten zu einem PDF pro Booklet
- Automatische Benennung nach dem übergeordneten Medienordner  
- Unterstützung von Sonderzeichen und Unicode-Normalisierung (macOS-kompatibel)
- Parallele Verarbeitung mehrerer Booklets (ThreadPoolExecutor)
- Fortschrittsanzeige mit `tqdm`
- Terminal- oder GUI-Modus für die Auswahl von Input- und Output-Ordnern
- Warnung bei bereits existierenden PDF-Dateien (Überspringen statt Überschreiben)

---

## Voraussetzungen

- Python 3.9 oder neuer
- Abhängigkeiten (Installation per `requirements.txt`):

```bash
pip install -r requirements.txt --upgrade
```

### Erforderliche Pakete
```txt
Pillow
tqdm
tkinter
```

(`tkinter` ist in der Regel in Standard-Python-Installationen bereits enthalten)

---

## Nutzung

Script starten:

```bash
python3 booklet2pdf.py
```

Beim Start erfolgt eine interaktive Abfrage:

1. **Ausführungsmodus**
   - `y` → Terminalmodus (Pfadangaben manuell eingeben)  
   - `n` oder Enter → GUI-Modus (Ordnerauswahl per Dialog)

2. **Ordnerauswahl**
   - Eingabe-Ordner: Basisverzeichnis, in dem nach Booklet-Ordnern gesucht wird
   - Ausgabe-Ordner: Zielverzeichnis, in dem die erzeugten PDFs gespeichert werden

Die PDFs werden nach folgendem Schema benannt:

```
<Komponist>-<Medientitel>.pdf
```

Beispiel:

```
Bach,Johann_Sebastian-Weihnachtsoratorium.pdf
Beethoven,Ludwig_van-Sinfonien_Vol._1.pdf
```

---

## Beispielhafte Eingabestruktur

```
/Volumes/Archiv/EinzelCDs/
└── Bach,Johann_Sebastian-Weihnachtsoratorium/
    └── booklet/
        ├── booklet-b.jpg
        ├── booklet.jpg
        ├── booklet0001.jpg
        └── booklet0002.jpg
```

### Ergebnis (Ausgabe)

```
/Volumes/Media/booklets/
└── Bach,Johann_Sebastian-Weihnachtsoratorium.pdf
```

---

## Sortierlogik der Bilder

Die Reihenfolge der Seiten wird anhand des Dateinamens bestimmt:

1. `booklet-b.jpg` 
2. `booklet.jpg`
3. `booklet0001.jpg`, `booklet0002.jpg`, `booklet0003.jpg`, …  

Diese Reihenfolge sorgt für eine konsistente Seitendarstellung der Booklets.

---

## Bekannte Einschränkungen

- Nur `.jpg` und `.jpeg` werden verarbeitet (keine `.png` oder `.tif`)
- Bereits vorhandene PDF-Dateien werden übersprungen (nicht überschrieben)
- Fehlerhafte oder nicht lesbare Bilder werden mit Warnungen übersprungen
- Die maximale Dateigröße pro Booklet hängt vom Arbeitsspeicher ab
- Keine automatische Rotation oder Nachbearbeitung der Bilder

---

## Interne Logik (Kurzüberblick)

| Komponente | Zweck |
|-------------|-------|
| `find_booklet_folders()` | Findet alle Ordner mit JPEG-Dateien |
| `sort_booklet_files()` | Sortiert Booklet-Seiten in logischer Reihenfolge |
| `build_pdf()` | Erstellt ein PDF aus den gefundenen Bildern |
| `ThreadPoolExecutor` + `tqdm` | Parallele Verarbeitung mit Fortschrittsanzeige |
| `smart_titlecase()` / `norm_text()` | Normalisierung von Namen und Sonderzeichen |

---

## Lizenz

Dieses Projekt steht unter der MIT-Lizenz.  
Siehe [LICENSE](LICENSE) für weitere Details.