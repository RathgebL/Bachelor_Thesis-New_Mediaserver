#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# --- Imports ---
import os, sys, re, unicodedata, tkinter as tk
from tkinter import filedialog
from pathlib import Path
from PIL import Image
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

# --- Utilities ---
def ask_terminal_mode() -> bool:
    while True:
        ans = input("Im Terminal ausführen (kein GUI)? [y/N]: ").strip().lower()
        if ans in ("y", "yes", "j", "ja"):
            return True
        if ans in ("n", "no", ""):
            return False
        print("Bitte 'y' oder 'n' eingeben.")

def choose_directory(prompt: str, terminal: bool = False) -> Path:
    if terminal:
        while True:
            path = input(f"{prompt}: ").strip()
            if not path:
                print("Abbruch: Kein Verzeichnis eingegeben.")
                sys.exit(1)
            p = Path(path).expanduser()
            if p.exists() and p.is_dir():
                return p
            else:
                print("Pfad existiert nicht oder ist kein Verzeichnis, bitte erneut eingeben.")
    else:
        root = tk.Tk()
        root.withdraw()
        path = filedialog.askdirectory(title=prompt)
        if not path:
            print(f"Abbruch: Kein Verzeichnis gewählt für {prompt}")
            sys.exit(1)
        return Path(path)

def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s or "")

def norm_text(s: str) -> str:
    s = s.replace("_", " ")
    s = s.replace("--", "—")
    s = re.sub(r"\b[oO][pP]\.?\s*", "op. ", s)
    s = s.replace("Nº", "No")
    s = re.sub(r"\b(?:no|nr)\.?\s*(\d+)(?=\D|$)", r"Nr. \1", s, flags=re.IGNORECASE)
    return s

def smart_titlecase(s: str) -> str:
    # Wandelt komplett großgeschriebene Strings in Title Case um
    if not s or not s.isupper():
        return s

    def fix_word(word: str) -> str:
        w = word.capitalize()

        # Apostrophe: d'Arc → d'Arc, O'Neill → O'Neill
        w = re.sub(r"([DdOo])'([A-Za-z])",
                   lambda m: m.group(1).lower() + "'" + m.group(2).upper(),
                   w)

        # Bindestriche: LIVE-KONZERT → Live-Konzert
        if "-" in word:
            parts = [fix_word(p) for p in word.split("-")]
            return "-".join(parts)
        
        # Pluszeichen: BACH+VIVALDI → Bach+Vivaldi
        if "+" in word:
            return "+".join(fix_word(p) for p in word.split("+"))

        return w

    return " ".join(fix_word(w) for w in s.split())

def norm_name(s: str) -> str:
    # Normalisierung für Personennamen
    if not s:
        return s
    s = s.replace("_", " ")  # Unterstriche zu Leerzeichen
    s = re.sub(r",\s*(\S)", r", \1", s)  # Nach Komma immer ein Leerzeichen
    s = smart_titlecase(s)  # Falls komplett groß, in Title Case umwandeln
    return s
    
def sort_booklet_files(files: list[Path]) -> list[Path]:
    def sort_key(p: Path):
        name = p.stem.lower()  # Dateiname ohne Endung
        # 1) booklet-b exakt
        if name == "booklet-b":
            return (0, 0)
        # 2) booklet-b + Nummer
        m = re.match(r"booklet-b(\d+)$", name)
        if m:
            return (1, int(m.group(1)))
        # 3) booklet exakt
        if name == "booklet":
            return (2, 0)
        # 4) booklet + Nummer
        m = re.match(r"booklet(\d+)$", name)
        if m:
            return (3, int(m.group(1)))
        # 5) Rest alphabetisch
        return (4, name)
    return sorted(files, key=sort_key)

# --- Booklet Finder ---
def find_booklet_folders(base: Path):
    for folder in base.rglob("*"):
        if folder.is_dir():
            jpegs = []
            for ext in ("*.jpg", "*.jpeg", "*.JPG", "*.JPEG"):
                jpegs.extend(folder.glob(ext))
            # Filter: keine macOS "._"-Dateien
            jpegs = [f for f in jpegs if not f.name.startswith("._")]
            if jpegs:
                yield folder, sort_booklet_files(jpegs)

# --- PDF Builder ---
def build_pdf(folder: Path, images: list[Path], out_dir: Path):
    # Der direkte Elternordner von "booklet" ist immer der Namensgeber
    base_dir = folder.parent
    raw_name = nfc(base_dir.name)

    # Trennen in Komponist und Medientitel
    if "-" in raw_name:
        comp_raw, title_raw = raw_name.split("-", 1)
    else:
        comp_raw, title_raw = raw_name, ""

    # Normalisierung
    comp  = norm_name(comp_raw) if comp_raw else ""
    title = norm_text(title_raw) if title_raw else ""

    # Wieder zusammensetzen
    base_name = f"{comp}-{title}" if title else comp

    # Leerzeichen in Unterstriche wandeln, PDF-Endung anhängen
    pdf_name = f"{base_name.replace(' ', '_')}.pdf"
    out_path = out_dir / pdf_name

    # Warnung, wenn PDF schon existiert
    if out_path.exists():
        print(f"[WARNING] Überspringe {out_path}, Datei existiert bereits.")
        return

    # Bilder laden
    pil_images = []
    for img_path in images:
        try:
            img = Image.open(img_path).convert("RGB")
            pil_images.append(img)
        except Exception as e:
            print(f"[WARNING] Konnte {img_path} nicht laden: {e}")

    if not pil_images:
        print(f"[WARNING] Keine gültigen Bilder in {folder}")
        return

    # PDF speichern
    first, *rest = pil_images
    first.save(out_path, save_all=True, append_images=rest)

# --- Main ---
def main():
    print("\n=== Booklet-PDF Generator ===")

    # Anzahl Threads automatisch bestimmen
    workers = os.cpu_count() or 4
    print(f"Threads automatisch auf {workers} gesetzt (Anzahl CPU-Kerne).")

    # Terminal/GUI Auswahl
    terminal = ask_terminal_mode()

    # Input & Output Ordner auswählen
    base = choose_directory("Basis-Ordner wählen (Input)", terminal)
    out_dir = choose_directory("Ziel-Ordner wählen (Output)", terminal)

    # Alle Booklet-Folder finden
    tasks = list(find_booklet_folders(base))
    if not tasks:
        print("Keine Booklet-Ordner mit JPEGs gefunden.", file=sys.stderr)
        sys.exit(1)

    errors = []
    # Multithreading + Fortschrittsanzeige
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {
            ex.submit(build_pdf, folder, images, out_dir): folder
            for folder, images in tasks
        }
        for fut in tqdm(as_completed(futures), total=len(futures), desc="Erstelle PDFs"):
            folder = futures[fut]
            try:
                fut.result()
            except Exception as e:
                errors.append((folder, str(e)))

    # Zusammenfassung
    if errors:
        print("\nFertig - mit Warnungen/Fehlern:")
        for folder, err in errors[:50]:
            print(f"  - {folder}: {err}")
        if len(errors) > 50:
            print(f"  ... und {len(errors)-50} weitere.")
        sys.exit(2)
    else:
        print("\nFertig - alle PDFs erfolgreich erstellt.")


if __name__ == "__main__":
    main()