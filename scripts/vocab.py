#!/usr/bin/env python3
"""
Vocabulary Analyzer & Extractor for EnglishCraft
Extracts, lemmatizes, ranks, and analyzes study-worthy English vocabulary from EPUB, Text, Markdown, or SRT files.
Filters out basic A1/A2 stop words, proper nouns, and URLs, providing frequency statistics and context sentences.
"""

import os
import sys
import re
import html
import json
import zipfile
import argparse
from collections import Counter

# Comprehensive set of function words and A1/A2 elementary English vocabulary to exclude from study lists
COMMON_STOPWORDS = {
    # Pronouns, determiners & articles
    "a", "an", "the", "this", "that", "these", "those", "my", "your", "his", "her", "its", "our", "their",
    "i", "you", "he", "she", "it", "we", "they", "me", "him", "us", "them", "myself", "yourself", "himself",
    "herself", "itself", "ourselves", "themselves", "who", "whom", "whose", "which", "what", "whatever",
    "whoever", "whichever", "someone", "somebody", "something", "anyone", "anybody", "anything", "nobody",
    "nothing", "everyone", "everybody", "everything", "each", "every", "either", "neither", "both", "another",
    # Prepositions, conjunctions & common adverbs
    "in", "on", "at", "by", "for", "with", "about", "against", "between", "into", "through", "during",
    "before", "after", "above", "below", "to", "from", "up", "down", "out", "off", "over", "under",
    "again", "further", "then", "once", "here", "there", "when", "where", "why", "how", "all", "any",
    "few", "more", "most", "other", "some", "such", "no", "nor", "not", "only", "own", "same", "so",
    "than", "too", "very", "can", "will", "just", "should", "now", "and", "but", "if", "or", "because",
    "as", "until", "while", "of", "also", "even", "though", "although", "whether", "within", "without",
    "along", "across", "behind", "beyond", "around", "near", "among", "since", "already", "almost",
    "always", "never", "often", "sometimes", "usually", "maybe", "perhaps", "quite", "rather", "enough",
    "together", "away", "back", "still", "yet", "ever", "soon", "today", "tomorrow", "yesterday",
    # Contraction stems & auxiliaries
    "s", "t", "don", "didn", "wasn", "weren", "isn", "aren", "doesn", "haven", "hadn", "won", "wouldn",
    "couldn", "shouldn", "mustn", "mightn", "needn", "be", "am", "is", "are", "was", "were", "been", "being",
    "have", "has", "had", "having", "do", "does", "did", "doing", "would", "could", "shall", "may", "might", "must",
    # Elementary A1/A2 verbs
    "say", "says", "said", "saying", "go", "goes", "went", "gone", "going", "come", "comes", "came", "coming",
    "get", "gets", "got", "gotten", "getting", "make", "makes", "made", "making", "take", "takes", "took",
    "taken", "taking", "see", "sees", "saw", "seen", "seeing", "know", "knows", "knew", "known", "knowing",
    "think", "thinks", "thought", "thinking", "look", "looks", "looked", "looking", "want", "wants", "wanted",
    "wanting", "give", "gives", "gave", "given", "giving", "use", "uses", "used", "using", "find", "finds",
    "found", "finding", "tell", "tells", "told", "telling", "ask", "asks", "asked", "asking", "work", "works",
    "worked", "working", "seem", "seems", "seemed", "seeming", "feel", "feels", "felt", "feeling", "try",
    "tries", "tried", "trying", "leave", "leaves", "left", "leaving", "call", "calls", "called", "calling",
    "keep", "kept", "let", "begin", "began", "begun", "help", "talk", "turn", "start", "show", "hear", "heard",
    "play", "run", "ran", "move", "like", "live", "believe", "hold", "held", "bring", "brought", "happen",
    "write", "wrote", "written", "sit", "sat", "stand", "stood", "lose", "lost", "pay", "paid", "meet", "met",
    "include", "continue", "set", "learn", "change", "lead", "led", "understand", "watch", "follow", "stop",
    "create", "speak", "spoke", "spoken", "read", "allow", "add", "spend", "spent", "grow", "grew", "grown",
    "open", "walk", "win", "won", "offer", "remember", "love", "consider", "appear", "buy", "bought", "wait",
    "serve", "die", "send", "sent", "expect", "build", "built", "stay", "fall", "fell", "fallen", "cut",
    "reach", "kill", "remain", "Pass", "sell", "sold", "decide", "return", "explain", "hope", "develop", "carry",
    "break", "broke", "broken", "receive", "agree", "support", "hit", "produce", "eat", "ate", "cover", "catch",
    "draw", "drew", "choose", "chose", "chosen", "wear", "wore", "drive", "drove", "driven",
    # Elementary A1/A2 adjectives & quantifiers
    "good", "better", "best", "bad", "worse", "worst", "new", "first", "last", "long", "great", "little",
    "less", "least", "much", "many", "old", "right", "big", "high", "different", "small", "large", "next",
    "early", "young", "important", "public", "able", "human", "local", "sure", "free", "true", "whole",
    "real", "easy", "hard", "full", "clear", "recent", "certain", "personal", "open", "red", "black", "white",
    "blue", "green", "short", "low", "single", "wrong", "fine", "ready", "simple", "half", "past", "close",
    "common", "poor", "natural", "significant", "similar", "hot", "cold", "dead", "central", "happy", "serious",
    # Elementary A1/A2 nouns & numbers & calendar
    "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve",
    "twenty", "thirty", "forty", "fifty", "hundred", "thousand", "million", "billion", "second", "third",
    "mr", "mrs", "ms", "dr", "st", "january", "february", "march", "april", "june", "july", "august",
    "september", "october", "november", "december", "monday", "tuesday", "wednesday", "thursday", "friday",
    "saturday", "sunday", "time", "year", "people", "way", "day", "man", "men", "woman", "women", "child",
    "children", "world", "life", "hand", "part", "place", "case", "week", "company", "system", "program",
    "question", "work", "government", "number", "night", "point", "home", "water", "room", "mother", "area",
    "money", "story", "fact", "month", "lot", "right", "study", "book", "eye", "job", "word", "business",
    "issue", "side", "kind", "head", "house", "service", "friend", "father", "power", "hour", "game", "line",
    "end", "member", "law", "car", "city", "community", "name", "president", "team", "minute", "idea", "kid",
    "body", "information", "back", "parent", "face", "others", "level", "office", "door", "health", "person",
    "art", "war", "history", "party", "result", "change", "morning", "reason", "research", "girl", "guy",
    "moment", "air", "teacher", "force", "education", "foot", "feet", "boy", "age", "policy", "process",
    "music", "market", "sense", "nation", "plan", "college", "interest", "death", "experience", "effect",
    "use", "class", "control", "care", "field", "development", "role", "effort", "rate", "heart", "drug",
    "show", "leader", "light", "voice", "wife", "police", "mind", "price", "report", "decision", "son",
    "view", "relationship", "town", "road", "arm", "table", "street", "model", "data", "paper", "form",
    "country", "state", "firm", "group", "bank", "tax", "oil", "food", "cost", "share", "stock", "trade",
    # Web / EPUB boilerplate tokens & remaining elementary tokens
    "http", "https", "www", "com", "org", "net", "html", "xhtml", "epub", "zlibrary", "download", "article",
    "page", "chapter", "section", "copyright", "edition", "author", "title", "imprint", "titlepage",
    "thing", "toward", "towards", "become", "became", "afternoon", "window", "front", "alone", "clock",
    "drink", "answer", "marry", "matter", "sound", "dress", "garden", "sport", "shake", "according",
    "earlier", "nearly", "largest", "quarter", "worth", "online",
}

IRREGULAR_LEMMAS = {
    "arose": "arise", "arisen": "arise", "awoke": "awake", "awoken": "awake",
    "bore": "bear", "borne": "bear", "beaten": "beat", "became": "become",
    "began": "begin", "begun": "begin", "bent": "bend", "bade": "bid", "bidden": "bid",
    "bound": "bind", "bit": "bite", "bitten": "bite", "bled": "bleed", "blew": "blow", "blown": "blow",
    "broke": "break", "broken": "break", "bred": "breed", "brought": "bring", "built": "build",
    "burnt": "burn", "bought": "buy", "caught": "catch", "chose": "choose", "chosen": "choose",
    "clung": "cling", "crept": "creep", "dealt": "deal", "dug": "dig", "dove": "dive",
    "drew": "draw", "drawn": "draw", "dreamt": "dream", "drank": "drink", "drunk": "drink",
    "drove": "drive", "driven": "drive", "dwelt": "dwell", "ate": "eat", "eaten": "eat",
    "fell": "fall", "fallen": "fall", "fed": "feed", "felt": "feel", "fought": "fight",
    "found": "find", "fled": "flee", "flung": "fling", "flew": "fly", "flown": "fly",
    "forbade": "forbid", "forbidden": "forbid", "forgot": "forget", "forgotten": "forget",
    "forgave": "forgive", "forgiven": "forgive", "froze": "freeze", "frozen": "freeze",
    "gave": "give", "given": "give", "ground": "grind", "grew": "grow", "grown": "grow",
    "hung": "hang", "heard": "hear", "hid": "hide", "hidden": "hide", "held": "hold",
    "kept": "keep", "knelt": "kneel", "knew": "know", "known": "know", "laid": "lay",
    "led": "lead", "leapt": "leap", "learnt": "learn", "left": "leave", "lent": "lend",
    "lain": "lie", "lit": "light", "lost": "lose", "made": "make", "meant": "mean",
    "met": "meet", "mistook": "mistake", "mistaken": "mistake", "overcame": "overcome",
    "overthrew": "overthrow", "overthrown": "overthrow", "paid": "pay", "pled": "plead",
    "proven": "prove", "rode": "ride", "ridden": "ride", "rang": "ring", "rung": "ring",
    "rose": "rise", "risen": "rise", "ran": "run", "saw": "see", "seen": "see",
    "sought": "seek", "sold": "sell", "sent": "send", "shook": "shake", "shaken": "shake",
    "shone": "shine", "shot": "shoot", "showed": "show", "shown": "show", "shrank": "shrink",
    "shrunk": "shrink", "sang": "sing", "sung": "sing", "sank": "sink", "sunk": "sink",
    "sat": "sit", "slew": "slay", "slain": "slay", "slept": "sleep", "slid": "slide",
    "slung": "sling", "smelt": "smell", "sowed": "sow", "sown": "sow", "spoke": "speak",
    "spoken": "speak", "sped": "speed", "spelt": "spell", "spent": "spend", "spilt": "spill",
    "spun": "spin", "spat": "spit", "spoilt": "spoil", "sprang": "spring", "sprung": "spring",
    "stood": "stand", "stole": "steal", "stolen": "steal", "stuck": "stick", "stung": "sting",
    "stank": "stink", "stunk": "stink", "strode": "stride", "struck": "strike", "strung": "string",
    "strove": "strive", "striven": "strive", "swore": "swear", "sworn": "swear", "swept": "sweep",
    "swollen": "swell", "swam": "swim", "swum": "swim", "swung": "swing", "took": "take",
    "taken": "take", "taught": "teach", "tore": "tear", "torn": "tear", "told": "tell",
    "thought": "think", "threw": "throw", "thrown": "throw", "trod": "tread", "trodden": "tread",
    "underwent": "undergo", "undergone": "undergo", "understood": "understand",
    "undertook": "undertake", "undertaken": "undertake", "woke": "wake", "woken": "wake",
    "wore": "wear", "worn": "wear", "wove": "weave", "woven": "weave", "wept": "weep",
    "won": "win", "wound": "wind", "withdrew": "withdraw", "withdrawn": "withdraw",
    "wrung": "wring", "wrote": "write", "written": "write",
    "analyses": "analysis", "crises": "crisis", "theses": "thesis", "hypotheses": "hypothesis",
    "phenomena": "phenomenon", "criteria": "criterion", "indices": "index", "appendices": "appendix",
}

_SYSTEM_DICT_CACHE = None

def get_system_dict():
    """Load lowercase words from OS dictionary (/usr/share/dict/words) if available."""
    global _SYSTEM_DICT_CACHE
    if _SYSTEM_DICT_CACHE is not None:
        return _SYSTEM_DICT_CACHE
    dict_paths = ["/usr/share/dict/words", "/usr/dict/words"]
    words = set()
    for p in dict_paths:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        w = line.strip()
                        if w and w[0].islower() and w.isalpha():
                            words.add(w.lower())
                break
            except Exception:
                pass
    _SYSTEM_DICT_CACHE = words
    return _SYSTEM_DICT_CACHE

def clean_html(raw_html):
    """Strip HTML tags while preserving paragraph breaks and removing boilerplate."""
    # Remove head, style, script blocks completely
    text = re.sub(r"<(head|style|script)[^>]*>.*?</\1>", " ", raw_html, flags=re.DOTALL | re.IGNORECASE)
    # Replace block closing tags and <br> with paragraph breaks
    text = re.sub(r"</(p|div|h[1-6]|li|blockquote|tr|section|article)>|<br\s*/?>", "\n\n", text, flags=re.IGNORECASE)
    # Remove remaining HTML tags
    text = re.sub(r"<[^>]+>", " ", text)
    # Unescape HTML entities (&amp;, &quot;, &mdash;, etc.)
    text = html.unescape(text)
    # Remove URLs
    text = re.sub(r"https?://\S+|www\.\S+", " ", text)
    # Remove common ebook download footers
    text = re.sub(r"This article was downloaded by[^\n]*", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"点击下载", " ", text)
    # Collapse horizontal whitespace while keeping paragraph breaks
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()

def extract_text_from_epub(epub_path):
    """Extract plain text chapters from an EPUB file."""
    if not zipfile.is_zipfile(epub_path):
        raise ValueError(f"Not a valid EPUB archive: {epub_path}")

    full_text = []
    with zipfile.ZipFile(epub_path, "r") as z:
        for name in z.namelist():
            lower_name = name.lower()
            if lower_name.endswith((".xhtml", ".html", ".htm")):
                if any(skip in lower_name for skip in ["toc.", "nav.", "cover.", "imprint.", "colophon.", "titlepage."]):
                    continue
                try:
                    content = z.read(name).decode("utf-8", errors="replace")
                    text = clean_html(content)
                    if len(text) > 120:
                        full_text.append(text)
                except Exception:
                    continue
    return "\n\n".join(full_text)

def extract_text_from_srt(srt_path):
    """Extract subtitles text from an SRT/VTT file, omitting timestamps and indices."""
    with open(srt_path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    clean_lines = []
    for line in lines:
        line_s = line.strip()
        if not line_s or line_s.isdigit() or "-->" in line_s or line_s.startswith("WEBVTT"):
            continue
        clean_lines.append(line_s)
    return " ".join(clean_lines)

def load_text(file_path):
    """Load text based on file format (.epub, .srt, .txt, .md, .html)."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".epub":
        return extract_text_from_epub(file_path)
    elif ext in [".srt", ".vtt"]:
        return extract_text_from_srt(file_path)
    elif ext in [".html", ".htm", ".xhtml"]:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            return clean_html(f.read())
    else:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            raw = f.read()
            raw = re.sub(r"https?://\S+|www\.\S+", " ", raw)
            return raw

def simple_lemmatize(word, valid_words=None):
    """Dictionary- and rule-backed lemmatization for English words."""
    w = word.lower()
    if len(w) <= 3:
        return w
    if w in IRREGULAR_LEMMAS:
        return IRREGULAR_LEMMAS[w]

    sys_dict = valid_words if valid_words is not None else get_system_dict()

    def is_valid(cand):
        if len(cand) < 3:
            return False
        if sys_dict:
            return cand in sys_dict
        return True

    # 1. -ies -> -y (e.g. policies -> policy, economies -> economy)
    if w.endswith("ies") and len(w) > 4:
        cand = w[:-3] + "y"
        if is_valid(cand):
            return cand

    # 2. -ied -> -y (e.g. applied -> apply, magnified -> magnify)
    if w.endswith("ied") and len(w) > 4:
        cand = w[:-3] + "y"
        if is_valid(cand):
            return cand

    # 3. -ves -> -f / -fe (e.g. wolves -> wolf, knives -> knife)
    if w.endswith("ves") and len(w) > 4:
        for suffix in ("f", "fe"):
            cand = w[:-3] + suffix
            if is_valid(cand):
                return cand

    # 4. -ing
    if w.endswith("ing") and len(w) > 5:
        base = w[:-3]
        # doubled consonant: running -> run, compelling -> compel
        if len(base) >= 3 and base[-1] == base[-2] and base[-1] not in "aeiouyssllffzz":
            cand = base[:-1]
            if is_valid(cand):
                return cand
        # silent e: undermining -> undermine, creating -> create
        if is_valid(base + "e") and (not is_valid(base) or base.endswith(("v", "c", "g", "z", "at", "it", "ut", "ot", "id", "ud", "od"))):
            return base + "e"
        if is_valid(base):
            return base
        if is_valid(base + "e"):
            return base + "e"

    # 5. -ed
    if w.endswith("ed") and not w.endswith("eed") and len(w) > 4:
        base = w[:-2]
        # doubled consonant: stopped -> stop, compelled -> compel
        if len(base) >= 3 and base[-1] == base[-2] and base[-1] not in "aeiouyssllffzz":
            cand = base[:-1]
            if is_valid(cand):
                return cand
        # silent e vs direct base: undermined -> undermine vs downloaded -> download
        if is_valid(base) and not base.endswith(("v", "c", "g", "z", "at", "it", "ut", "ot", "id", "ud")):
            return base
        if is_valid(base + "e"):
            return base + "e"
        if is_valid(base):
            return base

    # 6. -es
    if w.endswith("es") and len(w) > 4:
        if w.endswith(("ches", "shes", "xes", "zes", "sses")):
            cand = w[:-2]
            if is_valid(cand):
                return cand
        if is_valid(w[:-1]):
            return w[:-1]
        if is_valid(w[:-2]):
            return w[:-2]

    # 7. -s (plural / 3rd person singular, avoiding -ss, -us, -is, -os)
    if w.endswith("s") and not w.endswith(("ss", "us", "is", "os", "ics", "ous")) and len(w) > 3:
        cand = w[:-1]
        if is_valid(cand):
            return cand

    return w

def split_sentences(text):
    """Split text into clean sentences for context extraction."""
    flat = re.sub(r"\s+", " ", text)
    raw_sentences = re.split(r"(?<=[.!?])\s+", flat)
    clean_sents = []
    for s in raw_sentences:
        s = s.strip()
        # Filter out table-of-contents or header lists that have no verb/punctuation structure
        if 25 <= len(s) <= 300 and s[0].isupper() and any(ch in s for ch in ".,;—"):
            clean_sents.append(s)
    return clean_sents

def analyze_vocabulary(text, top_n=50, min_freq=2, min_length=4):
    """Analyze text and extract study-worthy English vocabulary."""
    sentences = split_sentences(text)
    sys_dict = get_system_dict()

    # Extract all alphabetic word tokens
    raw_tokens = re.findall(r"\b[A-Za-z]{2,}\b", text)
    total_tokens = len(raw_tokens)

    # Track capitalization to filter out proper nouns (names of people, places, brands)
    lower_counts = Counter()
    upper_counts = Counter()
    for tok in raw_tokens:
        low = tok.lower()
        if tok[0].islower():
            lower_counts[low] += 1
        else:
            upper_counts[low] += 1

    word_freq = Counter()
    lemma_to_forms = {}
    lemma_sentences = {}

    for token in raw_tokens:
        lower = token.lower()
        if len(lower) < min_length:
            continue
        if lower in COMMON_STOPWORDS:
            continue
        # Exclude proper nouns: words that almost never appear in lowercase in the text
        if lower_counts[lower] == 0 and upper_counts[lower] >= 1:
            continue
        if upper_counts[lower] > lower_counts[lower] * 3:
            continue

        lemma = simple_lemmatize(lower, sys_dict)
        if len(lemma) < min_length or lemma in COMMON_STOPWORDS:
            continue

        word_freq[lemma] += 1
        if lemma not in lemma_to_forms:
            lemma_to_forms[lemma] = set()
        lemma_to_forms[lemma].add(lower if token[0].isupper() else token)

    # Associate best context sentence for each target lemma
    for sent in sentences:
        words_in_sent = {simple_lemmatize(w.lower(), sys_dict) for w in re.findall(r"\b[A-Za-z]{4,}\b", sent)}
        for w in words_in_sent:
            if w in word_freq and w not in lemma_sentences:
                lemma_sentences[w] = sent

    # Filter and sort by frequency (then word length as tie-breaker for richer vocabulary)
    filtered = [(w, c) for w, c in word_freq.items() if c >= min_freq]
    filtered.sort(key=lambda x: (x[1], len(x[0])), reverse=True)

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
    md.append("### 📊 English Vocabulary Statistics")
    md.append(f"- **Total Words (Tokens)**: {stats['total_words']:,}")
    md.append(f"- **Key Target Words (Filtered)**: {stats['unique_target_words']:,}")
    md.append(f"- **Lexical Diversity**: {stats['lexical_richness'] * 100:.2f}%\n")
    md.append("| # | Word | Freq | Sample Context Sentence |")
    md.append("|---|---|---|---|")
    for idx, item in enumerate(stats["vocabulary"], 1):
        ctx = item["context"].replace("|", "\\|")
        if len(ctx) > 95:
            ctx = ctx[:95] + "..."
        md.append(f"| {idx} | **{item['word']}** | {item['count']} | {ctx} |")
    return "\n".join(md)

def main():
    parser = argparse.ArgumentParser(description="EnglishCraft Vocabulary Extractor & Analyzer")
    parser.add_argument("file", help="Path to EPUB, Markdown, TXT, HTML, or SRT file")
    parser.add_argument("--top", "-n", type=int, default=30, help="Number of top words to extract (default: 30)")
    parser.add_argument("--min-freq", "-m", type=int, default=2, help="Minimum occurrences (default: 2)")
    parser.add_argument("--min-length", "-l", type=int, default=5, help="Minimum word length (default: 5)")
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
