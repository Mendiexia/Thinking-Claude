"""Configuration for GPTINF automation."""

import os
import platform

# GPTINF website URL
GPTINF_URL = "https://www.gptinf.com/"

# Browser settings
HEADLESS = False  # Set True to run without visible browser
SLOW_MO = 100  # Milliseconds between actions (helps avoid detection)
TIMEOUT = 60000  # Max wait time for elements in milliseconds

# Chrome user data directory — so the automation reuses your logged-in session.
# Set this to your Chrome profile path. The defaults below cover the most common
# locations per OS. Override with the --profile CLI flag or by editing this value.
_system = platform.system()
if _system == "Windows":
    _default_profile = os.path.join(
        os.environ.get("LOCALAPPDATA", ""),
        "Google", "Chrome", "User Data",
    )
elif _system == "Darwin":  # macOS
    _default_profile = os.path.expanduser(
        "~/Library/Application Support/Google/Chrome",
    )
else:  # Linux
    _default_profile = os.path.expanduser("~/.config/google-chrome")

CHROME_USER_DATA_DIR = _default_profile

# Selectors for GPTINF interface (update if site changes)
SELECTORS = {
    # Input textarea - common selector patterns for the GPTINF editor
    "input_area": 'textarea[placeholder*="Paste"], textarea[placeholder*="paste"], '
                  'textarea[placeholder*="Enter"], textarea[placeholder*="enter"], '
                  'div[contenteditable="true"], textarea.input, '
                  '#input, #editor, textarea',
    # Process/submit button
    "process_button": 'button:has-text("Process"), button:has-text("Humanize"), '
                      'button:has-text("Paraphrase"), button:has-text("Start"), '
                      'button:has-text("Submit"), button:has-text("Rewrite")',
    # Output area
    "output_area": 'textarea[readonly], div.output, #output, '
                   'div[class*="output"], div[class*="result"]',
    # Loading indicator
    "loading": '.loading, .spinner, [class*="loading"], [class*="progress"]',
}

# Quality check thresholds
QUALITY_THRESHOLDS = {
    "min_similarity": 0.3,       # Minimum semantic similarity to original (0-1)
    "max_similarity": 0.95,      # Maximum similarity (too high = barely changed)
    "min_readability": 30,       # Minimum Flesch reading ease score
    "max_readability": 80,       # Maximum (too simple might lose meaning)
    "min_word_retention": 0.5,   # Minimum ratio of output words to input words
    "max_word_retention": 1.5,   # Maximum ratio
    "min_sentence_count_ratio": 0.5,  # Output sentences vs input sentences
}
