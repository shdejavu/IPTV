import re
import xml.etree.ElementTree as ET

# File paths (input and output)
m3ufile='jp.m3u'
m3u_file = m3ufile  # Replace with your actual M3U file path
epg_file = 'jp.xml'    # Replace with your EPG XML file path
output_m3u_file = m3ufile  # Output M3U file path

# Step 1: Parse the EPG XML file to create a map of tvg-id to display-name
epg_tree = ET.parse(epg_file)
epg_root = epg_tree.getroot()

# Dictionary to store tvg-id and corresponding tvg-name (display-name)
tvg_id_to_name = {}
for channel in epg_root.findall('channel'):
    tvg_id = channel.get('id')
    display_name = channel.find('display-name').text if channel.find('display-name') is not None else None
    if tvg_id and display_name:
        tvg_id_to_name[tvg_id] = display_name

# Step 2: Read the M3U file and update each channel with the corresponding tvg-name
updated_lines = []
with open(m3u_file, 'r', encoding='utf-8') as file:
    lines = file.readlines()
    for line in lines:
        # Check if the line contains a tvg-id
        match = re.search(r'tvg-id="([^"]+)"', line)
        if match:
            tvg_id = match.group(1)
            # Find the corresponding tvg-name from the EPG file
            if tvg_id in tvg_id_to_name:
                tvg_name = tvg_id_to_name[tvg_id]
                # Add or update the tvg-name attribute
                if 'tvg-name="' in line:
                    # If tvg-name already exists, replace it
                    line = re.sub(r'tvg-name="[^"]+"', f'tvg-name="{tvg_name}"', line)
                else:
                    # If tvg-name doesn't exist, add it after tvg-id
                    line = re.sub(r'(tvg-id="[^"]+")', f'\\1 tvg-name="{tvg_name}"', line)
        updated_lines.append(line)

# Step 3: Write the updated lines to a new M3U file
with open(output_m3u_file, 'w', encoding='utf-8') as file:
    file.writelines(updated_lines)

print(f"Updated M3U file saved as: {output_m3u_file}")

