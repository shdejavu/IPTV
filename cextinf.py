import re

def modify_extinf(extinf_line, title, flag=0):
    # Change the tvg-id to 's' + index and the group-title to 'general'
    # modified_line = re.sub(r'tvg-id="[^"]+"', f'tvg-id="s{index}"', extinf_line)
    if flag==1:
       extinf_line = re.sub(r'tvg-id="([^"]+)"\s*tvg-name="([^"]+)"',
        lambda m: (
            # Check if tvg-name contains CCTV
            'tvg-id="' + (re.sub(r"(CCTV)(\d+)", r"\1 \2", m.group(2)) if "CCTV" in m.group(2) else m.group(2)) + '" ' +
            'tvg-name="' + re.sub(r"(CCTV)(\d+)", r"\1 \2", m.group(2)) + '"'  # Format tvg-name
        ), extinf_line)
    modified_line = re.sub(r'group-title="[^"]+"', 'group-title="{}"'.format(title), extinf_line)
    return modified_line

# Function to parse M3U file and return a dictionary of metadata keyed by channel name
def parse_m3u(file_path):
    metadata_dict = {}
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith("#EXTINF"):
                # Extract the channel name, ignoring leading and trailing spaces
                #match = re.match(r'#EXTINF:[^\d]*,([^,\n\r]+)', line)
                match=line.split(',')[-1].strip().replace(' ','')
                if match:
                    channel_name = match  # Get the channel name, cleaned up
                    url = lines[i + 1].strip()  # The URL comes right after the #EXTINF line
                    if 'CCTV' in match:
                       extinf_line=modify_extinf(line,'央视')
                    elif '卫视' in match:
                       extinf_line=modify_extinf(line,'卫视')
                    else:
                       extinf_line=modify_extinf(line,'ITV')
                    metadata_dict[channel_name] = (extinf_line, url)  # Store both EXTINF and URL
                i += 2  # Skip over the URL line since it's already captured
            else:
                i += 1  # Move to the next line if it's not an #EXTINF line
    return metadata_dict

# Function to update the new M3U file with metadata from the old M3U file
def update_m3u(old_m3u, new_m3u, output_m3u):
    old_metadata = parse_m3u(old_m3u)  # Parse old M3U for metadata
    updated_lines = []  # List to store updated lines
    
    with open(new_m3u, 'r', encoding='utf-8') as file:
        lines = file.readlines()
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith("#EXTINF"):
                # Extract the channel name from the #EXTINF line in the new M3U file, ignoring spaces
                #match = re.match(r'#EXTINF:[^\d]*,([^,\n\r]+)', line)
                match=line.split(',')[-1].strip().replace(' ','')
                if match:
                    channel_name = match  # Clean up the channel name
                    url = lines[i + 1].strip()  # The URL comes right after the #EXTINF line
                    # Check if metadata is available in old M3U for this channel
                    if channel_name in old_metadata:
                        extinf,old_url = old_metadata[channel_name]  # Get both EXTINF and URL from the old file
                        updated_lines.append(extinf)  # Replace with the detailed #EXTINF from the old file
                        updated_lines.append(url)  # Replace with the corresponding URL from the old file
                    else:
                        extinf_line=modify_extinf(line,match)
                        updated_lines.append(extinf_line)  # Keep the new EXTINF if no match is found
                        updated_lines.append(url)  # Add the corresponding URL
                i += 2  # Skip over the next URL line since it's already processed
            else:
                updated_lines.append(line)  # Add non-EXTINF lines (e.g., comments, unrelated URLs)
                i += 1  # Move to the next line

    # Write the updated content to a new file
    with open(output_m3u, 'w', encoding='utf-8') as file:
        for line in updated_lines:
            file.write(f"{line}\n")  # Write each line into the output file

# Run the function with the file names
old_m3u = 'itv.m3u'  # Old M3U with detailed metadata
new_m3u = 'itvp.m3u'  # New M3U with missing metadata
output_m3u = 'itv_p.m3u'  # Output M3U with updated metadata
update_m3u(old_m3u, new_m3u, output_m3u)

print(f"Updated M3U file saved as {output_m3u}")

