#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re, unicodedata
from collections import defaultdict
from pathlib import Path

# ---------- Utilities ----------
def nfc(s: str) -> str: # Unicode-Normalisierung (NFC) für Umlaute auf macOS
    return unicodedata.normalize("NFC", s or "")

def norm_name(s: str) -> str: # Normalisierung für Personennamen
    s = s.replace("_", " ") # Unterstriche zu Leerzeichen
    s = re.sub(r",\s*(\S)", r", \1", s) # Nach Komma immer ein Leerzeichen
    return s

def norm_text(s: str) -> str: # Normalisierung für Titel, Alben und Werke
    s = s.replace("_", " ") # Unterstriche zu Leerzeichen
    s = re.sub(r"\b[oO][pP]\.?\s*", "op. ", s) # Opus vereinheitlichen 
    # Nummer vereinheitlichen
    s = s.replace("Nº", "No")
    s = re.sub(r"\b(?:no|nr)\.?\s*(\d+)(?=\D|$)", r"Nr. \1", s, flags=re.IGNORECASE) 
    return s

# ---------- Classifier ----------
def classify_path(wav_path: Path) -> str: # Klassifikation in "box" oder "single"
    parts = [p.name for p in wav_path.parents] # Liste der Ordnernamen
    if "Boxen" in parts:
        return "box"
    if "EinzelCDs" in parts:
        return "single"

# ---------- Parser: EinzelCD ----------
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

# ---------- Parser: Box ----------
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

# ---------- Dispatcher ----------
def parse_path(wav_path: Path) -> dict:
    kind = classify_path(wav_path)
    if kind == "single":
        return parse_single(wav_path)
    if kind == "box":
        return parse_box(wav_path)

# ---------- Tracknumbers ----------
def _natural_key(name: str):
    """Natürliche Sortierung: '2' < '10'."""
    parts = re.split(r'(\d+)', name)
    return [int(p) if p.isdigit() else p.lower() for p in parts]

def assign_tracknumbers(wav_paths: list[Path]) -> dict[Path, str]:
    """
    Vergibt pro CD/Disc (Container) fortlaufende Tracknummern.
    Container = eine Ebene über dem Werkordner → wav_path.parents[1]
    (z. B. .../EinzelCDs/<CD-Ordner>/<Werk-Ordner>/<Datei.wav>
           .../Boxen/<Box>/<Disc-Ordner>/<Werk-Ordner>/<Datei.wav>)
    Rückgabe: { wav_path: "1", ... }
    """
    buckets = defaultdict(list)

    for p in wav_paths:
        if p.suffix.lower() != ".wav":
            continue
        # Container-Ordner (eine Ebene über dem Werkordner); Fallback: Elternordner
        try:
            container = p.parents[1]
        except IndexError:
            container = p.parent
        buckets[container].append(p)

    trackmap = {}
    for container, files in buckets.items():
        # stabil sortieren: zuerst Werkordnername, dann natürlicher Dateiname
        files_sorted = sorted(files, key=lambda x: (x.parent.name.lower(), _natural_key(x.name)))
        for i, fp in enumerate(files_sorted, start=1):
            trackmap[fp] = str(i)   # Tags: "1","2","3"... (Zero-Pad nur für Dateinamen nötig)
    return trackmap

# ---------- WAV-Finder ----------
def find_wavs(root: Path) -> list[Path]:
    # Findet alle .wav-Dateien rekursiv unter root
    root = Path(root)
    return [p for p in root.rglob("*") if p.is_file() and p.suffix.lower() == ".wav"]

# ---------- Output-Pfade ----------
def out_flac_path(in_wav: Path, in_root: Path, out_root: Path) -> Path:
    # Spiegelt die Ordnerstruktur von in_root -> out_root und ersetzt .wav durch .flac
    rel = in_wav.relative_to(in_root)
    return (out_root / rel).with_suffix(".flac")