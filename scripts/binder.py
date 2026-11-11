#!/usr/bin/env python3
"""
Article & Chapter Binder for EnglishCraft
Binds multiple scattered English articles (Markdown, TXT, HTML) into a beautifully formatted,
standard EPUB 3 electronic book or compiled reading digest.
Zero external dependencies, 100% compliant EPUB packaging.
"""

import os
import sys
import re
import uuid
import zipfile
import argparse
import html
from datetime import datetime, timezone

CSS_STYLES = """
@charset "utf-8";
body {
    font-family: Georgia, "Times New Roman", Garamond, serif;
    line-height: 1.65;
    margin: 5% 8%;
    color: #1a1a1a;
    background-color: #fafafa;
}
h1, h2, h3, h4, h5, h6 {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    color: #111;
    line-height: 1.25;
    margin-top: 1.8em;
    margin-bottom: 0.6em;
}
h1 {
    font-size: 1.8em;
    border-bottom: 2px solid #eaeaea;
    padding-bottom: 0.3em;
}
p {
    margin: 0.8em 0;
    text-align: justify;
    text-indent: 1.5em;
}
p:first-of-type {
    text-indent: 0;
}
blockquote {
    border-left: 4px solid #6366f1;
    margin: 1.2em 0;
    padding-left: 1em;
    color: #4b5563;
    font-style: italic;
}
code {
    font-family: Menlo, Monaco, Consolas, monospace;
    font-size: 0.9em;
    background-color: #f3f4f6;
    padding: 0.2em 0.4em;
    border-radius: 4px;
}
hr {
    border: none;
    border-top: 1px solid #e5e7eb;
    margin: 2em 0;
}
.chapter-meta {
    font-family: sans-serif;
    font-size: 0.85em;
    color: #6b7280;
    margin-bottom: 1.8em;
    border-bottom: 1px dashed #d1d5db;
    padding-bottom: 0.5em;
}
"""

def markdown_to_html_paragraphs(md_text):
    """Simple converter for standard Markdown into HTML paragraphs and headings."""
    lines = md_text.splitlines()
    html_parts = []
    in_paragraph = False
    para_lines = []

    def flush_para():
        nonlocal in_paragraph, para_lines
        if para_lines:
            content = " ".join(para_lines)
            # inline code
            content = re.sub(r"`([^`]+)`", r"<code>\1</code>", content)
            # bold
            content = re.sub(r"\*\*([^\*]+)\*\*", r"<strong>\1</strong>", content)
            # italic
            content = re.sub(r"\*([^\*]+)\*", r"<em>\1</em>", content)
            # link
            content = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', content)
            html_parts.append(f"<p>{content}</p>")
            para_lines = []
            in_paragraph = False

    for line in lines:
        s_line = line.strip()
        if not s_line:
            flush_para()
            continue

        if s_line.startswith("# "):
            flush_para()
            html_parts.append(f"<h1>{html.escape(s_line[2:].strip())}</h1>")
        elif s_line.startswith("## "):
            flush_para()
            html_parts.append(f"<h2>{html.escape(s_line[3:].strip())}</h2>")
        elif s_line.startswith("### "):
            flush_para()
            html_parts.append(f"<h3>{html.escape(s_line[4:].strip())}</h3>")
        elif s_line.startswith("> "):
            flush_para()
            html_parts.append(f"<blockquote>{html.escape(s_line[2:].strip())}</blockquote>")
        elif s_line.startswith("---") or s_line.startswith("***"):
            flush_para()
            html_parts.append("<hr />")
        else:
            para_lines.append(html.escape(s_line))

    flush_para()
    return "\n".join(html_parts)

def extract_title_and_body(file_path):
    """Extract article title and content from markdown or text file."""
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    # Look for first H1 title
    title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    if title_match:
        title = title_match.group(1).strip()
    else:
        # Fallback to filename
        base = os.path.splitext(os.path.basename(file_path))[0]
        title = base.replace("-", " ").replace("_", " ").title()

    return title, content

def create_epub(articles, output_path, book_title="English Reading Digest", author="EnglishCraft"):
    """
    Pack multiple articles into a compliant EPUB file.
    articles: list of dicts with {'title': str, 'content': str}
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    temp_zip = output_path + ".tmp"
    book_id = f"urn:uuid:{uuid.uuid4()}"
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    with zipfile.ZipFile(temp_zip, "w", compression=zipfile.ZIP_DEFLATED) as z:
        # 1. mimetype (MUST be first file, uncompressed!)
        z.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)

        # 2. META-INF/container.xml
        container_xml = """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
    <rootfiles>
        <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
    </rootfiles>
</container>"""
        z.writestr("META-INF/container.xml", container_xml)

        # 3. Stylesheet
        z.writestr("OEBPS/stylesheet.css", CSS_STYLES)

        # 4. Chapters
        manifest_items = [
            '<item id="css" href="stylesheet.css" media-type="text/css"/>',
            '<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>',
            '<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>',
        ]
        spine_items = []
        nav_points = []
        nav_toc_links = []

        for idx, art in enumerate(articles, 1):
            ch_id = f"chapter_{idx}"
            ch_filename = f"chapter_{idx}.xhtml"
            ch_title = art["title"]
            ch_body_html = markdown_to_html_paragraphs(art["content"])

            xhtml_content = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="en">
<head>
    <title>{html.escape(ch_title)}</title>
    <link rel="stylesheet" type="text/css" href="stylesheet.css" />
</head>
<body>
    <div class="chapter-meta">Chapter {idx} · {html.escape(book_title)}</div>
    <h1>{html.escape(ch_title)}</h1>
    <div class="chapter-body">
        {ch_body_html}
    </div>
</body>
</html>"""
            z.writestr(f"OEBPS/{ch_filename}", xhtml_content)

            manifest_items.append(f'<item id="{ch_id}" href="{ch_filename}" media-type="application/xhtml+xml"/>')
            spine_items.append(f'<itemref idref="{ch_id}"/>')
            nav_toc_links.append(f'<li><a href="{ch_filename}">{html.escape(ch_title)}</a></li>')
            nav_points.append(f"""
        <navPoint id="np_{idx}" playOrder="{idx}">
            <navLabel><text>{html.escape(ch_title)}</text></navLabel>
            <content src="{ch_filename}"/>
        </navPoint>""")

        # 5. OEBPS/nav.xhtml
        nav_xhtml = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="en">
<head>
    <title>Table of Contents</title>
    <link rel="stylesheet" type="text/css" href="stylesheet.css" />
</head>
<body>
    <nav epub:type="toc" id="toc">
        <h1>Table of Contents</h1>
        <ol>
            {"".join(nav_toc_links)}
        </ol>
    </nav>
</body>
</html>"""
        z.writestr("OEBPS/nav.xhtml", nav_xhtml)

        # 6. OEBPS/toc.ncx (EPUB 2 compatibility)
        toc_ncx = f"""<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
    <head>
        <meta name="dtb:uid" content="{book_id}"/>
        <meta name="dtb:depth" content="1"/>
        <meta name="dtb:totalPageCount" content="0"/>
        <meta name="dtb:maxPageNumber" content="0"/>
    </head>
    <docTitle><text>{html.escape(book_title)}</text></docTitle>
    <navMap>
        {"".join(nav_points)}
    </navMap>
</ncx>"""
        z.writestr("OEBPS/toc.ncx", toc_ncx)

        # 7. OEBPS/content.opf
        manifest_str = "\n        ".join(manifest_items)
        spine_str = "\n        ".join(spine_items)
        content_opf = f"""<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="BookID">
    <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
        <dc:title>{html.escape(book_title)}</dc:title>
        <dc:creator>{html.escape(author)}</dc:creator>
        <dc:identifier id="BookID">{book_id}</dc:identifier>
        <dc:language>en</dc:language>
        <meta property="dcterms:modified">{now_iso}</meta>
    </metadata>
    <manifest>
        {manifest_str}
    </manifest>
    <spine toc="ncx">
        {spine_str}
    </spine>
</package>"""
        z.writestr("OEBPS/content.opf", content_opf)

    if os.path.exists(output_path):
        os.remove(output_path)
    os.replace(temp_zip, output_path)
    return output_path

def main():
    parser = argparse.ArgumentParser(description="EnglishCraft Article Binder (Compile articles into EPUB)")
    parser.add_argument("inputs", nargs="+", help="Files or directory containing Markdown / Text articles")
    parser.add_argument("--title", "-t", default="English Reading Digest", help="Book title (default: 'English Reading Digest')")
    parser.add_argument("--author", "-a", default="EnglishCraft", help="Author name")
    parser.add_argument("--output", "-o", default="./downloads/digest.epub", help="Output EPUB path (default: ./downloads/digest.epub)")

    args = parser.parse_args()

    files = []
    for item in args.inputs:
        if os.path.isdir(item):
            for fname in sorted(os.listdir(item)):
                if fname.lower().endswith((".md", ".txt", ".markdown")):
                    files.append(os.path.join(item, fname))
        elif os.path.isfile(item):
            files.append(item)

    if not files:
        print(f"Error: No valid Markdown or Text files found in inputs.", file=sys.stderr)
        sys.exit(1)

    articles = []
    for f in files:
        title, content = extract_title_and_body(f)
        articles.append({"title": title, "content": content, "source": f})

    print(f"📚 Binding {len(articles)} articles into: '{args.title}' ...")
    for idx, a in enumerate(articles, 1):
        print(f"   [{idx}] {a['title']}")

    out_epub = create_epub(articles, args.output, book_title=args.title, author=args.author)
    size_kb = os.path.getsize(out_epub) / 1024
    print(f"\n✓ Successfully compiled EPUB: {out_epub} ({size_kb:.1f} KB)")
    print(f"  Ready for Kindle, Apple Books, or WordTower import!")

if __name__ == "__main__":
    main()
