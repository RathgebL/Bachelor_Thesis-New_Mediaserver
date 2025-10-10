#!/bin/bash
# ============================================================
#  Medienserver Upload-Verarbeitung
#  ------------------------------------------------------------
#  Zweck:
#    - Verschiebt neue Uploads aus /incoming in die passende Zielstruktur.
#    - Setzt korrekte Rechte & führt Logrotation durch.
#    - Entfernt leere oder temporäre Upload-Ordner nach erfolgreicher Verarbeitung.
# ============================================================

INCOMING="/srv/incoming_media"         # Eingangsverzeichnis (Uploads)
TARGET_MUSIC="/mnt/media/music"        # Zielverzeichnis für FLAC-Dateien
TARGET_BOOKLETS="/mnt/media/booklets"  # Zielverzeichnis für PDFs
LOG="/srv/logs/process.log"            # Logdatei

# -------------------------------
# Vorbereitung & Logrotation
# -------------------------------
mkdir -p "$(dirname "$LOG")"
touch "$LOG"

# Wenn keine Dateien im Incoming-Ordner, sofort beenden
if ! find "$INCOMING" -type f | grep -q .; then
    echo "$(date '+%F %T') [INFO] Keine neuen Dateien – Skript übersprungen." >> "$LOG"
    exit 0
fi

# Logrotation ab ~50 KB (einfacher Schutz gegen Überlauf)
MAXSIZE=50000  # ~50 KB
if [[ -f "$LOG" && $(stat -c%s "$LOG" 2>/dev/null || stat -f%z "$LOG") -gt $MAXSIZE ]]; then
    mv "$LOG" "${LOG}.1"
    touch "$LOG"
    echo "$(date '+%F %T') [INFO] Logdatei rotiert (zu groß)" >> "$LOG"
fi

# -------------------------------
# Hauptlogik
# -------------------------------
count=0
MIN_AGE=60  # Sekunden, die eine Datei unverändert sein muss (z. B. 60s)

# Robustes Einlesen von stabilen Dateien (nicht jünger als MIN_AGE)
find "$INCOMING" -type f -mmin +$((MIN_AGE/60)) \
     ! -path "*/.rsync-partials/*" \
     ! -name ".*.tmp" \
     ! -name "*.part" \
     ! -name ".*" \
     -print0 | while IFS= read -r -d '' FILE; do

    ((count++))
    REL_PATH="${FILE#$INCOMING/}"

    # Dateityp prüfen
    if [[ "$FILE" == *.flac ]]; then
        DEST="$TARGET_MUSIC/$REL_PATH"
    elif [[ "$FILE" == *.pdf ]]; then
        DEST="$TARGET_BOOKLETS/$REL_PATH"
    else
        echo "$(date '+%F %T') [SKIP] Unbekannter Typ: $FILE" >> "$LOG"
        continue
    fi

    # Zielverzeichnis anlegen
    mkdir -p "$(dirname "$DEST")"

    # Datei verschieben (atomar)
    if mv -n "$FILE" "$DEST"; then
        echo "$(date '+%F %T') [OK] Verschoben: $FILE → $DEST" >> "$LOG"
    else
        echo "$(date '+%F %T') [ERROR] Konnte Datei nicht verschieben: $FILE" >> "$LOG"
    fi
done

# -------------------------------
# Wenn keine Dateien gefunden
# -------------------------------
if [[ $count -eq 0 ]]; then
    echo "$(date '+%F %T') [INFO] Keine neuen Dateien gefunden." >> "$LOG"
fi

# -------------------------------
# Aufräumen: versteckte Dateien & leere Ordner
# -------------------------------
# Entfernt macOS-Systemdateien und leert übrig gebliebene Upload-Verzeichnisse
find "$INCOMING" -name '.DS_Store' -delete 2>/dev/null
find "$INCOMING" -name '._*' -delete 2>/dev/null
find "$INCOMING" -mindepth 1 -type d -empty -delete 2>/dev/null
echo "$(date '+%F %T') [CLEANUP] Leere Ordner aus Incoming entfernt." >> "$LOG"

# -------------------------------
# Rechte setzen (Leserechte für nginx/Navidrome)
# -------------------------------
chmod -R o+r "$TARGET_MUSIC" "$TARGET_BOOKLETS" 2>/dev/null
find "$TARGET_MUSIC" "$TARGET_BOOKLETS" -type d -exec chmod o+x {} \; 2>/dev/null

# -------------------------------
# Abschlussmeldung
# -------------------------------
echo "$(date '+%F %T') [INFO] Verarbeitung abgeschlossen." >> "$LOG"
echo "-------------------------------------------------------" >> "$LOG"