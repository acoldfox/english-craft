#!/usr/bin/env python3
"""
Print & Reading Layout Generator for EnglishCraft
Generates elegant, print-ready A4 HTML/PDF reading sheets with:
1. Two-column layout: Main reading text on the left, vocabulary & handwritten note space on the right margin.
2. End-of-article Vocabulary Checklist with checkboxes for spaced repetition.
3. Standard @page A4 CSS rules, ready for 1-click browser printing or PDF saving.
"""

import os
import sys
import re
import html
import argparse
from vocab import load_text, analyze_vocabulary, clean_html, split_sentences

A4_PRINT_CSS = """
@charset "utf-8";

@page {
    size: A4 portrait;
    margin: 15mm 12mm 15mm 12mm;
    @bottom-center {
        content: counter(page) " / " counter(pages);
        font-family: sans-serif;
        font-size: 8pt;
        color: #888;
    }
}

* {
    box-sizing: border-box;
}

body {
    font-family: "Garamond", "Georgia", "Times New Roman", serif;
    font-size: 10.5pt;
    line-height: 1.6;
    color: #111;
    background-color: #fff;
    margin: 0;
    padding: 0;
}

.document-header {
    border-bottom: 2pt solid #222;
    padding-bottom: 6pt;
    margin-bottom: 16pt;
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
}

.document-title {
    font-size: 18pt;
    font-weight: bold;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    color: #111;
    margin: 0;
    line-height: 1.2;
}

.document-meta {
    font-size: 8.5pt;
    font-family: sans-serif;
    color: #666;
    text-align: right;
    white-space: nowrap;
}

.reading-row {
    display: flex;
    gap: 14pt;
    margin-bottom: 12pt;
    page-break-inside: avoid;
}

.text-col {
    flex: 1;
    text-align: justify;
    text-justify: inter-word;
}

.text-col p {
    margin: 0 0 6pt 0;
    text-indent: 1.5em;
}

.text-col p:first-child {
    text-indent: 0;
}

.margin-col {
    width: 140pt;
    flex-shrink: 0;
    border-left: 1pt dashed #cbd5e1;
    padding-left: 8pt;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    font-size: 8pt;
    color: #475569;
}

.margin-vocab-item {
    background: #f8fafc;
    border-radius: 3pt;
    padding: 3pt 5pt;
    margin-bottom: 5pt;
    border: 0.5pt solid #e2e8f0;
}

.margin-vocab-word {
    font-weight: bold;
    color: #0f172a;
}

.margin-note-line {
    border-bottom: 0.5pt dotted #94a3b8;
    height: 14pt;
    margin-top: 3pt;
}

.vocab-checklist-section {
    page-break-before: always;
    margin-top: 20pt;
    border-top: 2pt solid #0f172a;
    padding-top: 12pt;
}

.vocab-checklist-title {
    font-size: 14pt;
    font-family: sans-serif;
    font-weight: bold;
    color: #0f172a;
    margin-bottom: 10pt;
}

.vocab-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 8pt 16pt;
}

.vocab-card {
    border: 0.5pt solid #cbd5e1;
    border-radius: 4pt;
    padding: 6pt 8pt;
    background: #fff;
    page-break-inside: avoid;
}

.vocab-card-header {
    display: flex;
    justify-content: space-between;
    font-family: sans-serif;
    font-size: 9pt;
    margin-bottom: 4pt;
}

.vocab-card-word {
    font-weight: bold;
    color: #1e293b;
    font-size: 10pt;
}

.vocab-card-freq {
    color: #64748b;
    font-size: 8pt;
}

.vocab-card-ctx {
    font-size: 8.5pt;
    font-style: italic;
    color: #475569;
    line-height: 1.35;
}

.vocab-card-notes {
    border-bottom: 0.5pt dotted #cbd5e1;
    margin-top: 5pt;
    height: 14pt;
}

@media screen {
    body {
        max-width: 800px;
        margin: 20px auto;
        padding: 30px;
        background-color: #f1f5f9;
    }
    .page-container {
        background: #fff;
        padding: 40px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.08);
        border-radius: 6px;
    }
    .print-tip {
        background: #e0f2fe;
        color: #0369a1;
        padding: 10px 14px;
        border-radius: 6px;
        margin-bottom: 20px;
        font-family: sans-serif;
        font-size: 13px;
    }
}
@media print {
    .print-tip {
        display: none;
    }
    body {
        background: none;
    }
}
"""

def generate_print_html(input_file, title=None, top_vocab=40):
    raw_text = load_text(input_file)
    clean_text = clean_html(raw_text) if "<" in raw_text and ">" in raw_text else raw_text
    
    # Extract title
    doc_title = title
    if not doc_title:
        title_match = re.search(r"^#\s+(.+)$", raw_text, re.MULTILINE)
        if title_match:
            doc_title = title_match.group(1).strip()
        else:
            doc_title = os.path.splitext(os.path.basename(input_file))[0].replace("-", " ").replace("_", " ").title()

    # Vocab stats
    stats = analyze_vocabulary(clean_text, top_n=top_vocab, min_freq=1)
    target_vocab_map = {item["word"].lower(): item for item in stats["vocabulary"]}

    # Break into paragraphs
    raw_paragraphs = [p.strip() for p in clean_text.split("\n\n") if len(p.strip()) > 30]
    if len(raw_paragraphs) < 3:
        raw_paragraphs = [p.strip() for p in clean_text.split("\n") if len(p.strip()) > 30]

    rows_html = []
    seen_words = set()

    for p in raw_paragraphs:
        words_in_p = {w.lower() for w in re.findall(r"\b[A-Za-z]+\b", p)}
        matched_vocab = []
        for w in words_in_p:
            if w in target_vocab_map and w not in seen_words:
                matched_vocab.append(target_vocab_map[w])
                seen_words.add(w)

        # Margin content
        margin_items = []
        for v in matched_vocab[:3]:  # at most 3 words per paragraph margin
            margin_items.append(f"""
                <div class="margin-vocab-item">
                    <span class="margin-vocab-word">{html.escape(v['word'])}</span>
                    <div class="margin-note-line"></div>
                </div>""")
        if not margin_items:
            margin_items.append('<div class="margin-note-line"></div><div class="margin-note-line"></div>')

        p_escaped = html.escape(p)
        rows_html.append(f"""
        <div class="reading-row">
            <div class="text-col">
                <p>{p_escaped}</p>
            </div>
            <div class="margin-col">
                {''.join(margin_items)}
            </div>
        </div>""")

    # Vocabulary Checklist Section
    vocab_cards = []
    for item in stats["vocabulary"][:30]:
        ctx_snippet = html.escape(item["context"][:100] + ("..." if len(item["context"]) > 100 else "")) if item["context"] else ""
        vocab_cards.append(f"""
        <div class="vocab-card">
            <div class="vocab-card-header">
                <span class="vocab-card-word">☐ {html.escape(item['word'])}</span>
                <span class="vocab-card-freq">Freq: {item['count']}</span>
            </div>
            {f'<div class="vocab-card-ctx">“{ctx_snippet}”</div>' if ctx_snippet else ''}
            <div class="vocab-card-notes"></div>
        </div>""")

    full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>{html.escape(doc_title)} - EnglishCraft Print Sheet</title>
    <style>{A4_PRINT_CSS}</style>
</head>
<body>
    <div class="print-tip">
        💡 <strong>EnglishCraft A4 Print Sheet</strong>: Press <code>Cmd + P</code> (or <code>Ctrl + P</code>) to print or save as PDF. 
        Margin notes and the end-of-text vocabulary checklist are pre-formatted for intensive paper reading.
    </div>
    <div class="page-container">
        <div class="document-header">
            <div>
                <h1 class="document-title">{html.escape(doc_title)}</h1>
            </div>
            <div class="document-meta">
                Total Words: {stats['total_words']:,} | Target Words: {len(target_vocab_map)}<br>
                Curated by EnglishCraft
            </div>
        </div>

        <div class="reading-body">
            {''.join(rows_html)}
        </div>

        <div class="vocab-checklist-section">
            <div class="vocab-checklist-title">📝 Intensive Reading Vocabulary Checklist</div>
            <div class="vocab-grid">
                {''.join(vocab_cards)}
            </div>
        </div>
    </div>
</body>
</html>"""
    return full_html

def main():
    parser = argparse.ArgumentParser(description="EnglishCraft A4 Print-Friendly Reading Sheet Generator")
    parser.add_argument("input", help="Path to English EPUB, Markdown, TXT, or SRT file")
    parser.add_argument("--title", "-t", help="Custom document title")
    parser.add_argument("--top-vocab", "-n", type=int, default=40, help="Number of target vocabulary items to track (default: 40)")
    parser.add_argument("--output", "-o", default="./downloads/reading_sheet.html", help="Output HTML file path (default: ./downloads/reading_sheet.html)")

    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: File not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    print(f"🖨️  Generating A4 print-ready reading layout for: '{args.input}' ...")
    html_content = generate_print_html(args.input, title=args.title, top_vocab=args.top_vocab)

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(html_content)

    size_kb = os.path.getsize(args.output) / 1024
    print(f"✓ Print-ready reading sheet created: {args.output} ({size_kb:.1f} KB)")
    print(f"  Open in browser and press Cmd+P to print or save as A4 PDF with margin notes & vocab checklist!")

if __name__ == "__main__":
    main()
