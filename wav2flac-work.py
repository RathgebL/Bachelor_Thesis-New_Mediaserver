#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# --- Imports ---
import re, unicodedata, subprocess, sys
import tkinter as tk
from tkinter import filedialog
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from collections import defaultdict
from pathlib import Path
from mutagen.flac import FLAC, Picture
from datetime import datetime

# --- Utilities ---
def ask_options() -> dict:
    # Optonen für die Konvertierung abfragen
    print("\n=== Konverter Optionen ===")
    
    # Anzahl Threads
    while True:
        workers = input("Anzahl Threads (default=4): ").strip()
        if workers == "":
            workers = 4
            break
        elif workers.isdigit():
            workers = int(workers)
            break
        else:
            print("Bitte eine Zahl eingeben.")
    
    # Dry-Run
    dry = input("Dry-Run (nur simulieren)? [y/N]: ").strip().lower()
    dry_run = (dry == "y")
    
    return {
        "workers": workers,
        "dry_run": dry_run,
    }

def choose_directory(prompt: str) -> Path: # GUI-Dialog zur Verzeichnisauswahl
    root = tk.Tk()
    root.withdraw()  # Kein Hauptfenster
    path = filedialog.askdirectory(title=prompt)
    if not path:
        print(f"Abbruch: Kein Verzeichnis gewählt für {prompt}")
        sys.exit(1)
    return Path(path)

def nfc(s: str) -> str: # Unicode-Normalisierung (NFC) für Umlaute auf macOS
    return unicodedata.normalize("NFC", s or "")

def norm_name(s: str) -> str: # Normalisierung für Personennamen
    s = s.replace("_", " ") # Unterstriche zu Leerzeichen
    s = re.sub(r",\s*(\S)", r", \1", s) # Nach Komma immer ein Leerzeichen
    return s

def norm_text(s: str) -> str: # Normalisierung für Titel, Alben und Werke
    s = s.replace("_", " ") # Unterstriche zu Leerzeichen
    s = s.replace("--", "—") # Doppelter Bindestrich zu einfachem Bindestrich
    s = re.sub(r"\b[oO][pP]\.?\s*", "op. ", s) # Opus vereinheitlichen 
    # Nummer vereinheitlichen
    s = s.replace("Nº", "No")
    s = re.sub(r"\b(?:no|nr)\.?\s*(\d+)(?=\D|$)", r"Nr. \1", s, flags=re.IGNORECASE) 
    return s

# --- Classifier ---
def classify_path(wav_path: Path) -> str: # Klassifikation des Pfads: "single", "box" oder "unknown"
    parts = [p.name for p in wav_path.parents] # Liste der Ordnernamen im Pfad
    if "EinzelCDs" in parts:
        return "single"
    elif "Boxen" in parts:
        return "box"
    else:
        return "unknown"    

# --- Parser: EinzelCD ---
def parse_single(wav_path: Path) -> dict:
    work_dir  = wav_path.parent # Komponist,Vorname-Werk
    media_dir = work_dir.parent # Komponist,Vorname-Medientitel

    # Album aus dem Medientitel-Ordner
    m_album = re.match(r"^(?P<comp>[^-]+?)\s*-\s*(?P<album>.+)$", media_dir.name) # Trennt Komponist und Album
    album  = norm_text(nfc(m_album.group("album"))) if m_album else "Unknown Album" # Weist Album zu, wenn nicht gefunden "Unknown Album"

    # Werktitel und Komponist aus dem Werk-Ordner
    m_work = re.match(r"^(?P<comp>[^-]+?)\s*-\s*(?P<work>.+)$", work_dir.name) # Trennt Komponist und Werk
    work = norm_text(nfc(m_work.group("work"))) if m_work else "" # Weist Werk zu, wenn nicht gefunden leer
    composer = norm_name(nfc(m_work.group("comp"))) if m_work else "Unknown Artist" # Weist Komponist zu, wenn nicht gefunden "Unknown Artist"

    # Titel und Satznummer aus dem Dateinamen
    fname = wav_path.name
    m_num = re.match(r"^(?P<comp>[^-]+?)-(?P<work>.+?)-(?P<num>\d{1,3})-(?P<title>.+?)\.wav$", fname, re.I)
    m_non = re.match(r"^(?P<comp>[^-]+?)-(?P<title>.+?)\.wav$", fname, re.I)

    if m_num:
        title_raw = m_num.group("title")
        movementnumber = m_num.group("num").lstrip("0") # Satznummer ohne führende Nullen
    elif m_non:
        title_raw = m_non.group("title")
        movementnumber = "" # Wenn keine Satznummer, dann leer
    else: # Fallback
        title_raw = Path(fname).stem # Dateiname ohne Endung
        movementnumber = ""   # leer
        print(f"[WARNING] Unbekanntes Muster: {fname}")

    title = norm_text(nfc(title_raw))

    return {
        "artist":         composer, # Komponist als Interpret, da fehlende Info, aber Pflichtangabe
        "albumartist":    composer, # Komponist als Albuminterpret, da fehlende Info, aber Pflichtangabe
        "composer":       composer,
        "album":          album,
        "title":          title,
        "work":           work,
        "movement":       title,
        "movementnumber": movementnumber, 
        "discnumber":     "",
        # tracknumber wird separat vergeben
    }

# --- Parser: Box ---
def parse_box(wav_path: Path) -> dict:
    work_dir = wav_path.parent # Komponist,Vorname-Werk 
    disc_dir = work_dir.parent # Komponist,Vorname-Medientitel_CDNummer
    box_dir  = disc_dir.parent # Komponist,Vorname-BoxTitel

    # Box-Titel aus dem Box-Ordner
    m_box = re.match(r"^(?P<comp>[^-]+?)\s*-\s*(?P<box>.+)$", box_dir.name)
    boxtitle = norm_text(nfc(m_box.group("box"))) if m_box else "Unknown Album"

    # Disc-Titel aus dem Disc-Ordner
    m_disc = re.match(r"^(?P<comp>[^-]+?)\s*-\s*(?P<title>.+?)(?:[._ ]CD(?P<discnum>\d{1,2}))?$", disc_dir.name, re.IGNORECASE)
    disctitle = norm_text(nfc(m_disc.group("title"))) if m_disc else "Unknown Album" # Weist Disc-Titel zu, wenn nicht gefunden "Unknown Album"
    discnumber = m_disc.group("discnum") if m_disc and m_disc.group("discnum") else "" # Weist Discnummer zu, wenn nicht gefunden leer

    # Werktitel aus dem Werk-Ordner
    m_work = re.match(r"^(?P<comp>[^-]+?)\s*-\s*(?P<work>.+)$", work_dir.name) # Trennt Komponist und Werk
    work = norm_text(nfc(m_work.group("work"))) if m_work else "" # Weist Werk zu, wenn nicht gefunden leer
    composer = norm_name(nfc(m_work.group("comp"))) if m_work else "Unknown Artist" # Weist Komponist zu, wenn nicht gefunden "Unknown Artist"

    # Titel aus Dateiname
    fname = wav_path.name
    m_num = re.match(r"^(?P<comp>[^-]+?)-(?P<work>.+?)-(?P<num>\d{1,3})-(?P<title>.+?)\.wav$", fname, re.I)
    m_non = re.match(r"^(?P<comp>[^-]+?)-(?P<work>.+?)-(?P<title>.+?)\.wav$", fname, re.I)

    if m_num:
        title_raw = m_num.group("title")
        movementnumber = m_num.group("num").lstrip("0") # Satznummer ohne führende Nullen
    elif m_non:
        title_raw = m_non.group("title")
        movementnumber = "" # Wenn keine Satznummer, dann leer
    else: # Fallback
        title_raw = Path(fname).stem # Dateiname ohne Endung
        movementnumber = ""   # leer
        print(f"[WARNING] Unbekanntes Muster: {fname}")

    title = norm_text(nfc(title_raw))

    if disctitle == boxtitle:
        # Titel identisch (nur _CDn dran)
        album = boxtitle
        boxset = ""
    else:
        # Titel weicht ab
        album = disctitle
        boxset = boxtitle


    return {
        "artist":         composer, # Komponist als Interpret, da fehlende Info, aber Pflichtangabe
        "albumartist":    composer, # Komponist als Albuminterpret, da fehlende Info, aber Pflichtangabe
        "composer":       composer,
        "album":          album,
        "title":          title,
        "work":           work,
        "movement":       title,
        "movementnumber": movementnumber,
        "discnumber":     discnumber,
        "boxset":         boxset, # bei abweichenden Titeln
        # tracknumber wird separat vergeben
    }

# --- Dispatcher ---
def parse_path(wav_path: Path) -> dict:
    kind = classify_path(wav_path)
    if kind == "single":
        return parse_single(wav_path)
    if kind == "box":
        return parse_box(wav_path)

# --- Tracknumbers ---
def natural_key(name: str): # Natürliche Sortierung: '2' < '10'
    parts = re.split(r'(\d+)', name)
    return [int(p) if p.isdigit() else p.lower() for p in parts]

def assign_tracknumbers(wav_paths: list[Path]) -> dict[Path, str]: # Weist WAV-Dateien Tracknummern zu
    buckets = defaultdict(list)

    for p in wav_paths:
        if p.suffix.lower() != ".wav": # Datein die keine .wav sind, überspringen
            continue
        # Container-Ordner (eine Ebene über dem Werkordner); Fallback: Elternordner
        try:
            container = p.parents[1]
        except IndexError: # Verbesserung möglich
            container = p.parent
        buckets[container].append(p)

    trackmap = {}
    for container, files in buckets.items():
        # stabil sortieren: zuerst Werkordnername, dann natürlicher Dateiname
        files_sorted = sorted(files, key=lambda x: (x.parent.name.lower(), natural_key(x.name)))
        for i, fp in enumerate(files_sorted, start=1):
            trackmap[fp] = str(i)   # Tags: "1","2","3"... (Zero-Pad nur für Dateinamen nötig)
    return trackmap

# --- WAV-Finder ---
def find_wavs(root: Path) -> list[Path]:
    # Findet alle .wav-Dateien rekursiv unter root
    root = Path(root)
    return [p for p in root.rglob("*") if p.is_file() and p.suffix.lower() == ".wav"]

# --- Output-Pfade ---
def out_flac_path(in_wav: Path, in_root: Path, out_root: Path) -> Path:
    # Spiegelt die Ordnerstruktur von in_root -> out_root und ersetzt .wav durch .flac
    rel = in_wav.relative_to(in_root)
    return (out_root / rel).with_suffix(".flac")

# --- ffmpeg-Konvertierung ---
def convert_wav_to_flac(in_wav: Path, out_flac: Path, compression_level: int = 5, dry_run: bool = False) -> None:
    out_flac.parent.mkdir(parents=True, exist_ok=True)
    if dry_run:
        return
    cmd = [
        "ffmpeg", "-y",
        "-i", str(in_wav),
        "-map_metadata", "-1", # Keine Metadaten von der Quelle übernehmen
        "-compression_level", str(compression_level),
        str(out_flac),
    ]

    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"ffmpeg-Konvertierung fehlgeschlagen: {in_wav} -> {out_flac}") from e

# --- Tags schreiben (FLAC/Vorbis-Kommentare) ---
def write_flac_tags(flac_file: Path, tags: dict, dry_run: bool = False) -> None:
    if dry_run:
        return
    audio = FLAC(str(flac_file))

    def setif(key, val):
        if val is not None and val != "":
            audio[key] = [str(val)]

    # Standard
    setif("artist",         tags.get("artist"))
    setif("albumartist",    tags.get("albumartist"))
    setif("composer",       tags.get("composer"))
    setif("album",          tags.get("album"))
    setif("title",          tags.get("title"))
    setif("tracknumber",    tags.get("tracknumber"))
    setif("discnumber",     tags.get("discnumber"))
    # setif("date",           tags.get("date"))        # Daten nicht verfügbar
    # setif("genre",          tags.get("genre"))       # Daten nicht verfügbar

    # Klassik
    setif("work",           tags.get("work"))
    setif("movement",       tags.get("movement"))
    setif("movementnumber", tags.get("movementnumber"))
    setif("boxset",         tags.get("boxset"))

    audio.save()

# --- Cover einbetten ---
def embed_cover_if_present(flac_file: Path, source_wav: Path, dry_run: bool = False) -> None:
    # Container bestimmen (eine Ebene über dem Werk-Ordner)
    kind = classify_path(source_wav)
    if kind == "single":
        container = source_wav.parents[1]
    elif kind == "box":
        container = source_wav.parents[2]
    elif kind == "unknown":
        print(f"[COVER] Kein Medientyp erkannt: {source_wav}")
        return False

    # Kandidaten für Coverbilder
    candidates: list[Path] = [
        container / "booklet" / "booklet-b.jpg",
        container / "booklet" / "booklet-b.jpeg",
    ]

    # Kandidat wählen
    img_path = next((p for p in candidates if p.exists()), None)
    if not img_path:
        print(f"[COVER] Kein Cover gefunden in: {container}")
        return

    if dry_run:
        return

    # MIME aus Endung bestimmen
    ext = img_path.suffix.lower()
    if ext in (".jpg", ".jpeg"):
        mime = "image/jpeg"

    audio = FLAC(str(flac_file))
    pic = Picture()
    pic.type = 3  # Front cover
    pic.mime = mime
    pic.desc = "Cover"

    with open(img_path, "rb") as f:
        pic.data = f.read()

    audio.add_picture(pic)
    audio.save()

# --- Hauptverarbeitung einer Datei ---
def process_one(wav: Path, in_root: Path, out_root: Path, trackmap: dict[Path, str], dry_run: bool = False) -> tuple[Path, str | None]:
    try:
        tags = parse_path(wav)  # wählt intern single/box
        if tags is None:
            return (wav, "Parser gab None zurück")

        tn = trackmap.get(wav)
        if not tn:
            return (wav, "Keine Tracknummer ermittelt")

        tags["tracknumber"] = tn

        # Zielpfad
        out_flac = out_flac_path(wav, in_root=in_root, out_root=out_root)

        # Konvertieren
        convert_wav_to_flac(wav, out_flac, compression_level=5, dry_run=dry_run)

        # Tags schreiben
        write_flac_tags(out_flac, tags, dry_run=dry_run)

        # Cover einbetten
        embed_cover_if_present(out_flac, wav, dry_run=dry_run)

        return (wav, None)
    except Exception as e:
        return (wav, str(e))

# --- Main ---    
def main():
    # Optionen interaktiv abfragen
    opts = ask_options()

    # Ordner auswählen
    input_root = choose_directory("Wähle den Eingabe-Ordner mit WAV-Dateien")
    output_root = choose_directory("Wähle den Ausgabe-Ordner für FLAC-Dateien")
    run_ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
    output_root = output_root / run_ts
    print(f"Ausgabe-Ordner: {output_root}")

    # WAV-Dateien finden
    wavs = find_wavs(input_root)
    if not wavs:
        print("Keine WAV-Dateien gefunden.", file=sys.stderr)
        sys.exit(1)

    # Tracknummern zuweisen
    trackmap = assign_tracknumbers(wavs)

    if not wavs:
        print("Nichts zu tun (alle Zieldateien existieren bereits).")
        sys.exit(0)

    # Verarbeitung mit Fortschrittsanzeige
    errors = []
    with ThreadPoolExecutor(max_workers=opts["workers"]) as ex:
        futures = {ex.submit(process_one, w, input_root, output_root, trackmap, opts["dry_run"]): w for w in wavs}
        for fut in tqdm(as_completed(futures), total=len(futures), desc="Konvertiere"):
            wav, err = fut.result()
            if err:
                errors.append((wav, err))

    # Zusammenfassung
    if errors:
        print("\nFertig - mit Warnungen/Fehlern:")
        for wav, err in errors[:20]:
            print(f"  - {wav}: {err}")
        if len(errors) > 100:
            print(f"  ... und {len(errors)-100} weitere.")
        sys.exit(2)
    else:
        print("\nFertig - alles ok.")


if __name__ == "__main__":
    main()