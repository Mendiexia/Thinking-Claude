#!/usr/bin/env python3
"""GPTINF Automation - Process text and check output quality.

Usage:
    # Process text from a file:
    python main.py --file input.txt

    # Process text directly:
    python main.py --text "Your text to process here..."

    # Process and save output:
    python main.py --file input.txt --output result.txt

    # Run in headless mode:
    python main.py --file input.txt --headless

    # Quality check only (skip browser, provide both texts):
    python main.py --quality-only --file original.txt --output-text "processed text"
"""

import argparse
import json
import sys

from gptinf_processor import GptinfProcessor
from quality_checker import check_quality, format_report


def read_input(args):
    """Read input text from file or command line argument."""
    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            return f.read().strip()
    elif args.text:
        return args.text.strip()
    else:
        print("Error: Provide input via --file or --text")
        sys.exit(1)


def run_quality_only(args):
    """Run quality check without browser automation."""
    original = read_input(args)
    if not args.output_text:
        print("Error: --quality-only requires --output-text with the processed text")
        sys.exit(1)
    output = args.output_text.strip()

    result = check_quality(original, output)
    print(format_report(result))

    if args.json:
        print("\n--- JSON Report ---")
        print(json.dumps(result, indent=2))

    return result


def run_full_pipeline(args):
    """Run the full pipeline: browser automation + quality check."""
    original = read_input(args)

    print("\n[1/3] Starting browser automation...")
    processor = GptinfProcessor(
        headless=args.headless,
        slow_mo=args.slow_mo,
    )

    try:
        processor.start()
        print("[2/3] Processing text through GPTINF...")
        output = processor.process_text(original)
    except Exception as e:
        print(f"\nError during processing: {e}")
        print("\nTroubleshooting:")
        print("  - Make sure you're logged into gptinf.com in your browser")
        print("  - Check your internet connection")
        print("  - The site layout may have changed — update SELECTORS in config.py")
        print("  - Try running with --headless false to see what's happening")
        sys.exit(1)
    finally:
        processor.stop()

    # Save output if requested
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"  Output saved to {args.output}")

    # Quality check
    print("[3/3] Checking output quality...")
    result = check_quality(original, output)
    print(format_report(result))

    if args.json:
        print("\n--- JSON Report ---")
        print(json.dumps(result, indent=2))

    # Print the output text
    print("\n--- Processed Output ---")
    print(output)
    print("--- End Output ---\n")

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Automate GPTINF text processing and check output quality.",
    )
    parser.add_argument(
        "--file", "-f",
        help="Path to a text file to process",
    )
    parser.add_argument(
        "--text", "-t",
        help="Text string to process (for short inputs)",
    )
    parser.add_argument(
        "--output", "-o",
        help="Path to save the processed output text",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=False,
        help="Run browser in headless mode (no visible window)",
    )
    parser.add_argument(
        "--slow-mo",
        type=int,
        default=100,
        help="Delay between browser actions in ms (default: 100)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Also print quality report as JSON",
    )
    parser.add_argument(
        "--quality-only",
        action="store_true",
        help="Skip browser automation, just run quality check",
    )
    parser.add_argument(
        "--output-text",
        help="Pre-processed output text (used with --quality-only)",
    )

    args = parser.parse_args()

    if args.quality_only:
        result = run_quality_only(args)
    else:
        result = run_full_pipeline(args)

    # Exit with code 1 if quality check failed
    sys.exit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
