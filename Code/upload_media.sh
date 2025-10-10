#!/usr/bin/env bash
# ============================================================
#  Upload-Skript für Medienserver (macOS)
#  ------------------------------------------------------------
#  Zweck:
#    - Überträgt neue Medien-Dateien (FLACs, PDFs, JPGs etc.)
#      aus dem lokalen Upload-Ordner auf den zentralen Server.
#    - Erfolgreich übertragene Dateien werden lokal gelöscht.
#    - Logdatei dokumentiert alle Aktionen.
# ============================================================

# -------------------------------
# SSH-Agent aktivieren (macOS-kompatibel)
# -------------------------------
if ! pgrep -u "$USER" ssh-agent >/dev/null; then
    eval "$(ssh-agent -s)" >/dev/null
fi

SSH_KEY="$HOME/.ssh/id_ed25519"

# Falls der Schlüssel noch nicht geladen ist → hinzufügen
if ! ssh-add -l 2>/dev/null | grep -q "$SSH_KEY"; then
    ssh-add "$SSH_KEY"
fi

# -------------------------------
# Konfiguration
# -------------------------------
SOURCE="/Users/bibliothek/Desktop/_upload-to-server"            # Lokaler Upload-Ordner
DEST="medienserver@193.197.85.23:/srv/incoming_media"           # Ziel auf Server
LOGFILE="/Users/bibliothek/Desktop/Logs/upload_media.log"       # Lokale Log-Datei

# -------------------------------
# Vorbereitung
# -------------------------------
mkdir -p "$(dirname "$LOGFILE")"    # Log-Verzeichnis anlegen, falls fehlt
touch "$LOGFILE"                    # Log-Datei sicherstellen

echo "-------------------------------------------------------" >> "$LOGFILE"
echo "$(date '+%F %T') [INFO] Starte Upload-Prozess..." >> "$LOGFILE"

# Prüfen, ob der Upload-Ordner existiert und Dateien enthält
if ! find "$SOURCE" -type f | grep -q .; then
    echo "$(date '+%F %T') [INFO] Keine Dateien im Upload-Ordner – Upload übersprungen." >> "$LOGFILE"
    exit 0
fi

# -------------------------------
# Upload via rsync
# -------------------------------
caffeinate -i rsync -avz --remove-source-files --progress \
  --exclude=".DS_Store" \
  "$SOURCE/" "$DEST/" >> "$LOGFILE" 2>&1

RSYNC_EXIT=$?

# -------------------------------
# Nachbearbeitung
# -------------------------------
if [[ $RSYNC_EXIT -eq 0 ]]; then
    echo "$(date '+%F %T') [OK] Upload erfolgreich abgeschlossen." >> "$LOGFILE"

    # Versteckte Systemdateien löschen, dann leere Verzeichnisse entfernen
    find "$SOURCE" -name '.DS_Store' -delete
    find "$SOURCE" -name '._*' -delete
    find "$SOURCE" -mindepth 1 -type d -empty -delete
    echo "$(date '+%F %T') [CLEANUP] Leere Unterordner entfernt." >> "$LOGFILE"

else
    echo "$(date '+%F %T') [ERROR] Upload fehlgeschlagen (Exit-Code: $RSYNC_EXIT)." >> "$LOGFILE"
fi

# ------------------------------------------
# Serververarbeitung mit Verzögerung starten
# ------------------------------------------
WAIT_SECONDS=60
echo "$(date '+%F %T') [INFO] Warte $WAIT_SECONDS Sekunden, um Dateiabschlüsse zu sichern..." >> "$LOGFILE"
sleep $WAIT_SECONDS

echo "$(date '+%F %T') [INFO] Starte Serververarbeitung (process_incoming.service)..." >> "$LOGFILE"
ssh medienserver@193.197.85.23 "sudo systemctl start process_incoming.service" \
  >> "$LOGFILE" 2>&1

if [[ $? -eq 0 ]]; then
    echo "$(date '+%F %T') [INFO] Server-Job erfolgreich gestartet." >> "$LOGFILE"
else
    echo "$(date '+%F %T') [WARN] Konnte Server-Job nicht starten (Fehler beim SSH-Aufruf)." >> "$LOGFILE"
fi

echo "$(date '+%F %T') [INFO] Upload-Vorgang beendet." >> "$LOGFILE"
echo "-------------------------------------------------------" >> "$LOGFILE"