import csv
import json
import os
import re
from datetime import datetime

def parse_date(row: dict) -> datetime:
    """Replicates parse_date from make_simplefihtml.py for exact chronological sorting."""
    entry_type = row.get('data_type')
    
    # News/Feature and Media Mention (MM/DD/YY)
    if entry_type in ['News/Feature', 'Media Mention']:
        raw_date_str = str(row.get('date') or '').strip()
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

    # Publication (YYYY, M)
    elif entry_type == 'Publication':
        raw_year = str(row.get('published_year') or '').strip()
        raw_month = str(row.get('published_month') or '').strip()

        try:
            year = int(raw_year) if raw_year else 1900
        except ValueError:
            year = 1900
                
        try:
            month = int(raw_month) if raw_month and raw_month.strip() != '0' else 1
            if not (1 <= month <= 12): month = 1
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

def infer_source_type(url: str) -> str:
    """Infers source type classification based on URL domain or format."""
    if not url or url == '#':
        return "dead_or_empty"
    elif 'academiccommons.columbia.edu' in url:
        return "academic_commons"
    elif 'news.climate.columbia.edu' in url:
        return "climate_news"
    elif 'files/' in url or url.endswith(('.pdf', '.html', '.doc', '.docx')):
        return "local_cache"
    elif '<a' in url:
        return "custom_html"
    elif 'iri.columbia.edu' in url:
        return "iri_unresolved"
    return "original_external"

def generate_preview_html(input_csv="combined_data_cached.csv", output_html="preview.html"):
    if not os.path.exists(input_csv):
        print(f"Error: Could not find '{input_csv}'.")
        return

    rows = []
    with open(input_csv, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if 'notes' not in row:
                row['notes'] = ""
            if 'custom_url' not in row:
                row['custom_url'] = ""  # Empty by default
            if 'url_cached' not in row:
                row['url_cached'] = ""
            if 'url_secondary' not in row:
                row['url_secondary'] = ""
            if 'url_source_type' not in row or not row['url_source_type']:
                row['url_source_type'] = infer_source_type(str(row.get('url') or ''))

            date_obj = parse_date(row)
            row['_sort_timestamp'] = date_obj.timestamp()
            rows.append(row)

    # Sort reverse-chronologically by date_obj (newest first), matching make_simplefihtml.py
    rows.sort(key=lambda r: r['_sort_timestamp'], reverse=True)

    for idx, row in enumerate(rows, start=1):
        row['display_order'] = idx
        del row['_sort_timestamp']

    rows_json = json.dumps(rows)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>index.html Display Order & Link Audit Previewer</title>
    <style>
        body {{
            font-family: 'Helvetica Neue', Arial, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #f6f8fa;
            color: #333;
        }}
        .header {{
            position: sticky;
            top: 0;
            background: #01349A;
            color: white;
            padding: 15px 25px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.15);
            z-index: 1000;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .header h1 {{ margin: 0; font-size: 1.3rem; font-weight: 500; }}
        .btn-export {{
            background-color: #2ea44f;
            color: white;
            border: none;
            padding: 10px 18px;
            font-weight: bold;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.9rem;
        }}
        .btn-export:hover {{ background-color: #2c974b; }}
        
        .container {{
            max-width: 960px;
            margin: 20px auto;
            padding: 0 20px;
        }}

        .card {{
            background: white;
            border: 1px solid #e1e4e8;
            border-radius: 8px;
            margin: 20px 0;
            padding: 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }}
        .card-header {{
            font-size: 0.85rem;
            color: #586069;
            font-weight: bold;
            margin-bottom: 12px;
            display: flex;
            justify-content: space-between;
            border-bottom: 1px solid #f0f0f0;
            padding-bottom: 6px;
        }}

        /* Simulation of make_simplefihtml.py rendering */
        .site-preview-box {{
            background: #ffffff;
            border: 1px dashed #bbb;
            padding: 16px;
            border-radius: 6px;
            margin-bottom: 15px;
        }}
        .entry-title {{ font-weight: 600; font-size: 16px; margin-right: 5px; display: inline; }}
        .entry-title a {{ color: #1e62a3; text-decoration: none; }}
        .entry-title a:hover {{ text-decoration: underline; color: #004c99; }}
        .entry-meta {{ font-size: 13px; color: #666; margin-top: 3px; display: block; }}
        .entry-abstract {{ 
            font-size: 14px; 
            color: #444; 
            margin-top: 5px; 
            padding: 8px 0 0 0; 
            word-wrap: break-word; 
        }}
        .date {{ font-weight: 500; color: #993300; }}
        .author-list {{ font-style: italic; }}
        .type-label {{ color: #004c99; font-size: 11px; font-weight: normal; margin-left: 8px; }}

        /* Audit Panel */
        .audit-panel {{
            background: #f1f8ff;
            border: 1px solid #c8e1ff;
            padding: 15px;
            border-radius: 6px;
        }}
        .link-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
            gap: 12px;
            margin-top: 10px;
            margin-bottom: 12px;
        }}
        .link-option {{
            background: white;
            border: 1px solid #e1e4e8;
            padding: 10px;
            border-radius: 5px;
            font-size: 0.85rem;
        }}
        .link-option.primary-active {{
            border-color: #2ea44f;
            background-color: #f0fff4;
        }}
        .link-label {{
            font-weight: bold;
            display: block;
            margin-bottom: 4px;
        }}
        .url-text {{
            word-break: break-all;
            color: #586069;
            font-family: monospace;
            font-size: 0.78rem;
            margin-bottom: 8px;
            display: block;
        }}
        .btn-test {{
            display: inline-block;
            background: #0366d6;
            color: white;
            text-decoration: none;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.75rem;
        }}
        .btn-test:hover {{ background: #024ea4; }}

        .action-dot {{
            display: inline-block;
            margin-top: 6px;
            font-size: 0.78rem;
            color: #0366d6;
            cursor: pointer;
            font-weight: 600;
        }}
        .action-dot:hover {{
            text-decoration: underline;
        }}

        .custom-input {{
            width: 100%;
            padding: 6px;
            border: 1px solid #d1d5da;
            border-radius: 4px;
            font-family: monospace;
            font-size: 0.78rem;
            box-sizing: border-box;
            margin-top: 4px;
            margin-bottom: 6px;
        }}
        
        .notes-box {{
            margin-top: 12px;
        }}
        .notes-box label {{
            font-weight: bold;
            font-size: 0.85rem;
            display: block;
            margin-bottom: 4px;
            color: #24292e;
        }}
        .notes-input {{
            width: 100%;
            height: 55px;
            padding: 8px;
            border: 1px solid #d1d5da;
            border-radius: 4px;
            font-family: inherit;
            font-size: 0.85rem;
            box-sizing: border-box;
            resize: vertical;
        }}
        .notes-input:focus, .custom-input:focus {{
            border-color: #0366d6;
            outline: none;
            box-shadow: 0 0 0 3px rgba(3,102,214,0.1);
        }}

        .status-badge {{
            display: inline-block;
            padding: 2px 6px;
            font-size: 0.75rem;
            border-radius: 3px;
            font-weight: bold;
        }}
        .bg-ac {{ background: #ddf4ff; color: #0969da; }}
        .bg-news {{ background: #dafbe1; color: #1a7f37; }}
        .bg-files {{ background: #fff8c5; color: #9a6700; }}
        .bg-iri {{ background: #ffebe9; color: #cf222e; }}
        .bg-custom {{ background: #f3e8ff; color: #6b21a8; }}
    </style>
</head>
<body>

<div class="header">
    <div>
        <h1>index.html Display Order & Link Audit Previewer</h1>
        <small id="summary-text" style="color: #d0e2ff;">Loading items...</small>
    </div>
    <button class="btn-export" onclick="exportAuditedCSV()">Export Audited CSV</button>
</div>

<div class="container" id="container"></div>

<script>
    const data = {rows_json};

    function extractCleanUrl(urlField) {{
        if (!urlField) return "#";
        const clean = urlField.replace(/""/g, '"').trim();
        const match = clean.match(/href=["']?([^"'\s>]+)["']?/i);
        if (match) return match[1].trim();
        return clean;
    }}

    function inferSourceType(url) {{
        if (!url || url === '#') return "dead_or_empty";
        if (url.includes('academiccommons.columbia.edu')) return "academic_commons";
        if (url.includes('news.climate.columbia.edu')) return "climate_news";
        if (url.includes('files/') || url.match(/\\.(pdf|html|doc|docx)$/i)) return "local_cache";
        if (url.includes('<a')) return "custom_html";
        if (url.includes('iri.columbia.edu')) return "iri_unresolved";
        return "original_external";
    }}

    function syncDOMToData() {{
        data.forEach((item, index) => {{
            const noteElem = document.getElementById(`notes_input_${{index}}`);
            if (noteElem) {{
                item.notes = noteElem.value;
            }}
            const customElem = document.getElementById(`custom_input_${{index}}`);
            if (customElem) {{
                item.custom_url = customElem.value;
            }}
        }});
    }}

    function replacePrimaryWith(index, choice) {{
        syncDOMToData();
        const item = data[index];
        const oldPrimary = item.url;

        if (choice === 'cached' && item.url_cached) {{
            item.url_secondary = oldPrimary;
            item.url = item.url_cached;
            item.url_source_type = 'local_cache';
        }} else if (choice === 'secondary' && item.url_secondary) {{
            item.url_secondary = oldPrimary;
            item.url = item.url_secondary;
            item.url_source_type = inferSourceType(item.url);
        }} else if (choice === 'custom') {{
            const customVal = (document.getElementById(`custom_input_${{index}}`).value || '').trim();
            if (customVal) {{
                item.url_secondary = oldPrimary;
                item.url = customVal;
                item.custom_url = customVal;
                item.url_source_type = customVal.includes('<a') ? 'custom_html' : inferSourceType(customVal);
            }}
        }}

        renderCards();
    }}

    function updateLivePreview(index) {{
        const boxElem = document.getElementById(`preview_box_${{index}}`);
        if (!boxElem) return;

        const item = data[index];
        const dataType = item.data_type || 'Entry';
        const cleanTargetUrl = extractCleanUrl(item.url);
        const dateStr = item.date_str || '';
        const titleStr = item.title || 'Untitled';

        let simulatedHtml = '';

        if (dataType === 'Publication') {{
            const authorsPub = (item.authors_pub || '').replace(/\\n/g, ' ');
            const publisher = (item.publisher || '').trim();
            const journal = (item.journal || '').trim();
            const volume = (item.volume || '').trim();
            const issue = (item.issue || '').trim();

            let metaParts = [];
            if (authorsPub) metaParts.push(`<span class="author-list">${{authorsPub}}</span>`);
            if (dateStr) metaParts.push(`<span class="date">${{dateStr}}</span>`);
            const metaStr = metaParts.join(', ');

            let detailsParts = [];
            if (publisher) detailsParts.push(publisher);
            if (journal) detailsParts.push(journal);
            if (volume) detailsParts.push(`Vol. ${{volume}}`);
            if (issue) detailsParts.push(`Issue ${{issue}}`);
            const detailsStr = detailsParts.join(', ');

            const urlContent = item.url.includes('<a') ? item.url : `<a href="${{cleanTargetUrl}}" target="_blank">${{titleStr}}</a>`;

            simulatedHtml = `
                <div class="entry-meta">${{metaStr}}.</div>
                <div class="entry-title">
                    ${{urlContent}}
                    <span class="type-label">[Publication]</span>
                </div>
                ${{detailsStr ? `<div class="entry-meta">${{detailsStr}}.</div>` : ''}}
            `;
        }} else if (dataType === 'Media Mention') {{
            const sourceMedia = (item.source_media || '').trim();
            simulatedHtml = `
                <span class="entry-title">
                    <a href="${{cleanTargetUrl}}" target="_blank">${{titleStr}}</a>
                    <span class="type-label">[Media Mention]</span>
                </span>
                <span class="entry-meta">
                    (<span class="date">${{dateStr}}</span>) in ${{sourceMedia}}
                </span>
            `;
        }} else if (dataType === 'News/Feature') {{
            const author = (item.author || '').trim();
            const excerpt = (item.excerpt || '').trim();
            
            let metaStr = (author && dateStr) ? `by ${{author}} on <span class="date">${{dateStr}}</span>` : '';
            if (!metaStr && dateStr) metaStr = `on <span class="date">${{dateStr}}</span>`;
            if (!metaStr && author) metaStr = `by ${{author}}`;

            simulatedHtml = `
                <div class="entry-title">
                    <a href="${{cleanTargetUrl}}" target="_blank">${{titleStr}}</a>
                    <span class="type-label">[News/Feature]</span>
                    <span class="entry-meta" style="display:inline;">${{metaStr}}</span>
                </div>
                ${{excerpt ? `<div class="entry-abstract">${{excerpt}}</div>` : ''}}
            `;
        }} else {{
            simulatedHtml = `<a href="${{cleanTargetUrl}}" target="_blank">${{titleStr}}</a>`;
        }}

        boxElem.innerHTML = simulatedHtml;
    }}

    function renderCards() {{
        const container = document.getElementById('container');
        container.innerHTML = '';

        let acCount = 0, newsCount = 0, filesCount = 0, iriCount = 0, customCount = 0;

        data.forEach((item, index) => {{
            const st = item.url_source_type || inferSourceType(item.url);
            if (st === 'academic_commons') acCount++;
            if (st === 'climate_news') newsCount++;
            if (st === 'local_cache') filesCount++;
            if (st === 'iri_unresolved') iriCount++;
            if (st === 'custom_html') customCount++;

            const card = document.createElement('div');
            card.className = 'card';

            const typeClass = st === 'academic_commons' ? 'bg-ac' :
                              st === 'climate_news' ? 'bg-news' :
                              st === 'local_cache' ? 'bg-files' :
                              st === 'custom_html' ? 'bg-custom' : 'bg-iri';

            const dataType = item.data_type || 'Entry';
            const cleanTargetUrl = extractCleanUrl(item.url);

            card.innerHTML = `
                <div class="card-header">
                    <span>index.html Row #${{item.display_order}} — ${{dataType}}</span>
                    <span class="status-badge ${{typeClass}}">${{st}}</span>
                </div>

                <!-- Simulated make_simplefihtml.py rendering -->
                <div class="site-preview-box" id="preview_box_${{index}}"></div>

                <!-- Link Audit Panel -->
                <div class="audit-panel">
                    <strong>Active Link & Backup Options:</strong>
                    <div class="link-grid">
                        
                        <!-- Option 1: Always Active Primary URL -->
                        <div class="link-option primary-active">
                            <span class="link-label">1. Active Primary URL (url):</span>
                            <span class="url-text">${{cleanTargetUrl}}</span>
                            ${{cleanTargetUrl !== '#' ? `<a href="${{cleanTargetUrl}}" target="_blank" class="btn-test">Test Active Link ↗</a>` : ''}}
                            <div style="margin-top:6px; font-size:0.75rem; color:#2ea44f; font-weight:bold;">
                                ✓ Currently Used in Column 1
                            </div>
                        </div>

                        <!-- Option 2: Local Cache Reference -->
                        <div class="link-option">
                            <span class="link-label">2. Local Cache (url_cached):</span>
                            <span class="url-text">${{item.url_cached || 'Not Cached'}}</span>
                            ${{item.url_cached ? `<a href="${{item.url_cached}}" target="_blank" class="btn-test">Test File ↗</a>` : ''}}
                            ${{item.url_cached ? `
                                <div class="action-dot">
                                    <label><input type="radio" name="action_${{index}}" onclick="replacePrimaryWith('${{index}}', 'cached')"> Replace Primary with this</label>
                                </div>
                            ` : ''}}
                        </div>

                        <!-- Option 3: Secondary Mirror Reference -->
                        <div class="link-option">
                            <span class="link-label">3. Secondary Mirror (url_secondary):</span>
                            <span class="url-text">${{item.url_secondary || 'None'}}</span>
                            ${{item.url_secondary ? `<a href="${{item.url_secondary}}" target="_blank" class="btn-test">Test Secondary ↗</a>` : ''}}
                            ${{item.url_secondary ? `
                                <div class="action-dot">
                                    <label><input type="radio" name="action_${{index}}" onclick="replacePrimaryWith('${{index}}', 'secondary')"> Replace Primary with this</label>
                                </div>
                            ` : ''}}
                        </div>

                        <!-- Option 4: Custom Input (Empty by Default) -->
                        <div class="link-option">
                            <span class="link-label">4. Enter Custom Link / HTML:</span>
                            <input type="text" id="custom_input_${{index}}" class="custom-input" 
                                   placeholder="Paste URL or <a href='...'>HTML..."
                                   value="${{item.custom_url || ''}}">
                            <div class="action-dot">
                                <label><input type="radio" name="action_${{index}}" onclick="replacePrimaryWith('${{index}}', 'custom')"> Replace Primary with Custom</label>
                            </div>
                        </div>

                    </div>

                    <!-- Notes Field -->
                    <div class="notes-box">
                        <label>Audit Notes / Verification Log:</label>
                        <textarea id="notes_input_${{index}}" class="notes-input" placeholder="Enter notes here...">${{item.notes || ''}}</textarea>
                    </div>
                </div>
            `;
            container.appendChild(card);
            updateLivePreview(index);
        }});

        document.getElementById('summary-text').innerText = 
            `Total Items: ${{data.length}} | Academic Commons: ${{acCount}} | Climate News: ${{newsCount}} | Local Cache: ${{filesCount}} | Custom HTML: ${{customCount}} | Unresolved IRI: ${{iriCount}}`;
    }}

    function exportAuditedCSV() {{
        if (!data.length) return;

        syncDOMToData();

        const internalKeys = new Set(['display_order', 'date_str']);
        const headers = Object.keys(data[0]).filter(k => !internalKeys.has(k));

        let csvContent = headers.join(',') + '\\n';

        data.forEach(row => {{
            let line = headers.map(header => {{
                let val = row[header] || '';
                val = val.toString().replace(/"/g, '""');
                if (val.includes(',') || val.includes('\\n') || val.includes('"')) {{
                    val = `"${{val}}"`;
                }}
                return val;
            }}).join(',');
            csvContent += line + '\\n';
        }});

        const blob = new Blob([csvContent], {{ type: 'text/csv;charset=utf-8;' }});
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.setAttribute('download', 'combined_data_audited.csv');
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }}

    renderCards();
</script>
</body>
</html>
"""

    with open(output_html, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"Preview HTML generated: '{output_html}'")

if __name__ == "__main__":
    # Automatically load your audited progress if it exists
    input_file = "combined_data_audited.csv" if os.path.exists("combined_data_audited.csv") else "combined_data_cached.csv"
    print(f"Loading data from: '{input_file}'")
    generate_preview_html(input_csv=input_file)
