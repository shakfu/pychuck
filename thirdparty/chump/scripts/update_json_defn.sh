#!/bin/bash

# Check if directory argument is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <directory>"
    exit 1
fi

# Assign the directory argument to a variable
directory="$1"

# Check if the provided directory exists
if [ ! -d "$directory" ]; then
    echo "Error: Directory $directory does not exist."
    exit 1
fi

# Loop through all .json files in the directory recursively
find "$directory" -type f -name "*.json" | while read -r json_file; do
    echo "Processing $json_file..."

    # Run the first script (convert_api_version.py)
    python3 convert_api_version.py "$json_file" "$json_file"
    
    # Check if the first script executed successfully
    if [ $? -ne 0 ]; then
        echo "Error: convert_api_version.py failed on $json_file"
        exit 1
    fi

    # Run the second script (convert_language_version.py)
    python3 convert_language_version.py "$json_file" "$json_file"

    # Check if the second script executed successfully
    if [ $? -ne 0 ]; then
        echo "Error: convert_language_version.py failed on $json_file"
        exit 1
    fi

    echo "Successfully processed $json_file"
done

echo "All files processed."
