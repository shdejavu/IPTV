import requests
import time
import re
import os

# URLs to fetch
url_list = [
    'https://raw.githubusercontent.com/iptv-org/iptv/refs/heads/master/streams/cn.m3u',
    'https://raw.githubusercontent.com/iptv-org/iptv/refs/heads/master/streams/jp.m3u',
    'https://raw.githubusercontent.com/iptv-org/iptv/refs/heads/master/streams/jp_primehome.m3u',
    'https://raw.githubusercontent.com/iptv-org/iptv/refs/heads/master/streams/us.m3u'
]

special_url = 'https://raw.githubusercontent.com/yuanzl77/IPTV/main/live.m3u'
filter_url = 'livednow'

SPEED_THRESHOLD_KBPS = 100
SPECIAL_CHUNK_SIZE = 10240 * 10
NORMAL_CHUNK_SIZE = 10240

def is_url_ipv6(url):
    return bool(re.search(r'\[.*?\]', url))

# Function to process and modify the #EXTINF metadata
def modify_extinf(extinf_line, title, flag):
    # Change the tvg-id to 's' + index and the group-title to 'general'
    # modified_line = re.sub(r'tvg-id="[^"]+"', f'tvg-id="s{index}"', extinf_line)
    if flag==1:
       extinf_line = re.sub(r'tvg-id="([^"]+)"\s*tvg-name="([^"]+)"',
        lambda m: (
            # Check if tvg-name contains CCTV
            'tvg-id="' + (re.sub(r"(CCTV)(\d+)", r"\1 \2", m.group(2)) if "CCTV" in m.group(2) else m.group(2)) + '" ' +
            'tvg-name="' + re.sub(r"(CCTV)(\d+)", r"\1 \2", m.group(2)) + '"'  # Format tvg-name
        ), extinf_line)
    modified_line = re.sub(r'group-title="[^"]+"', 'group-title="{}"'.format(title), modified_line)
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

def is_url_speed_acceptable(url, special=False):
    chunk_size = 10240 if not special else 10240 * 10  # Larger chunk size for special URLs

    try:
        response = requests.get(url, stream=True, timeout=10)
        if response.status_code != 200:
            return False
        
        start_time = time.time()
        chunk = next(response.iter_content(chunk_size=chunk_size), None)
        end_time = time.time()

        if chunk is None:
            return False

        download_time = end_time - start_time
        speed_kbps = (len(chunk) / 1024) / download_time

        return speed_kbps >= SPEED_THRESHOLD_KBPS
    except requests.RequestException:
        return False

def process_m3u(content, filter_url=None, special_process=False):
    lines = content.splitlines()
    valid_lines = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        if line.startswith('#EXTINF') and (i + 1) < len(lines):
            extinf_line = line
            url_line = lines[i + 1]

            # Extract tvg-name or fallback to the title in #EXTINF line
            match = re.search(r'tvg-id="([^"]*)"', extinf_line)
            tvg_name = match.group(1) if match else extinf_line.split(',')[-1].strip()

            if filter_url and filter_url in url_line:
                special_process = True

            if is_url_speed_acceptable(url_line, special=special_process):
                valid_lines.append(extinf_line)
                valid_lines.append(url_line)
            i += 2
        else:
            if line.startswith('#EXTM3U'):
                valid_lines.append('#EXTM3U')
            i += 1
    
    return "\n".join(valid_lines)

def compare_and_update_m3u(new_content, existing_content):
    new_lines = new_content.splitlines()
    existing_lines = existing_content.splitlines()
    
    to_process = []
    i=0
    
    while i < len(new_lines):
        if new_lines[i].startswith('#EXTINF') and (i + 1) < len(new_lines):
           extinf_line = new_lines[i]
           url_line = new_lines[i + 1]
        
           match = re.search(r'tvg-name="([^"]*)"', extinf_line)
           tvg_name = match.group(1) if match else extinf_line.split(',')[-1].strip()
        
           if (tvg_name, url_line) not in [(existing_lines[j], existing_lines[j+1]) for j in range(len(existing_lines)-1)]:
              to_process.append((extinf_line, url_line))

           i+=2
        else:
           i+=1
    
    return to_process

def fetch_m3u_content(url):
    response = requests.get(url)
    if response.status_code == 200:
        return response.text
    return None

def process_multiple_m3u(url_list, special_url, filter_url):
    # Fetching and combining content from URL list
    combined_iplive_content = []
    
    for url in url_list:
        content = fetch_m3u_content(url)
        combined_iplive_content.append(content)
    
    iplive_content = '\n'.join(combined_iplive_content)

    # Compare and process new content
    try:
        with open('iplive.m3u', 'r') as f:
            existing_iplive_content = f.read()
    except FileNotFoundError:
        existing_iplive_content = ''

    to_process_iplive = compare_and_update_m3u(iplive_content, existing_iplive_content)

    with open('iplive.m3u', 'w') as f:
        f.write(iplive_content)

    # Fetching and processing special URL content
    special_content = fetch_m3u_content(special_url)
    #filtered_special_content = process_m3u(special_content, filter_url=filter_url, special_process=True)
    filtered_special_content = special_content
    
    try:
        with open('combined_cleaned.m3u', 'r') as f:
            existing_combined_content = f.read()
    except FileNotFoundError:
        existing_combined_content = ''

    to_process_combined = compare_and_update_m3u(filtered_special_content, existing_combined_content)

    # Append or replace processed content in combined_cleaned.m3u
    if len(to_process_combined)>0:
        with open('combined_cleaned.m3u', 'a') as f:
           for extinf, url in to_process_combined:
              f.write(f"{extinf}\n{url}\n")

    # Write filtered content to migu.m3u
    if "#EXTINF" in filtered_special_content:
        with open('migu.m3u', 'w') as f:
           f.write(filtered_special_content)

process_multiple_m3u(url_list, special_url, filter_url)

