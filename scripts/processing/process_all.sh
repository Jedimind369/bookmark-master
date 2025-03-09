#!/bin/bash

# Dieses Skript verarbeitet eine HTML-Lesezeichendatei in Batches und führt die Ergebnisse zusammen.

# Konfiguration
INPUT_FILE=$1
BATCH_SIZE=50
OUTPUT_DIR="data/processed"
MERGED_DIR="$OUTPUT_DIR/merged"
LOG_DIR="logs"

# Prüfe, ob die Eingabedatei angegeben wurde
if [ -z "$INPUT_FILE" ]; then
    echo "Fehler: Keine Eingabedatei angegeben."
    echo "Verwendung: $0 <pfad/zur/lesezeichen.html>"
    exit 1
fi

# Prüfe, ob die Eingabedatei existiert
if [ ! -f "$INPUT_FILE" ]; then
    echo "Fehler: Die Datei '$INPUT_FILE' existiert nicht."
    exit 1
fi

# Erstelle die Verzeichnisse
mkdir -p "$OUTPUT_DIR" "$LOG_DIR" "$MERGED_DIR"

# Definiere die Batch-Größen
BATCH_RANGES=(
    "0 3000"
    "3000 6000"
    "6000 9000"
    "9000"
)

# Verarbeite jeden Batch
for i in "${!BATCH_RANGES[@]}"; do
    RANGE="${BATCH_RANGES[$i]}"
    RUN_DIR="$OUTPUT_DIR/run_$((i+1))"
    LOG_FILE="$LOG_DIR/process_run_$((i+1)).log"
    
    echo "Starte Verarbeitung von Batch $((i+1)): $RANGE"
    
    # Erstelle das Verzeichnis für diesen Lauf
    mkdir -p "$RUN_DIR"
    
    # Baue den Befehl
    if [[ "$RANGE" == *" "* ]]; then
        # Bereich mit Start und Ende
        START=$(echo $RANGE | cut -d' ' -f1)
        END=$(echo $RANGE | cut -d' ' -f2)
        CMD="python -m scripts.processing.process_bookmarks \"$INPUT_FILE\" --start $START --end $END --batch-size $BATCH_SIZE --output-dir \"$RUN_DIR\""
    else
        # Nur Start, kein Ende (bis zum Ende verarbeiten)
        START=$RANGE
        CMD="python -m scripts.processing.process_bookmarks \"$INPUT_FILE\" --start $START --batch-size $BATCH_SIZE --output-dir \"$RUN_DIR\""
    fi
    
    echo "Ausführung: $CMD"
    echo "Log-Datei: $LOG_FILE"
    
    # Führe den Befehl aus und protokolliere die Ausgabe
    eval "$CMD" | tee "$LOG_FILE"
    
    # Prüfe, ob der Befehl erfolgreich war
    if [ ${PIPESTATUS[0]} -ne 0 ]; then
        echo "Fehler bei der Verarbeitung von Batch $((i+1)). Siehe $LOG_FILE für Details."
        exit 1
    fi
    
    echo "Batch $((i+1)) erfolgreich verarbeitet."
    echo
done

# Führe die Ergebnisse zusammen
echo "Führe die Ergebnisse zusammen..."

# Baue die Liste der Eingabeverzeichnisse
INPUT_DIRS=""
for i in "${!BATCH_RANGES[@]}"; do
    INPUT_DIRS="$INPUT_DIRS \"$OUTPUT_DIR/run_$((i+1))\""
done

# Führe den Befehl aus
MERGE_CMD="python -m scripts.processing.merge_results --input-dirs $INPUT_DIRS --output-dir \"$MERGED_DIR\""
echo "Ausführung: $MERGE_CMD"
eval "$MERGE_CMD"

echo "Verarbeitung abgeschlossen. Ergebnisse in $MERGED_DIR" 