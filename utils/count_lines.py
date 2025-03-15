import os

# Define file extensions to count
EXTENSIONS = {".py", ".js", ".html", ".sql"}

# Define directories to exclude
EXCLUDE_DIRS = {".venv", "__pycache__", "node_modules", "dist", "build"}

def count_lines_in_file(file_path):
    """Count non-empty and non-comment lines in a file."""
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return sum(1 for line in file if line.strip())  # Count non-empty lines
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return 0

def count_lines_in_directory(directory):
    """Recursively count lines of code in a directory, excluding specific folders."""
    total_lines = 0
    file_count = 0

    for root, dirs, files in os.walk(directory):
        # Remove excluded directories from the search
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

        for file in files:
            if any(file.endswith(ext) for ext in EXTENSIONS):
                file_path = os.path.join(root, file)
                lines = count_lines_in_file(file_path)
                total_lines += lines
                file_count += 1
                print(f"{file_path}: {lines} lines")

    print("\nSummary:")
    print(f"Total files scanned: {file_count}")
    print(f"Total lines of code: {total_lines}")

if __name__ == "__main__":
    directory = input("Enter the directory to scan: ")
    if os.path.isdir(directory):
        count_lines_in_directory(directory)
    else:
        print("Invalid directory!")
