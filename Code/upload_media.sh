#!/bin/bash
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
# -a : Archivmodus (bewahrt Zeitstempel, Rechte etc.)
# -v : Verbose (ausführliche Ausgabe)
# -z : Kompression während der Übertragung
# --remove-source-files : löscht Dateien, wenn erfolgreich übertragen
# --progress : Fortschrittsanzeige (hier ins Log umgeleitet)
# --exclude : ignoriert Systemdateien
rsync -avz --remove-source-files --progress \
  --exclude=".DS_Store" \
  "$SOURCE/" "$DEST/" >> "$LOGFILE" 2>&1

RSYNC_EXIT=$?

# -------------------------------
# Nachbearbeitung
# -------------------------------
if [[ $RSYNC_EXIT -eq 0 ]]; then
    echo "$(date '+%F %T') [OK] Upload erfolgreich abgeschlossen." >> "$LOGFILE"

    # Leere Unterordner entfernen (Hauptordner bleibt bestehen)
    find "$SOURCE" -mindepth 1 -type d -empty -delete
    echo "$(date '+%F %T') [CLEANUP] Leere Unterordner entfernt." >> "$LOGFILE"
else
    echo "$(date '+%F %T') [ERROR] Upload fehlgeschlagen (Exit-Code: $RSYNC_EXIT)." >> "$LOGFILE"
fi

echo "$(date '+%F %T') [INFO] Upload-Vorgang beendet." >> "$LOGFILE"
echo "-------------------------------------------------------" >> "$LOGFILE"