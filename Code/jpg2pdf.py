#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# --- Imports ---
import sys, re, unicodedata, tkinter as tk
from tkinter import filedialog
from pathlib import Path
from PIL import Image

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
    # Pfad bestimmen
    base_dir = folder.parent
    base_name = norm_text(nfc(base_dir.name))

    # Leerzeichen in Unterstriche wandeln, PDF-Endung anhängen
    pdf_name = f"{base_name.replace(' ', '_')}.pdf"
    out_path = out_dir / pdf_name

    # Warnung, wenn PDF schon existiert
    if out_path.exists():
        print(f"[WARNING] Überspringe {out_path}, Datei existiert bereits.")
        return
    print(f"[INFO] Erstelle PDF: {out_path}")

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
    terminal = ask_terminal_mode()
    base = choose_directory("Basis-Ordner wählen (Input)", terminal)
    out_dir = choose_directory("Ziel-Ordner wählen (Output)", terminal)

    for folder, images in find_booklet_folders(base):
        build_pdf(folder, images, out_dir)

if __name__ == "__main__":
    main()