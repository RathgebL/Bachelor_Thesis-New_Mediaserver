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
#
# Erweiterte Optionen:
# --partial : erlaubt das Fortsetzen abgebrochener Übertragungen
# --partial-dir : speichert unfertige Dateien temporär im Unterordner .rsync-partials
# --temp-dir : legt temporäre Upload-Dateien außerhalb des Zielverzeichnisses ab (z. B. /tmp)
# --delay-updates : sorgt dafür, dass Dateien erst nach vollständigem Upload umbenannt/aktiviert werden
#                   → verhindert, dass der Server halbfertige Dateien sieht
# Zusätzliche --exclude-Regeln schließen macOS-spezifische Metadaten aus
rsync -avz --remove-source-files --progress \
  --partial --partial-dir=".rsync-partials" \
  --temp-dir="/tmp" \
  --delay-updates \
  --exclude=".DS_Store" \
  --exclude="._*" \
  --exclude=".Spotlight-V100" \
  --exclude=".Trashes" \
  --exclude=".fseventsd" \
  "$SOURCE/" "$DEST/" >> "$LOGFILE" 2>&1

RSYNC_EXIT=$?

# -------------------------------
# Nachbearbeitung / Aufräumen
# -------------------------------
if [[ $RSYNC_EXIT -eq 0 ]]; then
    echo "$(date '+%F %T') [OK] Upload erfolgreich abgeschlossen." >> "$LOGFILE"

    # Leere Unterordner entfernen (Hauptordner bleibt bestehen)
    find "$SOURCE" -mindepth 1 -type d -empty -delete
    echo "$(date '+%F %T') [CLEANUP] Leere Unterordner entfernt." >> "$LOGFILE"

    # Alte temporäre Teil-Uploads löschen (.rsync-partials)
    # -type f : nur Dateien löschen
    # -mtime +2 : nur Dateien, die älter als 2 Tage sind (zur Sicherheit, falls rsync sie noch braucht)
    # -empty : leere Ordner im Anschluss entfernen
    if [[ -d "$SOURCE/.rsync-partials" ]]; then
        find "$SOURCE/.rsync-partials" -type f -mtime +2 -delete 2>/dev/null
        find "$SOURCE/.rsync-partials" -type d -empty -delete 2>/dev/null
        echo "$(date '+%F %T') [CLEANUP] Alte temporäre rsync-Teildateien entfernt." >> "$LOGFILE"
    fi
else
    echo "$(date '+%F %T') [ERROR] Upload fehlgeschlagen (Exit-Code: $RSYNC_EXIT)." >> "$LOGFILE"
fi

echo "$(date '+%F %T') [INFO] Upload-Vorgang beendet." >> "$LOGFILE"
echo "-------------------------------------------------------" >> "$LOGFILE"