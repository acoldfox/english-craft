#!/usr/bin/env python3
"""
Vocabulary Analyzer & Extractor for EnglishCraft
Extracts, ranks, and analyzes English vocabulary from EPUB, Text, Markdown, or SRT files.
Filters out basic stop words, provides frequency statistics and context sentences.
"""

import os
import sys
import re
import json
import zipfile
import argparse
from collections import Counter
import xml.etree.ElementTree as ET

# Curated list of high-frequency English functional words and elementary vocabulary
COMMON_STOPWORDS = {
    # Pronouns & determiners
    "a", "an", "the", "this", "that", "these", "those", "my", "your", "his", "her", "its", "our", "their",
    "i", "you", "he", "she", "it", "we", "they", "me", "him", "her", "us", "them", "who", "whom", "whose",
    "which", "what", "whatever", "whoever", "whichever", "someone", "somebody", "something", "anyone",
    "anybody", "anything", "no one", "nobody", "nothing", "everyone", "everybody", "everything",
    # Prepositions & conjunctions
    "in", "on", "at", "by", "for", "with", "about", "against", "between", "into", "through", "during",
    "before", "after", "above", "below", "to", "from", "up", "down", "in", "out", "on", "off", "over",
    "under", "again", "further", "then", "once", "here", "there", "when", "where", "why", "how", "all",
    "any", "both", "each", "few", "more", "most", "other", "some", "such", "no", "nor", "not", "only",
    "own", "same", "so", "than", "too", "very", "s", "t", "can", "will", "just", "don", "should", "now",
    "and", "but", "if", "or", "because", "as", "until", "while", "of", "also", "even", "though", "although",
    "didn", "wasn", "weren", "isn", "aren", "doesn", "haven", "hadn", "won", "wouldn", "couldn", "shouldn",
    # Basic auxiliary & elementary verbs
    "be", "am", "is", "are", "was", "were", "been", "being", "have", "has", "had", "having",
    "do", "does", "did", "doing", "would", "could", "should", "shall", "may", "might", "must",
    "say", "says", "said", "saying", "go", "goes", "went", "gone", "going", "come", "comes", "came", "coming",
    "get", "gets", "got", "gotten", "getting", "make", "makes", "made", "making", "take", "takes", "took",
    "taken", "taking", "see", "sees", "saw", "seen", "seeing", "know", "knows", "knew", "known", "knowing",
    "think", "thinks", "thought", "thinking", "look", "looks", "looked", "looking", "want", "wants", "wanted",
    "wanting", "give", "gives", "gave", "given", "giving", "use", "uses", "used", "using", "find", "finds",
    "found", "finding", "tell", "tells", "told", "telling", "ask", "asks", "asked", "asking", "work", "works",
    "worked", "working", "seem", "seems", "seemed", "seeming", "feel", "feels", "felt", "feeling", "try",
    "tries", "tried", "trying", "leave", "leaves", "left", "leaving", "call", "calls", "called", "calling",
    "good", "new", "first", "last", "long", "great", "little", "own", "other", "old", "right", "big", "high",
    "different", "small", "large", "next", "early", "young", "important", "few", "public", "bad", "same", "able",
    "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "hundred", "thousand", "million",
    "mr", "mrs", "ms", "dr", "said", "like", "well", "back", "still", "way", "man", "time", "day", "year", "people",
}

def clean_html(raw_html):
    """Strip HTML tags from text."""
    cleanr = re.compile(r"<[^>]+>")
    text = cleanr.sub(" ", raw_html)
    return re.sub(r"\s+", " ", text).strip()

def extract_text_from_epub(epub_path):
    """Extract plain text chapters from an EPUB file."""
    if not zipfile.is_zipfile(epub_path):
        raise ValueError(f"Not a valid EPUB archive: {epub_path}")

    full_text = []
    with zipfile.ZipFile(epub_path, "r") as z:
        for name in z.namelist():
            if name.lower().endswith((".xhtml", ".html", ".htm")):
                try:
                    content = z.read(name).decode("utf-8", errors="replace")
                    text = clean_html(content)
                    if len(text) > 100:  # Skip tiny cover/nav files
                        full_text.append(text)
                except Exception:
                    continue
    return "\n\n".join(full_text)

def extract_text_from_srt(srt_path):
    """Extract subtitles text from an SRT file, omitting timestamps and indices."""
    with open(srt_path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    clean_lines = []
    for line in lines:
        line_s = line.strip()
        if not line_s or line_s.isdigit() or "-->" in line_s:
            continue
        clean_lines.append(line_s)
    return " ".join(clean_lines)

def load_text(file_path):
    """Load text based on file format (.epub, .srt, .txt, .md)."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".epub":
        return extract_text_from_epub(file_path)
    elif ext in [".srt", ".vtt"]:
        return extract_text_from_srt(file_path)
    else:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()

def simple_lemmatize(word):
    """Basic rule-based lemmatization for English nouns and verbs."""
    w = word.lower()
    if len(w) <= 3:
        return w
    # Noun plurals / 3rd person singular
    if w.endswith("ies") and len(w) > 4:
        return w[:-3] + "y"
    if w.endswith("es") and len(w) > 4 and (w[-3] in "shxz" or w[-4:-2] in ["ch"]):
        return w[:-2]
    # Verb past/participle
    if w.endswith("ied") and len(w) > 4:
        return w[:-3] + "y"
    if w.endswith("ed") and len(w) > 4:
        if w[-3] == w[-4] and w[-3] not in "aeiouy": # e.g. stopped -> stop
            return w[:-3]
        return w[:-2] if w.endswith("eed") else (w[:-1] if w.endswith("ed") else w)
    # Continuous -ing
    if w.endswith("ing") and len(w) > 5:
        if w[-4] == w[-5] and w[-4] not in "aeiouy": # e.g. running -> run
            return w[:-4]
        return w[:-3]
    # Simple -s
    if w.endswith("s") and not w.endswith("ss") and len(w) > 3:
        return w[:-1]
    return w

def split_sentences(text):
    """Split text into sentences for context extraction."""
    raw_sentences = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in raw_sentences if len(s.strip()) > 10]

def analyze_vocabulary(text, top_n=50, min_freq=2, min_length=4):
    """Analyze text and extract key vocabulary."""
    sentences = split_sentences(text)
    
    # Extract all english word tokens
    raw_tokens = re.findall(r"\b[A-Za-z]+(?:'[A-Za-z]+)?\b", text)
    total_tokens = len(raw_tokens)
    
    word_freq = Counter()
    lemma_to_forms = {}
    lemma_sentences = {}

    for token in raw_tokens:
        lower = token.lower()
        if len(lower) < min_length:
            continue
        lemma = simple_lemmatize(lower)
        if lemma in COMMON_STOPWORDS or lower in COMMON_STOPWORDS:
            continue
        
        word_freq[lemma] += 1
        if lemma not in lemma_to_forms:
            lemma_to_forms[lemma] = set()
        lemma_to_forms[lemma].add(token)

    # Associate sample context sentence for each word
    for sent in sentences:
        words_in_sent = {simple_lemmatize(w.lower()) for w in re.findall(r"\b[A-Za-z]+\b", sent)}
        for w in words_in_sent:
            if w in word_freq and w not in lemma_sentences:
                lemma_sentences[w] = sent

    # Filter and sort
    filtered = [(w, c) for w, c in word_freq.items() if c >= min_freq]
    filtered.sort(key=lambda x: x[1], reverse=True)

    results = []
    for w, count in filtered[:top_n]:
        results.append({
            "word": w,
            "count": count,
            "forms": sorted(list(lemma_to_forms.get(w, [w]))),
            "context": lemma_sentences.get(w, ""),
        })

    unique_filtered = len(word_freq)
    stats = {
        "total_words": total_tokens,
        "unique_target_words": unique_filtered,
        "lexical_richness": round(unique_filtered / total_tokens, 4) if total_tokens else 0,
        "vocabulary": results,
    }
    return stats

def format_output(stats, output_format="table"):
    if output_format == "json":
        return json.dumps(stats, indent=2, ensure_ascii=False)
    
    if output_format == "csv":
        lines = ["Word,Count,Forms,Context Sentence"]
        for item in stats["vocabulary"]:
            forms_str = ";".join(item["forms"])
            ctx = item["context"].replace('"', '""')
            lines.append(f'"{item["word"]}",{item["count"]},"{forms_str}","{ctx}"')
        return "\n".join(lines)

    # Markdown / Table format
    md = []
    md.append(f"### 📊 English Vocabulary Statistics")
    md.append(f"- **Total Words (Tokens)**: {stats['total_words']:,}")
    md.append(f"- **Key Target Words (Filtered)**: {stats['unique_target_words']:,}")
    md.append(f"- **Lexical Diversity**: {stats['lexical_richness'] * 100:.2f}%\n")
    md.append("| # | Word | Freq | Sample Context Sentence |")
    md.append("|---|---|---|---|")
    for idx, item in enumerate(stats["vocabulary"], 1):
        ctx = item["context"].replace("|", "\\|")
        if len(ctx) > 85:
            ctx = ctx[:85] + "..."
        md.append(f"| {idx} | **{item['word']}** | {item['count']} | {ctx} |")
    return "\n".join(md)

def main():
    parser = argparse.ArgumentParser(description="EnglishCraft Vocabulary Extractor & Analyzer")
    parser.add_argument("file", help="Path to EPUB, Markdown, TXT, or SRT file")
    parser.add_argument("--top", "-n", type=int, default=30, help="Number of top words to extract (default: 30)")
    parser.add_argument("--min-freq", "-m", type=int, default=2, help="Minimum occurrences (default: 2)")
    parser.add_argument("--min-length", "-l", type=int, default=4, help="Minimum word length (default: 4)")
    parser.add_argument("--format", "-f", choices=["table", "markdown", "csv", "json"], default="table", help="Output format")
    parser.add_argument("--output", "-o", help="Output file path (default: stdout)")

    args = parser.parse_args()

    if not os.path.exists(args.file):
        print(f"Error: File not found: {args.file}", file=sys.stderr)
        sys.exit(1)

    try:
        text = load_text(args.file)
    except Exception as e:
        print(f"Error reading file {args.file}: {e}", file=sys.stderr)
        sys.exit(1)

    stats = analyze_vocabulary(text, top_n=args.top, min_freq=args.min_freq, min_length=args.min_length)
    output_str = format_output(stats, output_format=args.format)

    if args.output:
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output_str)
        print(f"✓ Vocabulary extracted and saved to: {args.output}")
    else:
        print(output_str)

if __name__ == "__main__":
    main()
