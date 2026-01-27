import json
import argparse

def convert_api_version_in_dict(data):
    """
    Recursively traverse a dictionary to find and convert "api_version" fields.
    """
    if isinstance(data, dict):
        for key, value in data.items():
            # If we find an "api_version" field with a string format like "X.Y"
            if key == "api_version" and isinstance(value, str):
                try:
                    # Split "api_version" into major and minor parts
                    major, minor = map(int, value.split('.'))
                    # Replace the "api_version" string with an object containing major and minor
                    data[key] = {"major": major, "minor": minor}
                except ValueError:
                    print(f"Warning: 'api_version' value '{value}' is not in the expected format 'X.Y'. Skipping conversion for this entry.")
            else:
                # Recursively traverse nested dictionaries and lists
                convert_api_version_in_dict(value)
    elif isinstance(data, list):
        for item in data:
            # Recursively check each item in the list
            convert_api_version_in_dict(item)

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Convert 'api_version' in a JSON file to an object with 'major' and 'minor' fields.")
    parser.add_argument("input_file", help="Path to the input JSON file")
    parser.add_argument("output_file", help="Path to the output JSON file")

    # Parse arguments
    args = parser.parse_args()

    # Read JSON data from input file
    with open(args.input_file, 'r') as file:
        json_data = json.load(file)

    # Convert "api_version" fields throughout the JSON
    convert_api_version_in_dict(json_data)

    # Write updated JSON data to output file
    with open(args.output_file, 'w') as file:
        json.dump(json_data, file, indent=4)

    print(f"Updated JSON has been saved to {args.output_file}")

# Run the program
if __name__ == "__main__":
    main()
