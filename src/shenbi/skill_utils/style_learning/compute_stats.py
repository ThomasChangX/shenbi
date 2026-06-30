#!/usr/bin/env python3
"""compute_stats.py — Deterministic style statistics for shenbi-style-learning.

Reads chapter files and outputs JSON statistics. Zero LLM, zero randomness.
Usage: python3 compute_stats.py <chapter_dir_or_files...> [--output stats.json]
"""

import json
import re
import sys
from collections import Counter
from pathlib import Path
from shenbi.safe_write import safe_write
from typing import Any

SENT_ENDS = re.compile(r"[。！？；\n]")
PUNCT_MAP = {
    "句号": "。",
    "逗号": "，",
    "感叹号": "！",
    "问号": "？",
    "破折号": "——",
    "省略号": "……",
    "顿号": "、",
    "分号": "；",
    "冒号": "：",
    "引号": "\"\"''「」『』",
}
CONNECTIVES = {
    "时间": ["然后", "接着", "之后", "忽然", "突然", "此时", "随后", "立刻", "马上"],
    "转折": ["但是", "然而", "不过", "可是", "却", "但", "只是", "偏偏"],
    "因果": ["因为", "所以", "因此", "既然", "于是", "从而", "因而"],
    "顺序": ["首先", "其次", "最后", "终于", "接着", "然后", "接下来"],
    "让步": ["虽然", "尽管", "固然", "即便", "哪怕"],
    "条件": ["如果", "只要", "只有", "除非", "否则"],
}
RHETORICAL = {
    "排比": re.compile(r"([^。！？\n]{8,})([。！？])\1([^。！？\n]{8,})\2"),
    "设问": re.compile(r"(为何|为什么|怎么|怎样|如何).*[？]"),
    "反问": re.compile(r"(难道|岂|怎能|怎会|莫非).*[？]"),
}
AI_MARKERS = [
    "似乎",
    "仿佛",
    "不由得",
    "缓缓地",
    "微微",
    "不禁",
    "淡淡的",
    "嘴角微扬",
    "瞳孔微缩",
    "不是…而是",
]
TRANSITION_WORDS = ["然而", "不过", "此时", "突然", "终于", "于是", "与此同时", "与此同时"]


def segment_sentences(text: str) -> list[tuple[str, int]]:
    """Segment Chinese text into sentences. Returns list of (sentence_text, char_count)."""
    sentences: list[tuple[str, int]] = []
    current: list[str] = []
    for ch in text:
        current.append(ch)
        if ch in "。！？\n":
            sent = "".join(current).strip()
            if sent:
                char_count = len(sent.replace("\n", "").replace(" ", ""))
                if char_count > 0:
                    sentences.append((sent, char_count))
            current = []
    if current:
        sent = "".join(current).strip()
        char_count = len(sent.replace("\n", "").replace(" ", ""))
        if char_count > 0:
            sentences.append((sent, char_count))
    return sentences


def segment_paragraphs(text: str) -> list[dict[str, Any]]:
    """Segment text into paragraphs by double-newline or single-newline boundaries."""
    raw = re.split(r"\n\s*\n", text)
    paragraphs: list[dict[str, Any]] = []
    for p in raw:
        p = p.strip()
        if not p:
            continue
        char_count = len(p.replace("\n", "").replace(" ", ""))
        sent_count = len([s for s in SENT_ENDS.finditer(p)])
        if char_count > 0:
            paragraphs.append({"text": p, "chars": char_count, "sentences": max(sent_count, 1)})
    return paragraphs


def compute_percentiles(values: list[int]) -> dict[str, int]:
    """Compute P25, P50, P75, P95 from a sorted list."""
    if not values:
        return {"P25": 0, "P50": 0, "P75": 0, "P95": 0}
    n = len(values)
    return {
        "P25": values[max(0, int(n * 0.25) - 1)],
        # P50 必须与 compute_sentence_stats 的 median（lengths[n//2]）同源；
        # 旧式 int(n*0.50)-1 在 n≥2 时与 median 偏移 → P50≠median（spec 支柱五修复）。
        "P50": values[n // 2],
        "P75": values[max(0, int(n * 0.75) - 1)],
        "P95": values[max(0, int(n * 0.95) - 1)],
    }


def compute_sentence_stats(sentences: list[tuple[str, int]]) -> dict[str, Any]:
    """Compute sentence length statistics."""
    if not sentences:
        return {}
    lengths = sorted([s[1] for s in sentences])
    n = len(lengths)
    mean = sum(lengths) / n
    median = lengths[n // 2]
    variance = sum((x - mean) ** 2 for x in lengths) / n
    std = variance**0.5
    cv = std / mean if mean > 0 else 0
    percentiles = compute_percentiles(lengths)
    hist = {"1-10": 0, "11-20": 0, "21-30": 0, "31-50": 0, "51-80": 0, "81+": 0}
    for l in lengths:
        if l <= 10:
            hist["1-10"] += 1
        elif l <= 20:
            hist["11-20"] += 1
        elif l <= 30:
            hist["21-30"] += 1
        elif l <= 50:
            hist["31-50"] += 1
        elif l <= 80:
            hist["51-80"] += 1
        else:
            hist["81+"] += 1
    return {
        "count": n,
        "mean": round(mean, 1),
        "median": median,
        "std": round(std, 1),
        "cv": round(cv, 3),
        **percentiles,
        "histogram": hist,
    }


def compute_paragraph_stats(paragraphs: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute paragraph length statistics."""
    if not paragraphs:
        return {}
    sent_lens = sorted([p["sentences"] for p in paragraphs])
    char_lens = sorted([p["chars"] for p in paragraphs])
    n = len(paragraphs)
    sent_mean = sum(sent_lens) / n
    char_mean = sum(char_lens) / n
    sent_variance = sum((x - sent_mean) ** 2 for x in sent_lens) / n
    char_variance = sum((x - char_mean) ** 2 for x in char_lens) / n
    return {
        "count": n,
        "sentences_per_paragraph": {
            "mean": round(sent_mean, 1),
            "std": round(sent_variance**0.5, 1),
        },
        "chars_per_paragraph": {
            "mean": round(char_mean, 1),
            "std": round(char_variance**0.5, 1),
        },
    }


def compute_ttr(text: str) -> dict[str, Any]:
    """Compute Type-Token Ratio at character level for Chinese text."""
    chars = [c for c in text if c.strip() and c not in "。，！？；：''「」『』（）——……、\n"]
    if not chars:
        return {"global_ttr": 0, "sliding_ttr_mean": 0, "sliding_ttr_std": 0}
    unique = len(set(chars))
    total = len(chars)
    global_ttr = round(unique / total, 4) if total > 0 else 0
    window = 1000
    step = 500
    window_ttrs: list[float] = []
    for start in range(0, total - window + 1, step):
        w_chars = chars[start : start + window]
        w_unique = len(set(w_chars))
        w_ttr = w_unique / window if window > 0 else 0
        window_ttrs.append(round(w_ttr, 4))
    if window_ttrs:
        mean_ttr = sum(window_ttrs) / len(window_ttrs)
        var_ttr = sum((x - mean_ttr) ** 2 for x in window_ttrs) / len(window_ttrs)
        sliding = {"mean": round(mean_ttr, 4), "std": round(var_ttr**0.5, 4)}
    else:
        sliding = {"mean": global_ttr, "std": 0}
    function_chars = set(
        "的了是就在也和着地得过都会可以能没被把让对从到向与而因所以然则之其以此或但若虽非更很太只个些还又要去来说"
    )
    content_chars = [c for c in chars if c not in function_chars]
    content_ttr = round(len(set(content_chars)) / len(content_chars), 4) if content_chars else 0
    return {
        "global_ttr": global_ttr,
        "content_ttr": content_ttr,
        "sliding_ttr_mean": sliding["mean"],
        "sliding_ttr_std": sliding["std"],
        "total_chars": total,
    }


def compute_ngrams(
    text: str, n: int = 2, min_count: int = 5, max_results: int = 30
) -> list[tuple[str, int]]:
    """Extract character-level n-grams from Chinese text."""
    cleaned = [c for c in text if c.strip()]
    ngrams: Counter[str] = Counter()
    for i in range(len(cleaned) - n + 1):
        gram = "".join(cleaned[i : i + n])
        ngrams[gram] += 1
    results = [(gram, count) for gram, count in ngrams.items() if count >= min_count]
    results.sort(key=lambda x: -x[1])
    return results[:max_results]


def compute_punctuation(text: str) -> dict[str, dict[str, float]]:
    """Compute punctuation density per 1000 characters."""
    total_chars = len(text.replace("\n", "").replace(" ", ""))
    if total_chars == 0:
        return {}
    densities: dict[str, dict[str, float]] = {}
    for name, chars in PUNCT_MAP.items():
        count = sum(text.count(c) for c in chars)
        per_1k = round(count * 1000 / total_chars, 1)
        densities[name] = {"count": count, "per_1000": per_1k}
    return densities


def compute_connectives(text: str) -> dict[str, dict[str, dict[str, float]]]:
    """Compute connective density per 1000 characters."""
    total_chars = len(text.replace("\n", "").replace(" ", ""))
    if total_chars == 0:
        return {}
    results: dict[str, dict[str, dict[str, float]]] = {}
    for category, words in CONNECTIVES.items():
        cat_results: dict[str, dict[str, float]] = {}
        for word in words:
            count = text.count(word)
            if count > 0:
                per_1k = round(count * 1000 / total_chars, 1)
                cat_results[word] = {"count": count, "per_1000": per_1k}
        if cat_results:
            results[category] = cat_results
    return results


def detect_rhetoric(text: str) -> dict[str, int]:
    """Rule-based detection of rhetorical patterns."""
    results: dict[str, int] = {}
    sent_texts = [s[0] for s in segment_sentences(text)]
    parallelism_count = 0
    for i in range(len(sent_texts) - 2):
        a, b, c = sent_texts[i][:20], sent_texts[i + 1][:20], sent_texts[i + 2][:20]
        la, lb, lc = len(a), len(b), len(c)
        if la > 0 and lb > 0 and lc > 0:
            if abs(la - lb) / max(la, lb) < 0.3 and abs(lb - lc) / max(lb, lc) < 0.3:
                parallelism_count += 1
    results["排比"] = parallelism_count
    shewen = len(re.findall(r"(为何|为什么|怎么|怎样|如何)[^？]{0,15}？", text))
    results["设问"] = shewen
    fanwen = len(re.findall(r"(难道|岂|怎能|怎会|莫非)[^？]{0,15}？", text))
    results["反问"] = fanwen
    repetition = 0
    for phrase_len in [3, 4, 5]:
        phrases: dict[str, list[int]] = {}
        for i in range(len(text) - phrase_len):
            phrase = text[i : i + phrase_len]
            if phrase not in phrases:
                phrases[phrase] = []
            phrases[phrase].append(i)
        for phrase, positions in phrases.items():
            if len(positions) >= 3:
                for j in range(len(positions) - 1):
                    if positions[j + 1] - positions[j] < 100:
                        repetition += 1
                        break
    results["反复"] = repetition
    return results


def count_ai_markers(text: str) -> dict[str, int]:
    """Count AI-typical markers."""
    results: dict[str, int] = {}
    for marker in AI_MARKERS:
        count = text.count(marker)
        if count > 0:
            results[marker] = count
    return results


def count_transition_words(text: str) -> dict[str, Any]:
    """Count transition words and compare against chapter word count."""
    total_chars = len(text.replace("\n", "").replace(" ", ""))
    results: dict[str, int] = {}
    for word in TRANSITION_WORDS:
        count = text.count(word)
        if count > 0:
            results[word] = count
    total = sum(results.values())
    density_per_3000 = round(total * 3000 / total_chars, 1) if total_chars > 0 else 0
    return {
        "words": results,
        "total_transitions": total,
        "density_per_3000_chars": density_per_3000,
    }


def read_chapters(paths: list[str]) -> dict[str, str]:
    """Read all chapter files from paths (files or directories)."""
    texts: dict[str, str] = {}
    for p in paths:
        pp = Path(p)
        if pp.is_dir():
            for md_file in sorted(pp.glob("*.md")):
                try:
                    texts[md_file.name] = md_file.read_text(encoding="utf-8")
                except Exception:
                    continue
        elif pp.is_file():
            try:
                texts[pp.name] = pp.read_text(encoding="utf-8")
            except Exception:
                continue
    return texts


def compute_all_stats(texts: dict[str, str]) -> dict[str, Any]:
    """Run all statistical analyses on the given texts."""
    combined = "\n\n".join(texts.values())
    total_chars = len(combined.replace("\n", "").replace(" ", ""))
    sentences = segment_sentences(combined)
    paragraphs = segment_paragraphs(combined)
    return {
        "sample": {
            "file_count": len(texts),
            "files": sorted(texts.keys()),
            "total_chars": total_chars,
        },
        "sentence_length": compute_sentence_stats(sentences),
        "paragraph_length": compute_paragraph_stats(paragraphs),
        "ttr": compute_ttr(combined),
        "bigrams": [
            {"gram": g, "count": c}
            for g, c in compute_ngrams(combined, n=2, min_count=50, max_results=20)
        ],
        "trigrams": [
            {"gram": g, "count": c}
            for g, c in compute_ngrams(combined, n=3, min_count=20, max_results=20)
        ],
        "4grams": [
            {"gram": g, "count": c}
            for g, c in compute_ngrams(combined, n=4, min_count=10, max_results=20)
        ],
        "punctuation": compute_punctuation(combined),
        "connectives": compute_connectives(combined),
        "rhetoric": detect_rhetoric(combined),
        "ai_markers": count_ai_markers(combined),
        "transition_density": count_transition_words(combined),
    }


def main() -> None:
    if len(sys.argv) < 2:
        sys.stdout.write(
            "Usage: compute_stats.py <chapter_dir_or_files...> [--output stats.json]\n"
        )
        sys.stdout.write("  Outputs JSON to stdout if no --output specified.\n")
        sys.exit(1)
    args = sys.argv[1:]
    output_path = None
    if "--output" in args:
        idx = args.index("--output")
        output_path = args[idx + 1]
        args = args[:idx] + args[idx + 2 :]
    paths = args
    if not paths:
        sys.stderr.write("Error: no input files specified\n")
        sys.exit(1)
    texts = read_chapters(paths)
    if not texts:
        sys.stderr.write("Error: no readable files found\n")
        sys.exit(1)
    stats = compute_all_stats(texts)
    result = json.dumps(stats, indent=2, ensure_ascii=False)
    if output_path:
        safe_write(Path(output_path), result)
        sys.stdout.write(f"Stats written to {output_path}\n")
    else:
        sys.stdout.write(result + "\n")


if __name__ == "__main__":
    main()
