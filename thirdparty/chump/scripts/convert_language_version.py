import json
import argparse

def convert_language_version_fields(data):
    """
    Recursively traverse a dictionary to find and convert "language_version_min" and "language_version_max" fields.
    """
    if isinstance(data, dict):
        for key, value in data.items():
            # Check for either "language_version_min" or "language_version_max"
            if key in {"language_version_min", "language_version_max"} and isinstance(value, str):
                try:
                    # Split the version string into mega, major, minor, and patch parts
                    mega, major, minor, patch = map(int, value.split('.'))
                    # Replace the field with an object containing mega, major, minor, and patch
                    data[key] = {
                        "mega": mega,
                        "major": major,
                        "minor": minor,
                        "patch": patch
                    }
                except ValueError:
                    print(f"Warning: '{key}' value '{value}' is not in the expected format 'mega.major.minor.patch'. Skipping conversion for this entry.")
            else:
                # Recursively traverse nested dictionaries and lists
                convert_language_version_fields(value)
    elif isinstance(data, list):
        for item in data:
            # Recursively check each item in the list
            convert_language_version_fields(item)

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Convert 'language_version_min' and 'language_version_max' fields in a JSON file to objects with 'mega', 'major', 'minor', and 'patch' fields.")
    parser.add_argument("input_file", help="Path to the input JSON file")
    parser.add_argument("output_file", help="Path to the output JSON file")

    # Parse arguments
    args = parser.parse_args()

    # Read JSON data from input file
    with open(args.input_file, 'r') as file:
        json_data = json.load(file)

    # Convert "language_version_min" and "language_version_max" fields throughout the JSON
    convert_language_version_fields(json_data)

    # Write updated JSON data to output file
    with open(args.output_file, 'w') as file:
        json.dump(json_data, file, indent=4)

    print(f"Updated JSON has been saved to {args.output_file}")

# Run the program
if __name__ == "__main__":
    main()
