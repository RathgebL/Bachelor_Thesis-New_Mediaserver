#!/usr/bin/env bash
# ============================================================
#  Upload-Skript für Medienserver (macOS, Launchd-kompatibel)
#  ------------------------------------------------------------
#  Zweck:
#    - Überträgt neue Medien-Dateien (FLAC, PDF, JPG etc.)
#      aus dem lokalen Upload-Ordner auf den Server.
#    - Wird automatisch per Launchd gestartet.
#    - Arbeitet zuverlässig auch bei eingeschränkter Umgebung.
# ============================================================

# -------------------------------
# Umgebungsvariablen / Sicherheit
# -------------------------------

# Setze absolutes Arbeitsverzeichnis, da Launchd nicht im Desktop-Kontext startet:
cd "/Users/bibliothek/Desktop/_upload-to-server" || {
  echo "$(date '+%F %T') [ERROR] Konnte Upload-Ordner nicht finden oder betreten."
  exit 1
}

# Stelle sicher, dass SSH-Agent bekannt ist (für rsync via SSH)
if [[ -S "$HOME/.ssh/ssh_auth_sock" ]]; then
  export SSH_AUTH_SOCK="$HOME/.ssh/ssh_auth_sock"
fi

# PATH explizit setzen (Launchd hat oft nur /usr/bin:/bin)
# Optional: /opt/homebrew/bin hinzufügen, falls rsync über Homebrew installiert ist
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

# -------------------------------
# Konfiguration
# -------------------------------
SOURCE="/Users/bibliothek/Desktop/_upload-to-server"            # Lokaler Upload-Ordner
DEST="medienserver@193.197.85.23:/srv/incoming_media"           # Ziel auf Server
LOGFILE="/Users/bibliothek/Logs/upload_media.log"               # Lokale Log-Datei

# -------------------------------
# Vorbereitung
# -------------------------------
# Stelle sicher, dass das Logverzeichnis existiert
mkdir -p "$(dirname "$LOGFILE")"

# Stelle sicher, dass die Logdatei existiert
touch "$LOGFILE"

# Trenner für neue Upload-Sitzung im Log
echo "-------------------------------------------------------" >> "$LOGFILE"
echo "$(date '+%F %T') [INFO] Starte Upload-Prozess..." >> "$LOGFILE"

# Prüfen, ob der Upload-Ordner existiert
if [[ ! -d "$SOURCE" ]]; then
    echo "$(date '+%F %T') [ERROR] Upload-Ordner '$SOURCE' nicht gefunden." >> "$LOGFILE"
    exit 1
fi

# Dateien im Upload-Ordner zählen
FILE_COUNT=$(find "$SOURCE" -type f ! -name ".DS_Store" ! -name "._*" | wc -l | tr -d ' ')

# Wenn keine Dateien vorhanden sind, sauber beenden
if [[ "$FILE_COUNT" -eq 0 ]]; then
    echo "$(date '+%F %T') [INFO] Keine Dateien im Upload-Ordner – Upload übersprungen." >> "$LOGFILE"
    exit 0
fi

# Zeitstempel für spätere Dauerberechnung speichern
START_TIME=$(date +%s)

# Statusmeldung mit Dateianzahl im Log
echo "$(date '+%F %T') [INFO] Starte Upload von $FILE_COUNT Dateien aus '$SOURCE'." >> "$LOGFILE"

# Sicherstellen, dass lokales Partial-Verzeichnis existiert
mkdir -p "$SOURCE/.rsync-partials"

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

caffeinate -i rsync -avz --remove-source-files --progress \
  --partial \
  --partial-dir="$SOURCE/.rsync-partials" \
  --temp-dir="/tmp" \
  --delay-updates \
  --exclude=".DS_Store" \
  --exclude="._*" \
  --exclude=".Spotlight-V100" \
  --exclude=".Trashes" \
  --exclude=".fseventsd" \
  "$SOURCE/" "$DEST/" 2>&1 | grep -v "Unable to create partial-dir" >> "$LOGFILE"

RSYNC_EXIT=${PIPESTATUS[0]}

# -------------------------------
# Nachbearbeitung / Aufräumen
# -------------------------------
if [[ $RSYNC_EXIT -eq 0 ]]; then
    echo "$(date '+%F %T') [OK] Upload erfolgreich abgeschlossen." >> "$LOGFILE"

    # Versteckte macOS-Dateien löschen, damit Ordner wirklich leer sind
    find "$SOURCE" -name '.DS_Store' -delete 2>/dev/null
    find "$SOURCE" -name '._*' -delete 2>/dev/null
    find "$SOURCE" -name '.localized' -delete 2>/dev/null

    # Leere Unterordner entfernen (Hauptordner bleibt bestehen)
    find "$SOURCE" -mindepth 1 -type d -empty -delete
    echo "$(date '+%F %T') [CLEANUP] Leere Unterordner entfernt." >> "$LOGFILE"

    # Alte temporäre Teil-Uploads löschen (.rsync-partials)
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