import csv
import hashlib
import os
import re
import shutil
import sys
import urllib.parse
from collections import defaultdict


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


def get_url_sha1_hash(url: str) -> str:
  """Generates 6-character SHA-1 hash for a URL."""
  clean = extract_clean_url(url)
  return hashlib.sha1(clean.encode('utf-8')).hexdigest()[:6].lower()


def analyze_html_file(filepath: str) -> dict:
  """Analyzes local HTML file for images, 404 errors, and file size to compute a quality score."""
  try:
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
      content = f.read()

    size = os.path.getsize(filepath)
    has_images = bool(re.search(r'<img\s|images/', content, re.IGNORECASE))
    is_404 = bool(
        re.search(r'404\s+Not\s+Found|Page\s+not\s+found', content, re.IGNORECASE)
    )

    # Scoring algorithm
    score = 0
    if not is_404:
      score += 1000
    if has_images:
      score += 500
    score += min(size / 1000, 100)

    return {
        'filepath': filepath,
        'filename': os.path.basename(filepath),
        'size': size,
        'has_images': has_images,
        'is_404': is_404,
        'score': score,
    }
  except Exception as e:
    return {
        'filepath': filepath,
        'filename': os.path.basename(filepath),
        'size': 0,
        'has_images': False,
        'is_404': True,
        'score': -1,
    }


def cleanup_and_sync_cache(files_dir='files'):
  """Audits cached HTML files, moves false versions to files/false/, and generates clean CSV."""
  if not os.path.exists(files_dir):
    print(f"Error: Directory '{files_dir}' not found.")
    sys.exit(1)

  false_dir = os.path.join(files_dir, 'false')
  os.makedirs(false_dir, exist_ok=True)

  # Group all HTML files in files/ by 6-character SHA-1 hash
  hash_groups = defaultdict(list)
  all_files = os.listdir(files_dir)

  for filename in all_files:
    filepath = os.path.join(files_dir, filename)
    if os.path.isdir(filepath):
      continue
    if not filename.lower().endswith('.html'):
      continue

    # Extract 6-char hash before extension (_<hash>.html)
    match = re.search(
        r'_([a-f0-9]{6})\.([a-z0-9]+)$', filename, re.IGNORECASE
    )
    if match:
      file_hash = match.group(1).lower()
      hash_groups[file_hash].append((filename, filepath))

  print(f'Found {len(hash_groups)} unique file hash groups in {files_dir}/.')

  # Rank candidates within each hash group
  verified_winners = {}  # hash -> winner_filename
  moved_false_count = 0

  for file_hash, file_list in hash_groups.items():
    analyzed_list = []
    for fn, fp in file_list:
      info = analyze_html_file(fp)
      analyzed_list.append(info)

    # Sort descending by quality score
    analyzed_list.sort(key=lambda x: x['score'], reverse=True)
    best_candidate = analyzed_list[0]

    if not best_candidate['is_404']:
      verified_winners[file_hash] = best_candidate['filename']
      # Move remaining lower-ranked duplicate or broken files to files/false/
      for false_item in analyzed_list[1:]:
        dest = os.path.join(false_dir, false_item['filename'])
        shutil.move(false_item['filepath'], dest)
        moved_false_count += 1
    else:
      # If all files in group are 404 error pages, move all to files/false/
      for false_item in analyzed_list:
        dest = os.path.join(false_dir, false_item['filename'])
        shutil.move(false_item['filepath'], dest)
        moved_false_count += 1

  print(
      f'Moved {moved_false_count} broken/false/duplicate HTML files to'
      f' {false_dir}/.'
  )
  print(
      f'Preserved {len(verified_winners)} verified cached HTML files in'
      f' {files_dir}/.'
  )

  # Auto-detect input CSV file
  input_csv = None
  for candidate in [
      'combined_data_3_cached.csv',
      'combined_data_3.csv',
      'combined_data_audited.csv',
      'combined_data_clean.csv',
      'combined_data.csv',
  ]:
    if os.path.exists(candidate):
      input_csv = candidate
      break

  if not input_csv:
    print('Error: No input CSV file found.')
    sys.exit(1)

  print(f"Reading CSV data from: '{input_csv}'")

  rows = []
  with open(input_csv, mode='r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    fieldnames = list(reader.fieldnames or [])

    # Ensure required audit columns exist
    for col in [
        'original_source_url',
        'local_debug_url',
        'url_cached',
        'url_secondary',
        'url_source_type',
        'notes',
    ]:
      if col not in fieldnames:
        fieldnames.append(col)

    matched_count = 0
    unresolved_count = 0

    for row in reader:
      raw_url = str(row.get('url') or '')
      clean_url = extract_clean_url(raw_url)
      original = str(row.get('original_source_url') or clean_url).strip()

      if not row.get('original_source_url'):
        row['original_source_url'] = original

      # Extract 6-char hash from existing URL or calculate from original URL
      target_hash = None
      match_existing = re.search(
          r'_([a-f0-9]{6})\.(html|pdf|doc|docx)', clean_url, re.IGNORECASE
      )
      if match_existing:
        target_hash = match_existing.group(1).lower()
      else:
        target_hash = get_url_sha1_hash(original)

      # Check if a preserved winner file exists for this hash
      if target_hash in verified_winners:
        winner_file = verified_winners[target_hash]
        encoded_winner = urllib.parse.quote(winner_file)

        local_path = f'files/{winner_file}'
        github_url = f'https://ccsfist.github.io/filist/files/{encoded_winner}'

        row['url'] = github_url
        row['local_debug_url'] = local_path
        row['url_cached'] = local_path
        row['url_source_type'] = 'local_cache'
        matched_count += 1
      else:
        # No local cached file available
        row['url'] = original
        row['local_debug_url'] = ''
        row['url_cached'] = ''
        row['url_source_type'] = (
            'iri_unresolved'
            if 'iri.columbia.edu' in original
            else 'original_external'
        )
        unresolved_count += 1

      rows.append(row)

  # Output to both combined_data.csv and combined_data_audited.csv
  for output_csv in ['combined_data.csv', 'combined_data_audited.csv']:
    with open(output_csv, mode='w', encoding='utf-8', newline='') as f:
      writer = csv.DictWriter(f, fieldnames=fieldnames)
      writer.writeheader()
      writer.writerows(rows)
    print(f"Saved updated dataset to: '{output_csv}'")

  print('\n' + '=' * 50)
  print('CLEANUP SUMMARY')
  print('=' * 50)
  print(f'Total CSV rows processed:      {len(rows)}')
  print(f'Rows matched to valid cache:  {matched_count}')
  print(f'Rows with unresolved links:   {unresolved_count}')
  print(f'False/duplicate files moved:  {moved_false_count}')


if __name__ == '__main__':
  cleanup_and_sync_cache()
