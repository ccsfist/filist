import csv
import hashlib
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from html.parser import HTMLParser


class ImageLinkExtractor(HTMLParser):
  """Parses HTML documents to extract all image src and srcset URLs."""

  def __init__(self, base_url):
    super().__init__()
    self.base_url = base_url
    self.image_urls = set()

  def handle_starttag(self, tag, attrs):
    attrs_dict = dict(attrs)
    if tag == 'img':
      src = attrs_dict.get('src')
      if src:
        self.image_urls.add(urllib.parse.urljoin(self.base_url, src.strip()))

      srcset = attrs_dict.get('srcset')
      if srcset:
        for entry in srcset.split(','):
          parts = entry.strip().split()
          if parts:
            self.image_urls.add(
                urllib.parse.urljoin(self.base_url, parts[0])
            )


def extract_clean_url(url_field: str) -> str:
  """Extracts raw URL string from plain text or <a href="..."> tags."""
  if not url_field:
    return ''
  clean_field = url_field.replace('""', '"').strip()
  match = re.search(
      r'href=["\']?([^"\' >]+)["\']?', clean_field, re.IGNORECASE
  )
  if match:
    return match.group(1).strip()
  return clean_field


def safe_filename(title: str, url: str, ext_override=None) -> str:
  """Generates a clean, safe filename using normalized title and SHA-1 hash."""
  clean_title = re.sub(r'[\W_]+', '_', title.lower()).strip('_')[:40] or 'doc'
  url_path = url.split('?')[0].split('#')[0]
  ext = ext_override or os.path.splitext(url_path)[1]

  if (
      not ext
      or len(ext) > 5
      or ext.lower()
      not in ('.html', '.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg')
  ):
    ext = '.html' if not ext_override else ext_override

  url_hash = hashlib.sha1(url.encode('utf-8')).hexdigest()[:6]
  return f'{clean_title}_{url_hash}{ext}'


def download_asset(url: str, output_path: str, headers: dict) -> bool:
  """Downloads a binary image or PDF asset to disk."""
  try:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=12) as resp:
      data = resp.read()
      os.makedirs(os.path.dirname(output_path), exist_ok=True)
      with open(output_path, 'wb') as f:
        f.write(data)
      return True
  except Exception as e:
    print(f'   [Asset download failed] {url} -> {e}')
    return False


def cache_url_with_images(
    target_url: str, title: str = 'webpage', output_dir: str = 'files'
) -> tuple[str, str]:
  """Downloads an HTML page, fetches image assets, rewrites image paths, and saves offline HTML.

  Returns tuple of (local_debug_url, github_pages_url).
  """
  headers = {
      'User-Agent': (
          'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
      )
  }
  images_dir = os.path.join(output_dir, 'images')
  os.makedirs(images_dir, exist_ok=True)

  url_path = target_url.split('?')[0].split('#')[0]
  ext = os.path.splitext(url_path)[1].lower()

  # Handle direct PDF or non-HTML document downloads
  if ext in ['.pdf', '.doc', '.docx', '.txt', '.zip']:
    doc_filename = safe_filename(title, target_url, ext_override=ext)
    doc_path = os.path.join(output_dir, doc_filename)

    if not os.path.exists(doc_path):
      print(f'   [Downloading document] {target_url}')
      download_asset(target_url, doc_path, headers)

    local_debug_path = f'{output_dir}/{doc_filename}'.replace('\\', '/')
    github_url = f'https://ccsfist.github.io/filist/{local_debug_path}'
    return local_debug_path, github_url

  # Fetch HTML webpage
  print(f'   [Fetching webpage] {target_url}')
  try:
    req = urllib.request.Request(target_url, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as resp:
      raw_html = resp.read().decode('utf-8', errors='ignore')
  except Exception as e:
    print(f'   [Webpage fetch failed] {target_url} -> {e}')
    return None, None

  # Parse image URLs
  parser = ImageLinkExtractor(target_url)
  parser.feed(raw_html)
  image_urls = parser.image_urls

  # Download image assets locally
  url_to_local_rel = {}
  for img_url in image_urls:
    if img_url.startswith('data:'):
      continue

    img_ext = os.path.splitext(img_url.split('?')[0])[1] or '.jpg'
    img_filename = safe_filename('img', img_url, ext_override=img_ext)
    local_img_path = os.path.join(images_dir, img_filename)

    if not os.path.exists(local_img_path):
      download_asset(img_url, local_img_path, headers)

    url_to_local_rel[img_url] = f'images/{img_filename}'

  # Rewrite HTML image src / srcset attributes
  modified_html = raw_html
  for img_url, local_rel in url_to_local_rel.items():
    modified_html = modified_html.replace(img_url, local_rel)
    parsed = urllib.parse.urlparse(img_url)
    if parsed.path:
      modified_html = modified_html.replace(parsed.path, local_rel)

  # Save local HTML file
  html_filename = safe_filename(title, target_url, ext_override='.html')
  output_html_path = os.path.join(output_dir, html_filename)

  with open(output_html_path, 'w', encoding='utf-8') as f:
    f.write(modified_html)

  local_debug_path = f'{output_dir}/{html_filename}'.replace('\\', '/')
  github_url = f'https://ccsfist.github.io/filist/{local_debug_path}'

  return local_debug_path, github_url


def process_csv_caching(
    input_csv='combined_data.csv',
    output_csv='combined_data_with_cached.csv',
    output_dir='files',
):
  """Reads CSV, caches iri.columbia.edu URLs (excluding ~deo), and writes updated CSV."""
  if not os.path.exists(input_csv):
    print(f"Error: Input file '{input_csv}' not found.")
    sys.exit(1)

  os.makedirs(output_dir, exist_ok=True)

  rows = []
  with open(input_csv, mode='r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    fieldnames = list(reader.fieldnames or [])

    # Ensure output CSV contains new columns
    for col in ['original_source_url', 'local_debug_url', 'url_cached', 'url_source_type']:
      if col not in fieldnames:
        fieldnames.append(col)

    total_count = 0
    cached_count = 0
    skipped_deo_count = 0

    for row in reader:
      total_count += 1
      raw_url = str(row.get('url') or '')
      clean_url = extract_clean_url(raw_url)
      title = str(row.get('title') or 'document')

      # Ensure original_source_url is populated
      if not row.get('original_source_url'):
        row['original_source_url'] = clean_url

      # Check IRI domain and exclude ~deo
      is_iri = 'iri.columbia.edu' in clean_url
      is_deo = 'iri.columbia.edu/~deo' in clean_url

      if is_deo:
        skipped_deo_count += 1
        print(f'[{total_count}] Skipped (~deo exclusion): {clean_url}')
        row['url'] = clean_url
      elif is_iri:
        print(f'[{total_count}] Caching IRI page: {title[:50]}...')
        local_debug, github_url = cache_url_with_images(
            clean_url, title=title, output_dir=output_dir
        )

        if local_debug and github_url:
          cached_count += 1
          row['url'] = github_url
          row['local_debug_url'] = local_debug
          row['url_cached'] = local_debug
          row['url_source_type'] = 'local_cache'
          print(f'    -> Local debug: {local_debug}')
          print(f'    -> GitHub Pages URL: {github_url}')
        else:
          print(f'    -> Caching failed for {clean_url}')
          row['url'] = clean_url

        time.sleep(0.3)
      else:
        # Non-IRI link: leave url as is
        row['url'] = clean_url

      rows.append(row)

  # Write updated spreadsheet
  with open(output_csv, mode='w', encoding='utf-8', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

  print('\n' + '=' * 50)
  print('CACHING SUMMARY')
  print('=' * 50)
  print(f'Total CSV rows processed:         {total_count}')
  print(f'IRI pages successfully cached:   {cached_count}')
  print(f'~deo URLs skipped (excluded):    {skipped_deo_count}')
  print(f"Output CSV saved to:             '{output_csv}'")


if __name__ == '__main__':
  process_csv_caching()
