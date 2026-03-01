"""Quality checker for GPTINF output text.

Analyzes the processed output against the original input using:
- Text similarity (how much meaning is preserved)
- Readability scores (Flesch reading ease, grade level)
- Structural analysis (sentence count, word count, vocabulary diversity)
- Change detection (what actually changed between input and output)
"""

import difflib
import re
from collections import Counter

import textstat

from config import QUALITY_THRESHOLDS


def _tokenize(text):
    """Split text into lowercase words."""
    return re.findall(r'\b[a-zA-Z]+\b', text.lower())


def _sentences(text):
    """Split text into sentences."""
    return [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]


def compute_similarity(original, output):
    """Compute text similarity using SequenceMatcher.

    Returns a ratio between 0 (completely different) and 1 (identical).
    """
    return difflib.SequenceMatcher(None, original, output).ratio()


def compute_word_overlap(original, output):
    """Compute the fraction of original words preserved in output."""
    orig_words = set(_tokenize(original))
    out_words = set(_tokenize(output))
    if not orig_words:
        return 0.0
    return len(orig_words & out_words) / len(orig_words)


def compute_readability(text):
    """Compute readability metrics for the text."""
    return {
        "flesch_reading_ease": textstat.flesch_reading_ease(text),
        "flesch_kincaid_grade": textstat.flesch_kincaid_grade(text),
        "gunning_fog": textstat.gunning_fog(text),
        "automated_readability_index": textstat.automated_readability_index(text),
        "reading_time_seconds": textstat.reading_time(text, ms_per_char=14.69),
    }


def compute_vocabulary_diversity(text):
    """Measure vocabulary richness (type-token ratio)."""
    words = _tokenize(text)
    if not words:
        return 0.0
    return len(set(words)) / len(words)


def compute_structural_metrics(original, output):
    """Compare structural properties of input vs output."""
    orig_words = _tokenize(original)
    out_words = _tokenize(output)
    orig_sents = _sentences(original)
    out_sents = _sentences(output)

    return {
        "original_word_count": len(orig_words),
        "output_word_count": len(out_words),
        "word_count_ratio": len(out_words) / max(len(orig_words), 1),
        "original_sentence_count": len(orig_sents),
        "output_sentence_count": len(out_sents),
        "sentence_count_ratio": len(out_sents) / max(len(orig_sents), 1),
        "original_avg_sentence_length": len(orig_words) / max(len(orig_sents), 1),
        "output_avg_sentence_length": len(out_words) / max(len(out_sents), 1),
    }


def compute_diff_summary(original, output):
    """Generate a human-readable summary of changes."""
    orig_lines = original.splitlines(keepends=True)
    out_lines = output.splitlines(keepends=True)
    diff = list(difflib.unified_diff(orig_lines, out_lines, lineterm=""))

    additions = sum(1 for line in diff if line.startswith("+") and not line.startswith("+++"))
    deletions = sum(1 for line in diff if line.startswith("-") and not line.startswith("---"))

    return {
        "lines_added": additions,
        "lines_removed": deletions,
        "diff_text": "".join(diff[:100]),  # First 100 lines of diff
    }


def _check_threshold(value, min_val, max_val, metric_name):
    """Check if a value falls within acceptable thresholds."""
    issues = []
    if value < min_val:
        issues.append(f"{metric_name} ({value:.2f}) is below minimum ({min_val})")
    if value > max_val:
        issues.append(f"{metric_name} ({value:.2f}) is above maximum ({max_val})")
    return issues


def check_quality(original, output):
    """Run full quality analysis on the GPTINF output.

    Args:
        original: The original input text.
        output: The GPTINF processed output text.

    Returns:
        A dict with quality metrics, issues found, and an overall pass/fail.
    """
    thresholds = QUALITY_THRESHOLDS
    issues = []

    # 1. Similarity analysis
    similarity = compute_similarity(original, output)
    word_overlap = compute_word_overlap(original, output)
    issues.extend(_check_threshold(
        similarity,
        thresholds["min_similarity"],
        thresholds["max_similarity"],
        "Text similarity",
    ))

    # 2. Readability
    orig_readability = compute_readability(original)
    out_readability = compute_readability(output)
    issues.extend(_check_threshold(
        out_readability["flesch_reading_ease"],
        thresholds["min_readability"],
        thresholds["max_readability"],
        "Readability (Flesch)",
    ))

    # 3. Structural metrics
    structural = compute_structural_metrics(original, output)
    issues.extend(_check_threshold(
        structural["word_count_ratio"],
        thresholds["min_word_retention"],
        thresholds["max_word_retention"],
        "Word count ratio",
    ))
    issues.extend(_check_threshold(
        structural["sentence_count_ratio"],
        thresholds["min_sentence_count_ratio"],
        float("inf"),
        "Sentence count ratio",
    ))

    # 4. Vocabulary diversity
    orig_diversity = compute_vocabulary_diversity(original)
    out_diversity = compute_vocabulary_diversity(output)

    # 5. Diff summary
    diff_summary = compute_diff_summary(original, output)

    # 6. Check for obvious problems
    if not output or not output.strip():
        issues.append("Output is empty")
    if output.strip() == original.strip():
        issues.append("Output is identical to input (no changes made)")
    if len(output.strip()) < 10:
        issues.append("Output is suspiciously short")

    passed = len(issues) == 0

    return {
        "passed": passed,
        "issues": issues,
        "metrics": {
            "similarity": {
                "text_similarity": round(similarity, 3),
                "word_overlap": round(word_overlap, 3),
            },
            "readability": {
                "original": orig_readability,
                "output": out_readability,
            },
            "structure": structural,
            "vocabulary_diversity": {
                "original": round(orig_diversity, 3),
                "output": round(out_diversity, 3),
            },
            "changes": {
                "lines_added": diff_summary["lines_added"],
                "lines_removed": diff_summary["lines_removed"],
            },
        },
    }


def format_report(result):
    """Format the quality check result as a readable report.

    Args:
        result: The dict returned by check_quality().

    Returns:
        A formatted string report.
    """
    lines = []
    lines.append("=" * 60)
    lines.append("  GPTINF OUTPUT QUALITY REPORT")
    lines.append("=" * 60)

    status = "PASS" if result["passed"] else "FAIL"
    lines.append(f"\n  Overall: {status}")

    if result["issues"]:
        lines.append(f"\n  Issues ({len(result['issues'])}):")
        for issue in result["issues"]:
            lines.append(f"    - {issue}")

    m = result["metrics"]

    lines.append("\n  --- Similarity ---")
    lines.append(f"  Text similarity:  {m['similarity']['text_similarity']}")
    lines.append(f"  Word overlap:     {m['similarity']['word_overlap']}")

    lines.append("\n  --- Readability (Flesch Reading Ease) ---")
    lines.append(f"  Original: {m['readability']['original']['flesch_reading_ease']}")
    lines.append(f"  Output:   {m['readability']['output']['flesch_reading_ease']}")

    lines.append("\n  --- Structure ---")
    s = m["structure"]
    lines.append(f"  Words:     {s['original_word_count']} -> {s['output_word_count']} "
                 f"(ratio: {s['word_count_ratio']:.2f})")
    lines.append(f"  Sentences: {s['original_sentence_count']} -> {s['output_sentence_count']} "
                 f"(ratio: {s['sentence_count_ratio']:.2f})")
    lines.append(f"  Avg sent length: {s['original_avg_sentence_length']:.1f} -> "
                 f"{s['output_avg_sentence_length']:.1f}")

    lines.append("\n  --- Vocabulary Diversity ---")
    lines.append(f"  Original: {m['vocabulary_diversity']['original']}")
    lines.append(f"  Output:   {m['vocabulary_diversity']['output']}")

    lines.append("\n  --- Changes ---")
    lines.append(f"  Lines added:   {m['changes']['lines_added']}")
    lines.append(f"  Lines removed: {m['changes']['lines_removed']}")

    lines.append("\n" + "=" * 60)
    return "\n".join(lines)
