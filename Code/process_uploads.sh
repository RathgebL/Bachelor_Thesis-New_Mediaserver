#!/bin/bash
# ============================================================
# Medienserver Upload-Verarbeitung
# Verschiebt neue Uploads aus /incoming in die passende Zielstruktur
# und sorgt für korrekte Rechte & Logging
# ============================================================

INCOMING="/srv/incoming_media"
TARGET_MUSIC="/mnt/media/music"
TARGET_BOOKLETS="/mnt/media/booklets"
LOG="/srv/logs/process.log"

# -------------------------------
# Vorbereitung
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
if [[ -f "$LOG" && $(stat -c%s "$LOG") -gt $MAXSIZE ]]; then
    mv "$LOG" "${LOG}.1"
    touch "$LOG"
    echo "$(date '+%F %T') [INFO] Logdatei rotiert (zu groß)" >> "$LOG"
fi

# -------------------------------
# Hauptlogik
# -------------------------------
count=0

find "$INCOMING" -type f | while read -r FILE; do
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

    # Datei verschieben
    if mv "$FILE" "$DEST"; then
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
# Rechte setzen (Leserechte für nginx/Navidrome)
# -------------------------------
chmod -R o+r "$TARGET_MUSIC" "$TARGET_BOOKLETS" 2>/dev/null
find "$TARGET_MUSIC" "$TARGET_BOOKLETS" -type d -exec chmod o+x {} \; 2>/dev/null

echo "$(date '+%F %T') [INFO] Verarbeitung abgeschlossen." >> "$LOG"