import re
import sys

# File paths (input and output)
input_file = "jp.m3u" # Replace with your actual input file path
output_file ="jp.m3u"  # Replace with your desired output file path

# Read the M3U file
with open(input_file, 'r', encoding='utf-8') as file:
    lines = file.readlines()

# Process each line to replace group-title with 'JP'
updated_lines = []
for line in lines:
    # Use regex to replace all group-title values with 'JP'
    updated_line = re.sub(r'group-title="[^"]+"', 'group-title="JP"', line)
    updated_lines.append(updated_line)

# Write the updated content to a new file
with open(output_file, 'w', encoding='utf-8') as file:
    file.writelines(updated_lines)

print(f"Updated M3U file saved as: {output_file}")

