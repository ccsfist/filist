import hashlib
import os
import re
import sys
import urllib.parse
import urllib.request
from html.parser import HTMLParser


class EnhancedImageLinkExtractor(HTMLParser):
  """Parses HTML documents to extract all image src, srcset, data-src, and lazy-loaded image URLs."""

  def __init__(self, base_url):
    super().__init__()
    self.base_url = base_url
    self.image_urls = set()

  def handle_starttag(self, tag, attrs):
    attrs_dict = dict(attrs)
    if tag in ('img', 'source'):
      # Check standard and lazy-loaded image attributes
      for attr_name in ('src', 'data-src', 'data-lazy-src', 'data-orig-file'):
        val = attrs_dict.get(attr_name)
        if val:
          full_url = urllib.parse.urljoin(self.base_url, val.strip())
          self.image_urls.add(full_url)

      # Check responsive srcset attributes
      srcset = attrs_dict.get('srcset') or attrs_dict.get('data-srcset')
      if srcset:
        for entry in srcset.split(','):
          parts = entry.strip().split()
          if parts:
            full_url = urllib.parse.urljoin(self.base_url, parts[0])
            self.image_urls.add(full_url)


def is_valid_image_url(url: str, base_url: str) -> bool:
  """Verifies that a URL is a legitimate image asset and not a webpage path or root slash."""
  if not url or url.startswith('data:'):
    return False

  parsed = urllib.parse.urlparse(url)
  base_parsed = urllib.parse.urlparse(base_url)

  path = parsed.path
  if not path or path == '/' or path.rstrip('/') == base_parsed.path.rstrip('/'):
    return False

  ext = os.path.splitext(path.split('?')[0])[1].lower()
  return ext in ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.ico')


def safe_filename(title: str, url: str, ext_override=None) -> str:
  """Generates a clean, safe filename using normalized title and SHA-1 hash."""
  clean_title = re.sub(r'[\W_]+', '_', title.lower()).strip('_')[:40] or 'doc'
  url_path = url.split('?')[0].split('#')[0]
  ext = ext_override or os.path.splitext(url_path)[1]

  allowed_exts = (
      '.html',
      '.jpg',
      '.jpeg',
      '.png',
      '.gif',
      '.webp',
      '.svg',
      '.pdf',
      '.doc',
      '.docx',
  )
  if not ext or len(ext) > 5 or ext.lower() not in allowed_exts:
    ext = '.html' if not ext_override else ext_override

  url_hash = hashlib.sha1(url.encode('utf-8')).hexdigest()[:6]
  return f'{clean_title}_{url_hash}{ext}'


def download_asset(url: str, output_path: str, headers: dict) -> bool:
  """Downloads a binary image or PDF asset to disk."""
  try:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as resp:
      data = resp.read()
      os.makedirs(os.path.dirname(output_path), exist_ok=True)
      with open(output_path, 'wb') as f:
        f.write(data)
      return True
  except Exception as e:
    print(f'   [Asset download failed] {url} -> {e}')
    return False


def cache_single_link(
    target_url: str, title: str = 'cached_document', output_dir: str = 'files'
) -> tuple[str, str]:
  """Downloads an HTML page or document, fetches image assets if HTML, rewrites image paths safely, and saves offline."""
  headers = {
      'User-Agent': (
          'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
      )
  }
  images_dir = os.path.join(output_dir, 'images')
  os.makedirs(images_dir, exist_ok=True)

  url_path = target_url.split('?')[0].split('#')[0]
  ext = os.path.splitext(url_path)[1].lower()

  # Handle direct PDF or binary document downloads
  if ext in ['.pdf', '.doc', '.docx', '.txt', '.zip']:
    doc_filename = safe_filename(title, target_url, ext_override=ext)
    doc_path = os.path.join(output_dir, doc_filename)

    print(f'   [Downloading document] {target_url}')
    if download_asset(target_url, doc_path, headers):
      local_debug_path = f'{output_dir}/{doc_filename}'.replace('\\', '/')
      github_url = f'https://ccsfist.github.io/filist/{local_debug_path}'
      return local_debug_path, github_url
    return None, None

  # Fetch HTML webpage
  print(f'   [Fetching webpage] {target_url}')
  try:
    req = urllib.request.Request(target_url, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as resp:
      raw_html = resp.read().decode('utf-8', errors='ignore')
  except Exception as e:
    print(f'   [Webpage fetch failed] {target_url} -> {e}')
    return None, None

  # Extract image URLs
  parser = EnhancedImageLinkExtractor(target_url)
  parser.feed(raw_html)

  # Filter to strictly valid image assets
  valid_image_urls = [
      u for u in parser.image_urls if is_valid_image_url(u, target_url)
  ]
  print(
      f'   [Found {len(valid_image_urls)} image/GIF assets to fetch and'
      ' localize]'
  )

  # Download image assets locally
  url_to_local_rel = {}
  for img_url in valid_image_urls:
    img_ext = os.path.splitext(img_url.split('?')[0])[1] or '.jpg'
    img_filename = safe_filename('img', img_url, ext_override=img_ext)
    local_img_path = os.path.join(images_dir, img_filename)

    if not os.path.exists(local_img_path):
      download_asset(img_url, local_img_path, headers)

    url_to_local_rel[img_url] = f'images/{img_filename}'

  # Safe HTML rewrite targeting specific image attributes
  modified_html = raw_html

  for img_url, local_rel in url_to_local_rel.items():
    # 1. Replace full absolute URL in HTML
    modified_html = modified_html.replace(img_url, local_rel)

    # 2. Replace relative paths safely inside HTML src/srcset attributes
    parsed = urllib.parse.urlparse(img_url)
    path = parsed.path
    if path and path != '/':
      modified_html = re.sub(
          r'(src|srcset|data-src|data-lazy-src|data-orig-file)=["\']'
          + re.escape(path)
          + r'(?:\?[^"\']*)?["\']',
          r'\1="' + local_rel + '"',
          modified_html,
          flags=re.IGNORECASE,
      )

      rel_path = path.lstrip('/')
      if rel_path:
        modified_html = re.sub(
            r'(src|srcset|data-src|data-lazy-src|data-orig-file)=["\']'
            + re.escape(rel_path)
            + r'(?:\?[^"\']*)?["\']',
            r'\1="' + local_rel + '"',
            modified_html,
            flags=re.IGNORECASE,
        )

  # Save local HTML file
  html_filename = safe_filename(title, target_url, ext_override='.html')
  output_html_path = os.path.join(output_dir, html_filename)

  with open(output_html_path, 'w', encoding='utf-8') as f:
    f.write(modified_html)

  local_debug_path = f'{output_dir}/{html_filename}'.replace('\\', '/')
  github_url = f'https://ccsfist.github.io/filist/{local_debug_path}'

  return local_debug_path, github_url


def main():
  if len(sys.argv) > 1:
    target_url = sys.argv[1]
    title = sys.argv[2] if len(sys.argv) > 2 else 'cached_document'
  else:
    target_url = input('Enter the IRI URL to cache: ').strip()
    title = (
        input('Enter title for filename (optional, press Enter to default): ')
        .strip()
        or 'cached_document'
    )

  if not target_url:
    print('Error: No URL provided.')
    sys.exit(1)

  print(f'\nCaching single URL: {target_url}')
  local_debug, github_url = cache_single_link(target_url, title=title)

  if local_debug and github_url:
    print('\n' + '=' * 50)
    print('SUCCESSFULLY CACHED')
    print('=' * 50)
    print(f'Local debug path: {local_debug}')
    print(f'GitHub Pages URL: {github_url}')
  else:
    print('\nFailed to cache the provided URL.')


if __name__ == '__main__':
  main()
