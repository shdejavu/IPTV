import requests
import time
import re
import os

# URLs to fetch
url_list = [
    'https://iptv-org.github.io/iptv/languages/zho.m3u',
    'https://iptv-org.github.io/iptv/languages/jpn.m3u',
    'https://iptv-org.github.io/iptv/languages/eng.m3u',
    'https://iptv-org.github.io/iptv/languages/undefined.m3u'
]

special_url = 'https://raw.githubusercontent.com/yuanzl77/IPTV/main/live.m3u'
filter_url = 'https://livednow.com/migu/'

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

def is_url_speed_acceptable(url, chunk_size=NORMAL_CHUNK_SIZE):
    try:
        response = requests.get(url, stream=True, timeout=10)
        if response.status_code != 200:
            return False
        if not is_valid_media_type(response):
            print(f"Invalid media type: {response.headers.get('Content-Type')}")
            return False
        start_time = time.time()
        chunk = next(response.iter_content(chunk_size=chunk_size), None)
        end_time = time.time()
        if chunk is None:
            return False
        download_time = end_time - start_time
        speed_kbps = (len(chunk) / 1024) / download_time
        print(f"URL: {url} | Speed: {speed_kbps:.2f} KB/s")
        return speed_kbps >= SPEED_THRESHOLD_KBPS
    except requests.RequestException:
        return False


def process_m3u(content, processed_channels, special_check=False):
    lines = content.splitlines()
    valid_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith('#EXTINF') and (i + 1) < len(lines):
            extinf_line = line
            url_line = lines[i + 1]
            if url_line.startswith('http'):
                tvg_name_match = re.search(r'tvg-name="([^"]+)"', extinf_line)
                if tvg_name_match:
                    tvg_name = tvg_name_match.group(1)
                    if tvg_name in processed_channels and processed_channels[tvg_name] == url_line:
                        print(f"Skipping unchanged channel: {tvg_name}")
                    else:
                        chunk_size = SPECIAL_CHUNK_SIZE if special_check else NORMAL_CHUNK_SIZE
                        if is_url_speed_acceptable(url_line, chunk_size=chunk_size):
                            valid_lines.append(extinf_line)
                            valid_lines.append(url_line)
                            processed_channels[tvg_name] = url_line
                        else:
                            print(f"Removing slow URL: {url_line}")
            i += 2
        else:
            if line.startswith('#EXTM3U'):
                valid_lines.append('#EXTM3U')
            i += 1
    return "\n".join(valid_lines)


def compare_and_update_m3u(new_content, old_content, special_check=False):
    old_channels = {}
    new_channels = {}
    to_process = []

    # Parse the old content
    for line in old_content.splitlines():
        if line.startswith('#EXTINF'):
            tvg_name_match = re.search(r'tvg-name="([^"]+)"', line)
            if tvg_name_match:
                tvg_name = tvg_name_match.group(1)
                url_line = next(old_content.splitlines(), None)
                old_channels[tvg_name] = url_line

    # Parse the new content
    lines = new_content.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith('#EXTINF') and (i + 1) < len(lines):
            extinf_line = line
            url_line = lines[i + 1]
            if url_line.startswith('http'):
                tvg_name_match = re.search(r'tvg-name="([^"]+)"', extinf_line)
                if tvg_name_match:
                    tvg_name = tvg_name_match.group(1)
                    new_channels[tvg_name] = url_line
                    if tvg_name not in old_channels or old_channels[tvg_name] != url_line:
                        to_process.append((tvg_name, url_line))
            i += 2

    # Process only the new or changed channels
    processed_channels = {}
    for tvg_name, url in to_process:
        chunk_size = SPECIAL_CHUNK_SIZE if special_check else NORMAL_CHUNK_SIZE
        if is_url_speed_acceptable(url, chunk_size=chunk_size):
            processed_channels[tvg_name] = url

    return processed_channels


def update_m3u_files():
    # Fetch old iplive.m3u content
    if os.path.exists('iplive.m3u'):
        with open('iplive.m3u', 'r') as f:
            old_content = f.read()
    else:
        old_content = ""

    # Combine new URL list
    new_content_list = []
    for url in url_list:
        new_content_list.append(fetch_m3u_content(url))
    new_content = '\n'.join(new_content_list)

    # Compare and update iplive.m3u
    updated_channels = compare_and_update_m3u(new_content, old_content)
    with open('iplive.m3u', 'w') as f:
        f.write("\n".join(updated_channels))

    # Special processing for migu.m3u
    special_content = fetch_m3u_content(special_url)
    filtered_special_content = "\n".join(line for line in special_content.splitlines() if filter_url in line)
    #special_channels = compare_and_update_m3u(filtered_special_content, old_content, special_check=True)
    
    # Write to combined_cleaned.m3u and migu.m3u
    with open('combined_cleaned.m3u', 'a') as f:
        f.write("\n".join(updated_channels))
    with open('migu.m3u', 'w') as f:
        f.write("\n".join(special_channels))


update_m3u_files()
