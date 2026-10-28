import csv
import os
import re

def clean_csv_file(input_file='combined_data.csv', output_file='combined_data_clean.csv'):
    """Reads combined_data.csv, cleans HTML anchor tags from the URL column,

    populates title column with extracted anchor text if applicable, and writes
    a clean CSV file.
    """
    if not os.path.exists(input_file):
        print(f"Error: Could not find input file '{input_file}' in current directory.")
        return

    cleaned_rows = []
    cleaned_count = 0

    with open(input_file, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames

        for row in reader:
            raw_url = str(row.get('url') or '').replace('""', '"').strip()
            raw_title = str(row.get('title') or '').strip()

            # Check if URL contains an HTML anchor tag <a href="...">Anchor Text</a>
            match = re.search(
                r'<a\s+[^>]*href=["\']?([^"\' >]+)["\']?[^>]*>(.*?)</a>',
                raw_url,
                re.IGNORECASE | re.DOTALL,
            )

            if match:
                clean_url = match.group(1).strip()
                extracted_title = re.sub(
                    r'<[^>]+>', '', match.group(2)
                ).strip()

                row['url'] = clean_url
                # Use extracted anchor text if existing title is missing or less detailed
                if not raw_title or raw_title.lower() == 'nan':
                    row['title'] = extracted_title
                else:
                    row['title'] = raw_title

                cleaned_count += 1
            else:
                row['url'] = raw_url
                row['title'] = raw_title

            cleaned_rows.append(row)

    # Save cleaned spreadsheet
    with open(output_file, mode='w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(cleaned_rows)

    print(
        f"✅ Cleaned {cleaned_count} rows containing HTML tags in URL column."
    )
    print(f"✅ Saved cleaned CSV to '{output_file}'.")


if __name__ == '__main__':
    clean_csv_file()
