import requests
import time
import re
from difflib import unified_diff

# URLs for the repositories
url_old_combined = 'https://raw.githubusercontent.com/shdejavu/IPTV/main/combined.m3u'
url_list = [
    'https://iptv-org.github.io/iptv/languages/zho.m3u',
    'https://iptv-org.github.io/iptv/languages/jpn.m3u',
    'https://iptv-org.github.io/iptv/languages/eng.m3u',
    'https://iptv-org.github.io/iptv/languages/undefined.m3u'
]

# Threshold in KB/s. URLs slower than this will be removed.
SPEED_THRESHOLD_KBPS = 100  # Example: 100 KB/s

# Fetch old combined m3u file from GitHub
def fetch_old_combined_m3u(url):
    response = requests.get(url)
    if response.status_code == 200:
        return response.text
    else:
        print(f"Failed to fetch the old combined m3u from {url}")
        return None

# Function to fetch the content of an .m3u file
def fetch_m3u_content(url):
    response = requests.get(url)
    if response.status_code == 200:
        return response.text
    else:
        print(f"Failed to fetch {url}")
        return None

# Function to check if the URL's speed is above the threshold
def is_url_speed_acceptable(url):
    try:
        response = requests.get(url, stream=True, timeout=5)
        if response.status_code != 200:
            return False

        start_time = time.time()
        chunk_size = 10240  # 10KB chunk
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

# Function to process the content of an .m3u file and filter valid URLs
def process_m3u(content):
    lines = content.splitlines()
    valid_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith('#EXTINF') and (i + 1) < len(lines):
            extinf_line = line
            url_line = lines[i + 1]
            if url_line.startswith('http') and is_url_speed_acceptable(url_line):
                valid_lines.append(extinf_line)
                valid_lines.append(url_line)
            i += 2
        else:
            if line.startswith('#EXTM3U'):
                valid_lines.append(line)
            i += 1
    return "\n".join(valid_lines)

# Compare old and new combined m3u files to find differences
def compare_m3u(old_content, new_content):
    diff = unified_diff(old_content.splitlines(), new_content.splitlines(), lineterm='')
    changed_channels = []
    for line in diff:
        if line.startswith('+') and not line.startswith('+++'):
            changed_channels.append(line[1:])
    return changed_channels

# Process multiple m3u files and generate a combined one
def process_multiple_m3u(url_list):
    processed_content_list = []
    for url in url_list:
        try:
            content = fetch_m3u_content(url)
            if content:
                processed_content = process_m3u(content)
                processed_content_list.append(processed_content)
        except Exception as e:
            print(f"Error processing {url}: {e}")
            continue
    combined_content = '\n'.join(processed_content_list)
    return combined_content

# Append new or changed valid URLs to the old combined file
def update_combined_m3u(old_combined, new_combined):
    old_combined_lines = old_combined.splitlines()
    new_combined_lines = new_combined.splitlines()

    diff = compare_m3u(old_combined, new_combined)
    for line in diff:
        if line.startswith('#EXTINF') or line.startswith('http'):
            new_channel = new_combined_lines[new_combined_lines.index(line):new_combined_lines.index(line) + 2]
            old_combined_lines.extend(new_channel)

    return "\n".join(old_combined_lines)

# Main workflow
def main():
    # Fetch old combined m3u file from GitHub
    old_combined_content = fetch_old_combined_m3u(url_old_combined)
    
    # Process and combine new m3u files
    new_combined_content = process_multiple_m3u(url_list)

    # Compare and update the old combined content
    updated_combined_content = update_combined_m3u(old_combined_content, new_combined_content)

    # Save the updated combined content to a file
    with open('combined_cleaned.m3u', 'w') as combined_file:
        combined_file.write(updated_combined_content)

    # Optionally push the updated file back to GitHub via GitHub API or GitHub Actions

main()
