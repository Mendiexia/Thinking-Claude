#!/usr/bin/env python3
"""Batch process multiple texts through GPTINF.

Usage:
    # Process all .txt files in a directory:
    python batch_process.py --input-dir ./texts/ --output-dir ./results/

    # Process a list of files:
    python batch_process.py --files text1.txt text2.txt text3.txt
"""

import argparse
import json
import os
import sys
import time

from gptinf_processor import GptinfProcessor
from quality_checker import check_quality, format_report


def process_batch(files, output_dir, headless=False, slow_mo=100, delay=5, profile_dir=None):
    """Process a batch of text files through GPTINF.

    Args:
        files: List of input file paths.
        output_dir: Directory to save outputs and reports.
        headless: Run browser in headless mode.
        slow_mo: Delay between browser actions in ms.
        delay: Seconds to wait between processing each file.
        profile_dir: Chrome user data directory (to reuse login session).
    """
    os.makedirs(output_dir, exist_ok=True)

    processor = GptinfProcessor(headless=headless, slow_mo=slow_mo, profile_dir=profile_dir)
    results = []

    try:
        processor.start()

        for i, filepath in enumerate(files):
            basename = os.path.splitext(os.path.basename(filepath))[0]
            print(f"\n{'='*50}")
            print(f"  Processing [{i+1}/{len(files)}]: {filepath}")
            print(f"{'='*50}")

            with open(filepath, "r", encoding="utf-8") as f:
                original = f.read().strip()

            if not original:
                print(f"  Skipping empty file: {filepath}")
                continue

            try:
                output = processor.process_text(original)

                # Save output
                out_path = os.path.join(output_dir, f"{basename}_output.txt")
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(output)

                # Quality check
                result = check_quality(original, output)
                print(format_report(result))

                # Save report
                report_path = os.path.join(output_dir, f"{basename}_report.json")
                with open(report_path, "w", encoding="utf-8") as f:
                    json.dump(result, f, indent=2)

                results.append({
                    "file": filepath,
                    "passed": result["passed"],
                    "issues": result["issues"],
                    "similarity": result["metrics"]["similarity"]["text_similarity"],
                })

            except Exception as e:
                print(f"  Error processing {filepath}: {e}")
                results.append({
                    "file": filepath,
                    "passed": False,
                    "issues": [str(e)],
                    "similarity": None,
                })

            # Wait between requests to be respectful
            if i < len(files) - 1:
                print(f"  Waiting {delay}s before next file...")
                time.sleep(delay)

    finally:
        processor.stop()

    # Print summary
    print(f"\n{'='*60}")
    print("  BATCH PROCESSING SUMMARY")
    print(f"{'='*60}")
    passed = sum(1 for r in results if r["passed"])
    print(f"  Total: {len(results)} | Passed: {passed} | Failed: {len(results) - passed}")
    for r in results:
        status = "PASS" if r["passed"] else "FAIL"
        sim = f"{r['similarity']:.3f}" if r["similarity"] is not None else "N/A"
        print(f"  [{status}] {r['file']} (similarity: {sim})")
    print(f"{'='*60}")

    # Save summary
    summary_path = os.path.join(output_dir, "batch_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\n  Summary saved to {summary_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Batch process texts through GPTINF.",
    )
    parser.add_argument(
        "--files",
        nargs="+",
        help="List of text files to process",
    )
    parser.add_argument(
        "--input-dir",
        help="Directory containing .txt files to process",
    )
    parser.add_argument(
        "--output-dir",
        default="./batch_output",
        help="Directory for output files (default: ./batch_output)",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser in headless mode",
    )
    parser.add_argument(
        "--slow-mo",
        type=int,
        default=100,
        help="Delay between browser actions in ms",
    )
    parser.add_argument(
        "--delay",
        type=int,
        default=5,
        help="Seconds to wait between files (default: 5)",
    )
    parser.add_argument(
        "--profile",
        help="Path to Chrome user data directory (to reuse your login session)",
    )

    args = parser.parse_args()

    files = []
    if args.files:
        files = args.files
    elif args.input_dir:
        files = sorted(
            os.path.join(args.input_dir, f)
            for f in os.listdir(args.input_dir)
            if f.endswith(".txt")
        )
    else:
        print("Error: Provide --files or --input-dir")
        sys.exit(1)

    if not files:
        print("No files to process.")
        sys.exit(0)

    print(f"Found {len(files)} files to process.")
    process_batch(
        files,
        args.output_dir,
        headless=args.headless,
        slow_mo=args.slow_mo,
        delay=args.delay,
        profile_dir=args.profile,
    )


if __name__ == "__main__":
    main()
