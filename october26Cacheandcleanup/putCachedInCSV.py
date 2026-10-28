import csv
import os
import re
import hashlib
import json
import urllib.parse
import urllib.request
import unicodedata
import time
from collections import defaultdict

def decode_html_entities(text: str) -> str:
    """Decodes HTML entities like &#8217;, &#8220;, &amp;, etc."""
    if not text:
        return ""
    text = text.replace('&#8217;', "'").replace('&#8220;', '"').replace('&#8221;', '"')
    text = text.replace('&#8211;', '-').replace('&#038;', '&').replace('&amp;', '&')
    return text

def normalize_words(text: str) -> set[str]:
    """Extracts lowercase key alphanumeric words (3+ chars) excluding common stopwords."""
    if not text:
        return set()
    text = decode_html_entities(text)
    nfkd = unicodedata.normalize('NFD', text)
    clean = ''.join(c for c in nfkd if unicodedata.category(c) != 'Mn')
    words = re.findall(r'\b[a-z0-9]{3,}\b', clean.lower())
    stopwords = {'the', 'and', 'for', 'with', 'about', 'from', 'this', 'that', 'into', 'with'}
    return {w for w in words if w not in stopwords}

def title_match_score(target_title: str, candidate_title: str) -> float:
    """Calculates word overlap ratio between target title and candidate title."""
    t_words = normalize_words(target_title)
    c_words = normalize_words(candidate_title)
    if not t_words or not c_words:
        return 0.0
    overlap = len(t_words.intersection(c_words))
    return overlap / len(t_words)

def normalize_text_filename(text: str) -> str:
    """Cleans Spanish accents/diacritics and returns lowercase string with underscores."""
    if not text:
        return ""
    text = decode_html_entities(text)
    nfkd = unicodedata.normalize('NFD', text)
    clean_text = ''.join(c for c in nfkd if unicodedata.category(c) != 'Mn')
    return re.sub(r'[\W_]+', '_', clean_text.lower()).strip('_')

def extract_clean_url(url_field: str) -> str:
    """Extracts raw URL string from plain text or <a href="..."> tags."""
    if not url_field:
        return ""
    clean_field = url_field.replace('""', '"').strip()
    match = re.search(r'href=["\']?([^"\' >]+)["\']?', clean_field, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return clean_field

def safe_filename(title: str, url: str) -> str:
    """Generates a safe filename using normalized title and full URL SHA-1 hash."""
    clean_title = normalize_text_filename(title)[:40] or "document"
    url_path = url.split('?')[0].split('#')[0]
    ext = os.path.splitext(url_path)[1]
    
    if not ext or len(ext) > 5 or ext.lower() not in ('.html', '.pdf', '.doc', '.docx', '.txt'):
        ext = '.html' 
    
    url_hash = hashlib.sha1(url.encode('utf-8')).hexdigest()[:6]
    return f"{clean_title}_{url_hash}{ext}"

def find_local_cached_file(title: str, raw_url_field: str, cache_dir: str, cached_files_list: list) -> tuple[str, str, str]:
    """Strictly checks local files/ directory using exact URL hashes or exact file names."""
    actual_url = extract_clean_url(raw_url_field)

    if not actual_url or actual_url == '#':
        return actual_url, None, None

    # Strategy 1: Direct decoded filename match in files/
    decoded_url = urllib.parse.unquote(actual_url)
    url_basename = os.path.basename(decoded_url.split('?')[0].split('#')[0])
    if url_basename and url_basename in cached_files_list:
        return actual_url, f"{cache_dir}/{url_basename}".replace('\\', '/'), url_basename

    # Strategy 2: Check for exact safe_filename match using full URL SHA-1
    expected_fn = safe_filename(title, actual_url)
    if expected_fn in cached_files_list:
        return actual_url, f"{cache_dir}/{expected_fn}".replace('\\', '/'), expected_fn

    # Strategy 3: Exact SHA-1 hash suffix match
    url_hash = hashlib.sha1(actual_url.encode('utf-8')).hexdigest()[:6]
    hash_pattern = f"_{url_hash}."
    for file in cached_files_list:
        if hash_pattern in file:
            return actual_url, f"{cache_dir}/{file}".replace('\\', '/'), file

    return actual_url, None, None

def search_academic_commons(title: str, author: str) -> str:
    """Searches Academic Commons and verifies result title similarity."""
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0'}
    clean_title = decode_html_entities(title)
    
    if not clean_title:
        return None
        
    words = clean_title.split()
    queries = []
    
    if author and str(author) != 'nan' and str(author).strip():
        clean_author = str(author).split()[0]
        queries.append(f"{' '.join(words[:5])} {clean_author}")
        
    queries.append(' '.join(words[:5]))
    if len(words) >= 3:
        queries.append(' '.join(words[:3]))

    for q in queries:
        if not q.strip():
            continue
        search_url = f"https://academiccommons.columbia.edu/search?q={urllib.parse.quote(q)}"
        try:
            req = urllib.request.Request(search_url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                html = resp.read().decode('utf-8')
                
                # Match links with anchor text to verify title similarity
                matches = re.findall(r'<a\s+href="(/doi/[^"]+|/catalog/[^"]+|/download/fedora_content/[^"]+)"[^>]*>(.*?)</a>', html, re.DOTALL | re.IGNORECASE)
                
                best_link = None
                best_score = 0.0
                for link, cand_text in matches:
                    cand_title = re.sub(r'<[^>]+>', '', cand_text).strip()
                    score = title_match_score(title, cand_title)
                    if score > best_score:
                        best_score = score
                        best_link = link
                
                # Require at least 50% title word overlap to reject false positives
                if best_link and best_score >= 0.5:
                    matched_url = f"https://academiccommons.columbia.edu{best_link}"
                    print(f"   [FOUND ACADEMIC COMMONS (Score: {best_score:.2f})] '{q}' -> {matched_url}")
                    return matched_url
        except Exception:
            continue
            
    return None

def search_climate_news(title: str) -> str:
    """Searches news.climate.columbia.edu via WordPress REST API with title validation."""
    clean_title = decode_html_entities(title)
    if not clean_title:
        return None

    words = clean_title.split()
    short_query = ' '.join(words[:5])

    api_url = f"https://news.climate.columbia.edu/wp-json/wp/v2/posts?search={urllib.parse.quote(short_query)}&per_page=3"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0'}

    try:
        req = urllib.request.Request(api_url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            if data and isinstance(data, list):
                for item in data:
                    cand_title = item.get('title', {}).get('rendered', '')
                    cand_link = item.get('link')
                    score = title_match_score(title, cand_title)
                    if cand_link and score >= 0.45:
                        print(f"   [FOUND CLIMATE NEWS (Score: {score:.2f})] '{short_query}' -> {cand_link}")
                        return cand_link
    except Exception:
        pass
        
    return None

def update_cached_links(input_csv="combined_data.csv", output_csv="combined_data_cached.csv", cache_dir="files"):
    """Parses CSV, checks online mirrors and local cache, and formats detailed output CSV."""
    
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir, exist_ok=True)
        cached_files_list = []
    else:
        cached_files_list = os.listdir(cache_dir)
        
    used_files = set()
    url_map_counts = defaultdict(list)
    
    links_to_files = []
    links_to_academic_commons = []
    links_to_climate_news = []
    links_still_iri = []
    links_dead_or_failed = []
    other_external_links = []

    try:
        with open(input_csv, mode='r', encoding='utf-8') as infile:
            reader = csv.DictReader(infile)
            original_fieldnames = list(reader.fieldnames or [])
            
            # Ensure custom URL columns exist in output CSV schema
            new_fieldnames = []
            for fn in original_fieldnames:
                new_fieldnames.append(fn)
                if fn == 'url':
                    if 'url_cached' not in new_fieldnames:
                        new_fieldnames.extend(['url_cached', 'url_secondary', 'url_source_type'])

            with open(output_csv, mode='w', encoding='utf-8', newline='') as outfile:
                writer = csv.DictWriter(outfile, fieldnames=new_fieldnames)
                writer.writeheader()
                
                total_count = 0
                
                for row in reader:
                    total_count += 1
                    original_url_field = str(row.get('url') or '')
                    title = str(row.get('title') or '')
                    author = str(row.get('author') or row.get('authors_pub') or '')
                    source_media = str(row.get('source_media') or '').lower()

                    actual_url = extract_clean_url(original_url_field)
                    if actual_url:
                        url_map_counts[actual_url].append((total_count, title))

                    is_iri = 'iri.columbia.edu' in actual_url
                    
                    primary_url = actual_url
                    url_cached = ""
                    url_secondary = ""
                    url_source_type = "original_external"

                    # Check local files/ cache
                    _, cached_rel_path, matched_filename = find_local_cached_file(
                        title, original_url_field, cache_dir, cached_files_list
                    )
                    if cached_rel_path:
                        url_cached = cached_rel_path
                        used_files.add(matched_filename)

                    if is_iri:
                        print(f"[{total_count}] Checking online mirrors for IRI link: '{title[:45]}...'")
                        
                        # Use source_media hints to order online searches
                        climate_hint = any(h in source_media for h in ['earth', 'climate', 'state of the planet', 'ei.columbia', 'blogs.ei', 'news.climate'])
                        
                        ac_match = None
                        news_match = None

                        if climate_hint:
                            news_match = search_climate_news(title)
                            if not news_match:
                                ac_match = search_academic_commons(title, author)
                        else:
                            ac_match = search_academic_commons(title, author)
                            if not ac_match:
                                news_match = search_climate_news(title)

                        if ac_match:
                            primary_url = ac_match
                            url_source_type = "academic_commons"
                            url_secondary = url_cached or (news_match or "")
                            links_to_academic_commons.append((title or 'Untitled', ac_match))
                        elif news_match:
                            primary_url = news_match
                            url_source_type = "climate_news"
                            url_secondary = url_cached or (ac_match or "")
                            links_to_climate_news.append((title or 'Untitled', news_match))
                        elif url_cached:
                            primary_url = url_cached
                            url_source_type = "local_cache"
                            links_to_files.append((title or 'Untitled', url_cached))
                        else:
                            url_source_type = "iri_unresolved"
                            links_still_iri.append((title or 'Untitled', actual_url))
                            links_dead_or_failed.append({
                                'title': title or 'Untitled',
                                'url': actual_url,
                                'reason': "No online mirror found on Academic Commons/Climate News and no local cache file"
                            })

                        time.sleep(0.2)

                    else:
                        if url_cached:
                            url_source_type = "local_cache"
                            links_to_files.append((title or 'Untitled', url_cached))
                        elif not actual_url or actual_url == '#':
                            url_source_type = "dead_or_empty"
                            links_dead_or_failed.append({
                                'title': title or 'Untitled',
                                'url': actual_url,
                                'reason': "Missing or empty URL (#)"
                            })
                        elif 'academiccommons.columbia.edu' in actual_url:
                            url_source_type = "academic_commons"
                            links_to_academic_commons.append((title or 'Untitled', actual_url))
                        elif 'news.climate.columbia.edu' in actual_url:
                            url_source_type = "climate_news"
                            links_to_climate_news.append((title or 'Untitled', actual_url))
                        else:
                            url_source_type = "original_external"
                            other_external_links.append((title or 'Untitled', actual_url))

                    # Format clean primary URL independent of data_type
                    row['url'] = primary_url
                    row['url_cached'] = url_cached
                    row['url_secondary'] = url_secondary
                    row['url_source_type'] = url_source_type

                    writer.writerow(row)

        print("\n==================================================")
        print("                FINAL LINK SUMMARY                ")
        print("==================================================")
        print(f"Total processed CSV entries:                   {total_count}")
        print(f"  1. Links to academiccommons.columbia.edu :   {len(links_to_academic_commons)}")
        print(f"  2. Links to news.climate.columbia.edu :      {len(links_to_climate_news)}")
        print(f"  3. Links to local cached files/ :           {len(links_to_files)}")
        print(f"  4. Links STILL pointing to iri.columbia.edu: {len(links_still_iri)}")
        print(f"  5. Other valid external domain links:        {len(other_external_links)}")
        print(f"  6. Dead / Failed / Unresolved URLs:          {len(links_dead_or_failed)}")
        print(f"\nUpdated CSV successfully saved to '{output_csv}'.")

        # Report Duplicate URLs in CSV
        duplicate_urls = {u: lst for u, lst in url_map_counts.items() if len(lst) > 1 and u != '#'}
        print("\n========================================")
        print(f"DUPLICATE URLS FOUND IN CSV ({len(duplicate_urls)}):")
        print("========================================")
        if duplicate_urls:
            for d_url, entries in duplicate_urls.items():
                print(f"  - URL: {d_url}")
                for r_num, r_title in entries:
                    print(f"      Row {r_num}: {r_title}")
                print()
        else:
            print("  None! All input URLs are unique.")

        # Report Unused Local Files
        unused_files = sorted(set(cached_files_list) - used_files)
        print("\n========================================")
        print(f"UNUSED FILES IN '{cache_dir}/' ({len(unused_files)}):")
        print("========================================")
        if unused_files:
            for f in unused_files:
                print(f"  - {f}")
        else:
            print("  None! All cached files were matched.")

        # Detailed Report: Links Still Pointing to IRI Columbia
        if links_still_iri:
            print("\n========================================")
            print(f"LINKS STILL POINTING TO IRI.COLUMBIA.EDU ({len(links_still_iri)}):")
            print("========================================")
            for t_item, url_item in links_still_iri:
                print(f"  - Title: {t_item}")
                print(f"    URL:   {url_item}\n")

        # Detailed Report: Dead or Failed URLs
        if links_dead_or_failed:
            print("\n========================================")
            print(f"DEAD / FAILED / UNRESOLVED URLS ({len(links_dead_or_failed)}):")
            print("========================================")
            for item in links_dead_or_failed:
                print(f"  - Title:        {item['title']}")
                print(f"    URL:          {item['url']}")
                print(f"    FAILURE REASON: {item['reason']}\n")

    except FileNotFoundError:
        print(f"Error: Input file '{input_csv}' was not found in current directory.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    update_cached_links()
