import requests
import time

# URLs for the two files in their repositories
url_1 = 'https://iptv-org.github.io/iptv/index.m3u'
url_2 = 'https://raw.githubusercontent.com/yuanzl77/IPTV/main/live.m3u'

# Threshold in KB/s. URLs slower than this will be removed.
SPEED_THRESHOLD_KBPS = 200  # Example: 100 KB/s

# Function to check if the URL's speed is above the threshold
def is_url_speed_acceptable(url):
    try:
        # Make a GET request and fetch a small chunk of the file
        response = requests.get(url, stream=True, timeout=10)
        
        # If the request is not successful, return False
        if response.status_code != 200:
            return False

        # Start measuring time
        start_time = time.time()
        # Read a small chunk (e.g., 1024 bytes)
        chunk_size = 1024*1024
        chunk = next(response.iter_content(chunk_size=chunk_size), None)

        # End measuring time
        end_time = time.time()

        # If no chunk is received, return False
        if chunk is None:
            return False

        # Calculate download speed (KB/s)
        download_time = end_time - start_time
        speed_kbps = (len(chunk) / 1024) / download_time

        print(f"URL: {url} | Speed: {speed_kbps:.2f} KB/s")

        # Return True if speed is above threshold, False otherwise
        return speed_kbps >= SPEED_THRESHOLD_KBPS

    except requests.RequestException:
        return False

# Function to extract and validate URLs and #EXTINF lines from the .m3u content
def process_m3u(content):
    lines = content.splitlines()
    valid_lines = []
    
    i = 0
    while i < len(lines):
        line = lines[i]
        # Check if it's an #EXTINF line, and the next line is the URL
        if line.startswith('#EXTINF') and (i + 1) < len(lines):
            extinf_line = line  # Store the #EXTINF line
            url_line = lines[i + 1]  # Store the URL line
            if url_line.startswith('http'):
                if is_url_speed_acceptable(url_line):
                    # Add both the #EXTINF and the URL if speed is acceptable
                    valid_lines.append(extinf_line)
                    valid_lines.append(url_line)
                else:
                    print(f"Removing slow URL: {url_line}")
            i += 2  # Skip to the next pair (#EXTINF and URL)
        else:
            # Add non-#EXTINF lines (if there are any) such as comments
            valid_lines.append(line)
            i += 1
    
    return "\n".join(valid_lines)

processed_content1 = process_m3u(url_1)
processed_content2 = process_m3u(url_2)
    
# Combine the two processed playlists
combined_content = processed_content1 + '\n' + processed_content2
    
# Save the combined and cleaned content to a new .m3u file
with open('combined_cleaned.m3u', 'w') as combined_file:
        combined_file.write(combined_content)

print("Combined and cleaned playlist saved as 'combined_cleaned.m3u'")
