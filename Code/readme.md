# WAV → FLAC Konverter

Ein Python-Script, das WAV-Dateien rekursiv in FLAC-Dateien konvertiert.  
Metadaten (Komponist, Werk, Album, Titel, Satznummer, Discnummer, Box-Set, Coverbilder) werden automatisch aus der Ordnerstruktur und den Dateinamen abgeleitet.

## Features

- **Automatische Konvertierung** von `.wav` nach `.flac` mit `ffmpeg`
- **Automatische Tag-Befüllung** (Komponist, Werk, Titel, Album, Discnummer, etc.)
- **Cover-Einbettung**, wenn ein Coverbild (`booklet/booklet-b.jpg` oder `.jpeg`) vorhanden ist
- **Natürliche Tracknummern-Zuordnung** pro Ordner
- **Unicode-Normalisierung** (für Umlaute, macOS-kompatibel)
- **Dry-Run Modus** (Simulation ohne Änderungen)
- **Terminal- oder GUI-Modus**: wahlweise Pfadeingabe im Terminal oder mit Dateiauswahldialog
- **Ausgabeordner mit Zeitstempel** (`YYYY-MM-DD_HH-MM`), sodass keine bestehenden Dateien überschrieben und neue Dateien ordentlich verpackt werden.

## Voraussetzungen

- Python **3.9+**
- Installierte Systemabhängigkeit: [`ffmpeg`](https://ffmpeg.org/download.html)
- Python-Pakete (siehe `requirements.txt`):

```bash
pip3 install -r requirements.txt --upgrade
```

## Nutzung

Script starten:

```bash
python3 wav2flac-work.py
```

Beim Start wirst du nach folgenden Optionen gefragt:

1. **Terminal oder GUI-Modus**
   - Terminalmodus: Pfade werden direkt eingegeben
   - GUI-Modus: Auswahlfenster für Eingabe-/Ausgabeordner

2. **Dry-Run**
   - `y`: Simulation, keine Dateien werden erzeugt
   - `n` oder Enter: normale Konvertierung

Danach wählst du Eingabe- und Ausgabeordner.  
Die Ausgabedateien landen automatisch in einem neuen Unterordner mit Zeitstempel, z. B.:

```
/media/user/Musik/2025-09-09_11-24/EinzelCDs/...
/media/user/Musik/2025-09-09_11-24/Boxen/...
```

## Beispiel Ordnerstruktur (Input)

```
2025-09-15/EinzelCDs/
└── Brahms,Johannes-21_Lieder/
    └── Brahms,Johannes-Über_die_Heide,_op._86_No._4/
        └── Brahms-Über_die_Heide,_op._86_No._4.wav

2025-09-15/Boxen/
└── Bach,Johann_Sebastian-WEIHNACHTSORATORIUM/
    └── Bach,Johann_Sebastian-WEIHNACHTSORATORIUM._CD1/
        └── Bach,Johann_Sebastian-Kantate_Nr._1_(Am_ersten_Weihnachtsfeiertage).wav
```

## Bekannte Einschränkungen

- Nur `booklet/booklet-b.jpg` oder `.jpeg` werden als Cover erkannt (erweiterbar)
- `ffmpeg` muss im Systempfad verfügbar sein
- Unbekannte Dateinamenmuster können nicht richtig bearbeitet werden und erzeugen eine Warnung

## Lizenz

Dieses Projekt steht unter der MIT Lizenz – siehe [LICENSE](LICENSE).

