import argparse
import csv
import hashlib
import io
import os
import re
import sys
from datetime import datetime
from typing import Any, Dict, List


def format_title_link(title: str, url: str) -> str:
  """Formats title and plain URL into an anchor tag <a href="..." target="_blank">Title</a>.

  If url is already an HTML anchor tag, returns url directly.
  """
  if not url or url == '#':
    return f'<a href="#">{title}</a>'

  clean_url = url.strip()
  if (
      clean_url.startswith('<a ')
      or clean_url.startswith('<a\n')
      or clean_url.startswith('<a\r')
  ):
    return clean_url

  return f'<a href="{clean_url}" target="_blank">{title}</a>'


def parse_date(
    raw_date_str: str, entry_type: str, row: Dict[str, Any]
) -> datetime:
  """Parses date string into a datetime object for sorting."""

  # --- Logic for News/Feature and Media Mention (MM/DD/YY) ---
  if entry_type in ['News/Feature', 'Media Mention']:
    raw_date_str = str(raw_date_str or '').strip()
    if not raw_date_str:
      row['date_str'] = ''
      return datetime(1900, 1, 1)

    try:
      date_obj = datetime.strptime(raw_date_str, '%m/%d/%y')
      row['date_str'] = date_obj.strftime('%B %d, %Y')
      return date_obj
    except ValueError:
      row['date_str'] = ''
      return datetime(1900, 1, 1)

  # --- Logic for Publication (YYYY, M) ---
  elif entry_type == 'Publication':
    raw_year = str(row.get('published_year') or '').strip()
    raw_month = str(row.get('published_month') or '').strip()

    try:
      year = int(float(raw_year)) if raw_year else 1900
    except ValueError:
      year = 1900

    try:
      month = (
          int(float(raw_month))
          if raw_month and raw_month.strip() != '0'
          else 1
      )
      if not (1 <= month <= 12):
        month = 1
    except ValueError:
      month = 1

    try:
      date_obj = datetime(year, month, 1)
      date_str = date_obj.strftime('%B %Y')

      if year == 1900:
        date_str = ''
      elif month == 1 and year > 1900 and not raw_month:
        date_str = date_obj.strftime('%Y')

      row['date_str'] = date_str
      return date_obj
    except ValueError:
      row['date_str'] = ''
      return datetime(1900, 1, 1)

  row['date_str'] = ''
  return datetime(1900, 1, 1)


def parse_csv_data(filename: str) -> List[Dict[str, Any]]:
  """Reads the CSV file, parses data, and applies date logic."""
  entries = []

  try:
    with open(filename, mode='r', encoding='utf-8') as f:
      reader = csv.DictReader(f)

      for row in reader:
        entry_type = row.get('data_type')
        if not entry_type:
          continue

        row['data_type'] = entry_type
        row['date_obj'] = parse_date(row.get('date'), entry_type, row)
        entries.append(row)

  except FileNotFoundError:
    print(f"Error: The file '{filename}' was not found.")
    sys.exit(1)
  except Exception as e:
    print(f'An unexpected error occurred during CSV parsing: {e}')
    sys.exit(1)

  return entries


def generate_html(entries: List[Dict[str, Any]]) -> str:
  """Generates the main HTML content for the entry list."""

  html_entries = []

  for row in entries:
    data_type = row.get('data_type')
    type_label = {
        'News/Feature': 'News/Feature',
        'Publication': 'Publication',
        'Media Mention': 'Media Mention',
    }.get(data_type, 'Entry')

    url = str(row.get('url') or '#').strip()
    title = str(row.get('title') or 'Untitled').strip()
    date_str = str(row.get('date_str') or '').strip()
    title_link = format_title_link(title, url)

    if data_type == 'Publication':
      # --- Publication Format ---
      authors_pub = (
          str(row.get('authors_pub') or '')
          .replace('\n', ' ')
          .replace('<br />', ' ')
      )
      publisher = str(row.get('publisher') or '').strip()
      journal = str(row.get('journal') or '').strip()
      volume = str(row.get('volume') or '').strip()
      issue = str(row.get('issue') or '').strip()

      meta_parts = []
      if authors_pub:
        meta_parts.append(f'<span class="author-list">{authors_pub}</span>')
      if date_str:
        meta_parts.append(f'<span class="date">{date_str}</span>')

      meta_str = ', '.join(meta_parts)

      details_parts = []
      if publisher:
        details_parts.append(publisher)
      if journal:
        details_parts.append(journal)
      if volume:
        details_parts.append(f'Vol. {volume}')
      if issue:
        details_parts.append(f'Issue {issue}')

      details_str = ', '.join(details_parts)

      metadata_html = f"""
                <div class="entry-meta">
                    {meta_str}.
                </div>
            """

      html_content = f"""
            <li class="">
                {metadata_html}
                <div class="entry-title">
                    {title_link}
                    <span class="type-label">[{type_label}]</span>
                </div>
                {f'<div class="entry-meta">{details_str}.</div>' if details_str else ''}
            </li>
            """

    elif data_type == 'Media Mention':
      # --- Media Mention Format ---
      source_media = str(row.get('source_media') or '').strip()

      html_content = f"""
            <li class="">
                <span class="entry-title">
                    {title_link}
                    <span class="type-label">[{type_label}]</span>
                </span>
                <span class="entry-meta">
                    (<span class="date">{date_str}</span>) in {source_media}
                </span>
            </li>
            """

    elif data_type == 'News/Feature':
      # --- News/Feature Format ---
      author = str(row.get('author') or '').strip()
      imagename = str(row.get('imagename') or '').strip()
      excerpt = str(row.get('excerpt') or '').strip()

      image_html = ''
      if imagename and os.path.exists(os.path.join('images', imagename)):
        image_html = (
            f'<img src="images/{imagename}" alt="{title}"'
            ' class="entry-image">'
        )

      meta_str = (
          f'by {author} on <span class="date">{date_str}</span>'
          if author and date_str
          else ''
      )
      meta_str = meta_str or (
          f'on <span class="date">{date_str}</span>' if date_str else ''
      )
      meta_str = meta_str or (f'by {author}' if author else '')

      html_content = f"""
            <li class="clearfix">
                {image_html}
                <div class="news-content-wrapper">
                    <div class="entry-title">
                        {title_link}
                        <span class="type-label">[{type_label}]</span>
                        <span class="entry-meta">{meta_str}</span>
                    </div>
                    {f'<div class="entry-abstract">{excerpt}</div>' if excerpt else ''}
                </div>
            </li>
            """
    else:
      continue

    html_entries.append(html_content)

  # --- Google Analytics 4 Tracking Code ---
  GA_TRACKING_CODE = """
    <script async src="https://www.googletagmanager.com/gtag/js?id=G-YM4PVFJE0F"></script>
    <script>
      window.dataLayer = window.dataLayer || [];
      function gtag(){dataLayer.push(arguments);}
      gtag('js', new Date());

      gtag('config', 'G-YM4PVFJE0F');
    </script>
    """

  # --- HTML Shell ---
  HTML_SHELL = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Financial Instruments Links</title>
    {GA_TRACKING_CODE}
    <style>
        
        /* Set full browser window background to white */
        body {{ font-family: 'Helvetica Neue', Arial, sans-serif; margin: 0; padding: 0; background-color: #fff; color: #333; }} 
        
        /* Blue header bar across the top of the page */
        .header-bar {{ background-color: #01349A; padding: 15px 0; margin-bottom: 30px; }}
        
        /* White title styling and positioning, centered with content area */
        .header-title {{ max-width: 960px; margin: 0 auto; padding: 0 20px; font-size: 28px; color: white; font-weight: 500; }} 
        
        /* Content container */
        .container {{ max-width: 960px; margin: 0 auto; padding: 0 20px 20px 20px; background-color: #fff; }} 
        
        /* General list styles */
        .entry-list {{ list-style: none; padding: 0; }}
        .entry-list > li {{ margin-bottom: 25px; border-bottom: 1px dashed #eee; padding-bottom: 15px; }}
        .entry-list > li:last-child {{ border-bottom: none; margin-bottom: 0; padding-bottom: 0; }}
        
        /* Entry component styles */
        .entry-title {{ font-weight: 600; font-size: 16px; margin-right: 5px; display: inline; }}
        .entry-title a {{ color: #1e62a3; text-decoration: none; }}
        .entry-title a:hover {{ text-decoration: underline; color: #004c99; }}
        .entry-meta {{ font-size: 13px; color: #666; margin-top: 3px; display: block; }}
        
        /* Ensure abstract text displays fully without truncation or overflow limits */
        .entry-abstract {{ 
            font-size: 14px; 
            color: #444; 
            margin-top: 5px; 
            padding: 8px 0 0 0; 
            white-space: normal;
            overflow: visible;
            word-wrap: break-word; 
        }}

        /* Styling for the image in news/feature entries */
        .entry-image {{
            float: left; 
            margin-right: 15px; 
            margin-bottom: 15px; 
            max-width: 150px; 
            height: auto;
            border-radius: 4px;
        }}

        /* Wrapper to contain the floated image and the text content */
        .news-content-wrapper {{
            display: flow-root; 
        }}

        /* Class to clear the float after the news entry is complete. */
        .clearfix::after {{
            content: "";
            display: table;
            clear: both;
        }}
        
        /* Specialized styles */
        .date {{ font-weight: 500; color: #993300; }}
        .author-list {{ font-style: italic; }}
        .type-label {{ color: #004c99; font-size: 11px; font-weight: normal; margin-left: 8px; }}
    
    </style>
</head>
<body>
    <div class="header-bar">
        <div class="header-title">Financial Instruments Links</div>
    </div>
    <div class="container">
<ul class='entry-list'>

{os.linesep.join(html_entries)}

</ul>
    </div>
</body>
</html>
"""

  return HTML_SHELL


def main():
  parser = argparse.ArgumentParser(
      description='Generate an HTML file from pre-combined CSV data.'
  )
  parser.add_argument(
      '--input',
      type=str,
      default=None,
      help='Path to input CSV file. Defaults to auto-detecting audited/clean CSV.',
  )
  args = parser.parse_args()

  # Auto-select best input file if not explicitly specified
  input_file = args.input
  if not input_file:
    for candidate in [
        'combined_data_audited.csv',
        'combined_data_clean.csv',
        'combined_data.csv',
    ]:
      if os.path.exists(candidate):
        input_file = candidate
        break

  if not input_file or not os.path.exists(input_file):
    print('Error: No valid input CSV file found.')
    sys.exit(1)

  print(f"Loading data from: '{input_file}'")

  all_entries = parse_csv_data(input_file)
  all_entries.sort(key=lambda x: x['date_obj'], reverse=True)

  html_output = generate_html(all_entries)

  output_filename = 'index.html'
  with open(output_filename, 'w', encoding='utf-8') as f:
    f.write(html_output)

  print(f"Successfully generated HTML file: {output_filename}")


if __name__ == '__main__':
  main()
