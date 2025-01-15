#!/bin/bash

FILE="V1.2.4.bin"
CHUNK_SIZE=512
TOTAL_BYTES=0
LOOP_COUNT=0

# Ensure the file exists
if [[ ! -f "$FILE" ]]; then
    echo "File '$FILE' not found!"
    exit 1
fi

# Get the total size of the file
FILE_SIZE=$(stat -c%s "$FILE")

# Read the file in chunks
while IFS= read -r -n $CHUNK_SIZE chunk
do
    # Increment loop count
    LOOP_COUNT=$((LOOP_COUNT + 1))

    # Calculate bytes received in this chunk
    BYTES_RECEIVED=${#chunk}

    # Update total bytes
    TOTAL_BYTES=$((TOTAL_BYTES + BYTES_RECEIVED))

    # Convert chunk to hex
    HEX=$(echo -n "$chunk" | xxd -p -c $BYTES_RECEIVED)

    # Calculate checksum: sum of bytes modulo 256
    CHECKSUM=$(echo "$HEX" | sed 's/../0x& /g' | awk '{sum += $1} END {printf "0x%02X", sum % 256}')

    # Print the details
    printf "[Download Loop %d] Bytes Received: %d, Total Bytes: %d, Buffer Checksum: %s\n" \
           "$LOOP_COUNT" "$BYTES_RECEIVED" "$TOTAL_BYTES" "$CHECKSUM"

done < "$FILE"
