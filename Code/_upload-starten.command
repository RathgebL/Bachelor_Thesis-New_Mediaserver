#!/bin/bash
# ============================================================
#  Upload-Starter für den Medienserver (per Doppelklick)
# ============================================================

# -------------------------------
# Pfadkonfiguration
# -------------------------------
SCRIPT="/Users/bibliothek/Scripts/upload_media.sh"     # Hauptskript
LOGFILE="/Users/bibliothek/Logs/upload_media_manual.log"  # Log-Datei

# -------------------------------
# Vorbereitung: Log sicherstellen
# -------------------------------
mkdir -p "$(dirname "$LOGFILE")"   # Log-Verzeichnis anlegen, falls nicht vorhanden
touch "$LOGFILE"                   # Leere Log-Datei erstellen (falls nicht existiert)

# -------------------------------
# Startzeit in Log schreiben
# -------------------------------
echo "-------------------------------------------------------" >> "$LOGFILE"
echo "$(date '+%F %T') [INFO] Manuell gestarteter Upload..." >> "$LOGFILE"

# -------------------------------
# Upload ausführen
# -------------------------------
# Führt das eigentliche Upload-Skript aus und leitet
# Standardausgabe und Fehlerausgabe in die Log-Datei um.
bash "$SCRIPT" >> "$LOGFILE" 2>&1

# -------------------------------
# Abschlussmeldung
# -------------------------------
echo "$(date '+%F %T') [INFO] Upload abgeschlossen." >> "$LOGFILE"
echo "-------------------------------------------------------" >> "$LOGFILE"

# -------------------------------
# Rückmeldung im Terminalfenster
# -------------------------------
echo "Upload abgeschlossen. Details im Log unter: $LOGFILE"
read -n 1 -s -r -p "Drücke eine Taste zum Schließen..."