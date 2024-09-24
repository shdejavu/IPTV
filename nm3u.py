import requests
import time
import re

# URLs for the files to compare
url_0 = 'https://iptv-org.github.io/iptv/index.m3u'
url_00 = 'https://raw.githubusercontent.com/yuanzl77/IPTV/main/live.m3u'
url_list = [
    'https://iptv-org.github.io/iptv/languages/zho.m3u',
    'https://iptv-org.github.io/iptv/languages/jpn.m3u',
    'https://iptv-org.github.io/iptv/languages/eng.m3u',
    'https://iptv-org.github.io/iptv/languages/undefined.m3u'
]

# File paths
IPLIVE_FILE = 'iplive.m3u'
COMBINED_CLEANED_FILE = 'combined_cleaned.m3u'

# Threshold in KB/s. URLs slower than this will be removed.
SPEED_THRESHOLD_KBPS = 100  # Example: 100 KB/s

def is_url_ipv6(url):
    return bool(re.search(r'\[.*?\]', url))

# Function to process and modify the #EXTINF metadata
def modify_extinf(extinf_line, title, flag):
    # Change the tvg-id to 's' + index and the group-title to 'general'
    # modified_line = re.sub(r'tvg-id="[^"]+"', f'tvg-id="s{index}"', extinf_line)
    if flag==1:
       modified_line = re.sub(r'tvg-id="([^"]+)"\s*tvg-name="([^"]+)"',
        lambda m: (
            # Check if tvg-name contains CCTV
            'tvg-id="' + (re.sub(r"(CCTV)(\d+)", r"\1 \2", m.group(2)) if "CCTV" in m.group(2) else m.group(2)) + '" ' +
            'tvg-name="' + re.sub(r"(CCTV)(\d+)", r"\1 \2", m.group(2)) + '"'  # Format tvg-name
        ), extinf_line)
    modified_line = re.sub(r'group-title="[^"]+"', 'group-title="{title}"', modified_line)
    return modified_line
    
# Fetch M3U content
def fetch_m3u_content(url):
    response = requests.get(url)
    if response.status_code == 200:
        return response.text
    else:
        print(f"Failed to fetch {url}")
        return None

def is_valid_media_type(response):
    content_type = response.headers.get('Content-Type', '')
    if "video" in content_type or "application" in content_type:
        return True
    return False

def is_valid_language(tvg_name):
    # English, Chinese, and Japanese Unicode ranges
    valid_characters = re.compile(r'^[\u0020-\u007F\u4E00-\u9FFF\u3040-\u30FF]+$')
    return bool(valid_characters.match(tvg_name))

def write_special_m3u(content, files):
    with open(files, 'w') as file:
        file.write(content)

# Function to modify group-title based on title input for migu processing
def process_migu_m3u(content, title):
    lines = content.splitlines()
    valid_lines = ['#EXTM3U x-tvg-url="https://assets.livednow.com/epg.xml"\n']

    i = 0
    while i < len(lines):
        line = lines[i]
        # Check if it's an #EXTINF line, and the next line is the URL
        if line.startswith('#EXTINF') and (i + 1) < len(lines):
            extinf_line = line  # Store the #EXTINF line
            url_line = lines[i + 1]  # Store the URL line

            # Filter URLs containing 'https://livednow.com/migu/'
            if 'https://livednow.com/migu/' in url_line:
                # Replace group-title based on input parameter (title)
                # extinf_line = re.sub(r'group-title="[^"]*"', f'group-title="{title}"', extinf_line)
                extinf_line = modify_extinf(extinf_line, title, 1)

                if is_special_url_speed_acceptable(url_line):
                    # Add both the #EXTINF and the URL if speed is acceptable
                    valid_lines.append(extinf_line)
                    valid_lines.append(url_line)
            i += 2  # Skip to the next pair (#EXTINF and URL)
        else:
            if line.startswith('#EXTM3U'):
               valid_lines.append(line)
               i += 1

    # Write the migu.m3u file
    with open('migu.m3u', 'w') as migu_file:
        migu_file.write("\n".join(valid_lines))

# Speed check for regular URLs
def is_url_speed_acceptable(url):
    try:
        response = requests.get(url, stream=True, timeout=5)
        if response.status_code != 200:
            return False
        start_time = time.time()
        chunk_size = 10240  # Regular chunk size
        chunk = next(response.iter_content(chunk_size=chunk_size), None)
        end_time = time.time()
        if chunk is None:
            return False
        download_time = end_time - start_time
        speed_kbps = (len(chunk) / 1024) / download_time
        return speed_kbps >= SPEED_THRESHOLD_KBPS
    except requests.RequestException:
        return False

# Speed check for special filtered URLs (larger chunk size)
def is_url_speed_acceptable_special(url):
    try:
        response = requests.get(url, stream=True, timeout=15)
        if response.status_code != 200:
            return False

        if not is_valid_media_type(response):
            print(f"Invalid media type: {response.headers.get('Content-Type')}")
            return False
            
        start_time = time.time()
        chunk_size = 1024*500  # 50x chunk size for special check
        chunk = next(response.iter_content(chunk_size=chunk_size), None)
        end_time = time.time()
        if chunk is None:
            return False
        download_time = end_time - start_time
        speed_kbps = (len(chunk) / 1024) / download_time
        return speed_kbps >= SPEED_THRESHOLD_KBPS
    except requests.RequestException:
        return False

# Extract TV channel name from #EXTINF line
def extract_channel_name(extinf_line):
    match = re.search(r'tvg-name="(.*?)"', extinf_line)
    if match:
        return match.group(1)
    return None

# Process the M3U content
def process_m3u(content, existing_channels, filter_url=None, special_check=False):
    lines = content.splitlines()
    valid_lines = []
    i = 0
    index = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith('#EXTINF') and (i + 1) < len(lines):
            extinf_line = line
            url_line = lines[i + 1]
            channel_name = extract_channel_name(extinf_line)
            
            if filter_url and filter_url not in url_line:
                i += 2
                continue
            
            if channel_name:
                if special_check:
                    is_acceptable = is_url_speed_acceptable_special(url_line)
                else:
                    is_acceptable = is_url_speed_acceptable(url_line)

                if is_acceptable:
                    if special_check:
                        index+=1
                        extinf_line = modify_extinf(extinf_line, 'general', 0)
                        
                    valid_lines.append(extinf_line)
                    valid_lines.append(url_line)
                    if channel_name in existing_channels:
                        print(f"Replaced channel: {channel_name}")
                    else:
                        print(f"Added new channel: {channel_name}")
            i += 2
        else:
            i += 1
    return valid_lines

# Read the current "iplive.m3u" to compare with new content
def read_existing_channels(filepath):
    existing_channels = {}
    try:
        with open(filepath, 'r') as file:
            lines = file.readlines()
            i = 0
            while i < len(lines):
                if lines[i].startswith('#EXTINF'):
                    extinf_line = lines[i]
                    url_line = lines[i + 1] if (i + 1) < len(lines) else ''
                    channel_name = extract_channel_name(extinf_line)
                    if channel_name:
                        existing_channels[channel_name] = (extinf_line, url_line)
                    i += 2
                else:
                    i += 1
    except FileNotFoundError:
        print(f"File {filepath} not found, starting fresh.")
    return existing_channels

def compare_and_update_m3u(new_channels, existing_channels, special=False):
    to_process = []
    for tvg_name, url in new_channels.items():
        # If channel is new or URL has changed, process it
        if tvg_name not in existing_channels or existing_channels[tvg_name] != url:
            to_process.append((tvg_name, url))
    return to_process

# Write the combined cleaned content to "combined_cleaned.m3u"
def append_or_replace_combined_cleaned(channel_name, extinf_line, url_line):
    # Read the existing "combined_cleaned.m3u" file to update or append new channels
    try:
        with open(COMBINED_CLEANED_FILE, 'r') as f:
            existing_lines = f.readlines()
    except FileNotFoundError:
        existing_lines = []

    updated_lines = []
    replaced = False
    i = 0
    while i < len(existing_lines):
        if existing_lines[i].startswith('#EXTINF'):
            existing_channel_name = extract_channel_name(existing_lines[i])
            if existing_channel_name == channel_name:
                # Replace the old channel information
                updated_lines.append(extinf_line + '\n')
                updated_lines.append(url_line + '\n')
                replaced = True
                i += 2
            else:
                updated_lines.append(existing_lines[i])
                updated_lines.append(existing_lines[i + 1])
                i += 2
        else:
            updated_lines.append(existing_lines[i])
            i += 1

    # If not replaced, append at the end
    if not replaced:
        updated_lines.append(extinf_line + '\n')
        updated_lines.append(url_line + '\n')

    # Write back the updated content
    with open(COMBINED_CLEANED_FILE, 'w') as f:
        f.writelines(updated_lines)

# Main function to process and compare channels
def process_multiple_m3u(url_list, special_url, filter_url):
    existing_channels = read_existing_channels(IPLIVE_FILE)
    
    # Process regular URLs
    for url in url_list:
        content = fetch_m3u_content(url)
        if content:
            valid_lines = process_m3u(content, existing_channels)
            for i in range(0, len(valid_lines), 2):
                channel_name = extract_channel_name(valid_lines[i])
                append_or_replace_combined_cleaned(channel_name, valid_lines[i], valid_lines[i + 1])

    # Process special filtered content
    special_content = fetch_m3u_content(special_url)
    if special_content:
        filtered_content = process_m3u(special_content, existing_channels, filter_url=filter_url, special_check=True)
        process_migu_m3u(filtered_content,'綜合')
        for i in range(0, len(filtered_content), 2):
            channel_name = extract_channel_name(filtered_content[i])
            append_or_replace_combined_cleaned(channel_name, filtered_content[i], filtered_content[i + 1])

# URLs to process
special_url = 'https://raw.githubusercontent.com/yuanzl77/IPTV/main/live.m3u'
filter_url = 'livednow'

# Process the M3U files
process_multiple_m3u(url_list, special_url, filter_url)

