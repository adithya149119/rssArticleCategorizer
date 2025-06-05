import os
import feedparser
from bs4 import BeautifulSoup
from datetime import datetime
import json
import csv
import unicodedata
import re
from collections import deque
from rapidfuzz import fuzz

def clean_html(html):
    return BeautifulSoup(html, "html.parser").get_text()

def normalize_text(text):
    text = unicodedata.normalize("NFKD", text) #normalize unicode
    text = text.encode("ascii","ignore").decode("utf-8") #remove accents
    text = text.strip().lower()
    text = re.sub(r"\s+", " ", text) #collapse multiple spaces
    return text

def Clean_title(text):
    text = unicodedata.normalize("NFKD", text) #normalize unicode
    text = text.encode("ascii","ignore").decode("utf-8") #remove accents
    text = text.strip()
    text = re.sub(r"\s+", " ", text) #collapse multiple spaces
    return text

FUZZY_THRESHOLD = 97

def is_duplicate_title(new_title, seen_titles):
    for i in seen_titles:
        if fuzz.ratio(new_title, i) >= FUZZY_THRESHOLD:
            return True
    return False

# Keywords for filtering
ma_keywords = [
    "acquisition", "merger", "takeover", "buyout", "acquires", "merges with",
    "purchases", "absorbs", "joint venture", "consolidates with", "stake in"
]

defense_keywords = [
    "defense company", "defense", "defence", "military", "military contractor", "aerospace", "security firm",
    "military supplier", "weapons manufacturer", "armed forces", "defense technology"
]

def contains_keywords(text, keywords):
    text_lower = text.lower()
    return any(k in text_lower for k in keywords)

# Load RSS feed URLs from file
with open("feeds.txt", "r") as f:
    feed_urls = [line.strip() for line in f if line.strip()]

# Parse feeds and gather entries
entries = []
for url in feed_urls:
    feed = feedparser.parse(url)
    for entry in feed.entries:
        title = Clean_title(entry.get("title", "").strip())
        link = entry.get("link", "").strip()
        summary = Clean_title(clean_html(entry.get("summary", "")))
        published = entry.get("published", "")
        
        # Filter for keywords: M&A AND Defense terms
        combined_text = title + " " + summary
        if contains_keywords(combined_text, ma_keywords) and contains_keywords(combined_text, defense_keywords):
            entries.append({
                "title": title,
                "link": link,
                "summary": summary,
                "published": published
            })

# Load existing deduplication data
dedup_file = "deduplication.json"
if os.path.exists(dedup_file):
    with open(dedup_file, "r") as f:
        dedup_data = json.load(f)
        seen_titles = deque(dedup_data.get("titles", []),maxlen=3000)
        seen_links = deque(dedup_data.get("links", []),maxlen=3000)
else:
    seen_titles = deque(maxlen=3000)
    seen_links = deque(maxlen=3000)

filtered_entries = []

# Deduplicate by title and link separately
for entry in entries:
    title_norm = normalize_text(entry["title"])
    link_norm = normalize_text(entry["link"])

    duplicate_title = is_duplicate_title(title_norm,seen_titles)
    duplicate_link = link_norm in seen_links

    if not duplicate_title and not duplicate_link:
            filtered_entries.append(entry)
            seen_titles.append(title_norm)
            seen_links.append(link_norm)

# Prepare date-based output filename prefix
today = datetime.now().strftime("%d%b%Y")
output_folder = f"Date_{today}"
output_base = f"results_{today}"

Folder = f"{output_folder}"

if not os.path.exists(Folder.encode("utf-8")):
        os.makedirs(Folder.encode("utf-8"))

# Save CSV
with open(f"{Folder}\\{output_base}.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["title", "link", "summary", "published"])
    writer.writeheader()
    writer.writerows(filtered_entries)

# Save Markdown
with open(f"{Folder}\\{output_base}.md", "w", encoding="utf-8") as f:
    for entry in filtered_entries:
        f.write(f"- [{entry['title']}]({entry['link']})\n")

# Save HTML
with open(f"{Folder}\\{output_base}.html", "w", encoding="utf-8") as f:
    f.write("<html><body>\n")
    for entry in filtered_entries:
        f.write(f"<p><a href='{entry['link']}'>{entry['title']}</a><br>{entry['summary']}</p>\n")
    f.write("</body></html>\n")

# Update deduplication record file
with open(dedup_file, "w") as f:
    json.dump({
        "titles": list(seen_titles),
        "links": list(seen_links)
    }, f, indent=2)
