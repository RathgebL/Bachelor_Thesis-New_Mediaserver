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
if [[ -f "$LOG" && $(stat -c%s "$LOG" 2>/dev/null || stat -f%z "$LOG") -gt $MAXSIZE ]]; then
    mv "$LOG" "${LOG}.1"
    touch "$LOG"
    echo "$(date '+%F %T') [INFO] Logdatei rotiert (zu groß)" >> "$LOG"
fi

# -------------------------------
# Hauptlogik
# -------------------------------
count=0

# Robustes Einlesen von Dateien (Nullbyte-separiert, sicher für Leerzeichen/Umlaute)
find "$INCOMING" -type f -print0 | while IFS= read -r -d '' FILE; do
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
# Aufräumen: versteckte Dateien & leere Ordner
# -------------------------------
# Entfernt macOS-Systemdateien und leert übrig gebliebene Upload-Verzeichnisse
find "$INCOMING" -name '.DS_Store' -delete
find "$INCOMING" -name '._*' -delete
find "$INCOMING" -mindepth 1 -type d -empty -delete
echo "$(date '+%F %T') [CLEANUP] Leere Ordner aus Incoming entfernt." >> "$LOG"

# -------------------------------
# Rechte setzen (Leserechte für nginx/Navidrome)
# -------------------------------
chmod -R o+r "$TARGET_MUSIC" "$TARGET_BOOKLETS" 2>/dev/null
find "$TARGET_MUSIC" "$TARGET_BOOKLETS" -type d -exec chmod o+x {} \; 2>/dev/null

echo "$(date '+%F %T') [INFO] Verarbeitung abgeschlossen." >> "$LOG"