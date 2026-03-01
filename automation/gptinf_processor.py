"""Browser automation for GPTINF text processing.

Uses Playwright to automate the GPTINF web interface:
1. Launch Chrome using your existing profile (keeps your GPTINF login)
2. Navigate to gptinf.com
3. Input text into the editor
4. Click the process/humanize button
5. Wait for and extract the output

IMPORTANT: Close Chrome before running so Playwright can use your profile.
"""

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from config import GPTINF_URL, HEADLESS, SLOW_MO, TIMEOUT, SELECTORS, CHROME_USER_DATA_DIR


class GptinfProcessor:
    """Automates text processing through the GPTINF web interface."""

    def __init__(self, headless=None, slow_mo=None, profile_dir=None):
        self.headless = headless if headless is not None else HEADLESS
        self.slow_mo = slow_mo if slow_mo is not None else SLOW_MO
        self.profile_dir = profile_dir or CHROME_USER_DATA_DIR
        self.context = None
        self.page = None
        self.playwright = None

    def start(self):
        """Launch Chrome with your existing profile to keep your GPTINF login.

        Uses launch_persistent_context so cookies/sessions carry over.
        Make sure Chrome is closed before running this.
        """
        self.playwright = sync_playwright().start()

        print(f"  Using Chrome profile: {self.profile_dir}")
        print("  (Make sure Chrome is closed before running!)")

        self.context = self.playwright.chromium.launch_persistent_context(
            user_data_dir=self.profile_dir,
            headless=self.headless,
            slow_mo=self.slow_mo,
            viewport={"width": 1280, "height": 800},
            channel="chrome",  # Use your installed Chrome, not bundled Chromium
        )
        # Persistent context opens with one page by default
        self.page = self.context.pages[0] if self.context.pages else self.context.new_page()
        self.page.set_default_timeout(TIMEOUT)

    def stop(self):
        """Close browser and clean up."""
        if self.context:
            self.context.close()
        if self.playwright:
            self.playwright.stop()
        self.context = None
        self.page = None
        self.playwright = None

    def navigate_to_gptinf(self):
        """Navigate to the GPTINF website and wait for it to load."""
        print(f"  Navigating to {GPTINF_URL}...")
        self.page.goto(GPTINF_URL, wait_until="networkidle")
        # Give the page extra time to fully render JS content
        self.page.wait_for_timeout(2000)
        print("  Page loaded.")

    def _find_element(self, selector_key):
        """Try multiple selector patterns to find an element.

        The GPTINF interface may change, so we try several selectors.
        """
        selectors = SELECTORS[selector_key]
        for selector in selectors.split(", "):
            selector = selector.strip()
            try:
                element = self.page.wait_for_selector(selector, timeout=3000)
                if element and element.is_visible():
                    return element
            except PlaywrightTimeout:
                continue
        return None

    def _find_clickable_button(self):
        """Find the process/humanize button using multiple strategies."""
        # Strategy 1: Use configured selectors
        selectors = SELECTORS["process_button"]
        for selector in selectors.split(", "):
            selector = selector.strip()
            try:
                element = self.page.wait_for_selector(selector, timeout=3000)
                if element and element.is_visible():
                    return element
            except PlaywrightTimeout:
                continue

        # Strategy 2: Find any prominent button
        buttons = self.page.query_selector_all("button")
        for btn in buttons:
            text = (btn.inner_text() or "").strip().lower()
            if any(kw in text for kw in [
                "process", "humanize", "paraphrase", "rewrite",
                "start", "submit", "go", "run"
            ]):
                if btn.is_visible():
                    return btn

        return None

    def input_text(self, text):
        """Input text into the GPTINF editor.

        Args:
            text: The text to process through GPTINF.
        """
        print(f"  Inputting text ({len(text)} chars)...")

        # Try to find the input area
        input_el = self._find_element("input_area")
        if not input_el:
            # Fallback: click on any large text area visible on page
            areas = self.page.query_selector_all("textarea")
            for area in areas:
                if area.is_visible():
                    input_el = area
                    break

        if not input_el:
            # Try contenteditable divs
            divs = self.page.query_selector_all('div[contenteditable="true"]')
            for div in divs:
                if div.is_visible():
                    input_el = div
                    break

        if not input_el:
            raise RuntimeError(
                "Could not find the GPTINF input area. "
                "The site layout may have changed — update SELECTORS in config.py."
            )

        # Clear existing content and type new text
        input_el.click()
        self.page.keyboard.press("Control+a")
        self.page.keyboard.press("Backspace")
        input_el.type(text, delay=10)
        print("  Text entered.")

    def click_process(self):
        """Click the process/humanize button."""
        print("  Looking for process button...")
        button = self._find_clickable_button()
        if not button:
            raise RuntimeError(
                "Could not find the GPTINF process button. "
                "The site layout may have changed — update SELECTORS in config.py."
            )
        print("  Clicking process button...")
        button.click()

    def wait_for_output(self, max_wait_seconds=120):
        """Wait for processing to complete and return the output text.

        Args:
            max_wait_seconds: Maximum time to wait for output.

        Returns:
            The processed/humanized text output.
        """
        print(f"  Waiting for output (max {max_wait_seconds}s)...")

        # Wait for any loading indicators to appear then disappear
        try:
            loading_sel = SELECTORS["loading"]
            for selector in loading_sel.split(", "):
                selector = selector.strip()
                try:
                    self.page.wait_for_selector(selector, timeout=5000, state="visible")
                    # Found a loading indicator, now wait for it to disappear
                    self.page.wait_for_selector(
                        selector,
                        timeout=max_wait_seconds * 1000,
                        state="hidden",
                    )
                    break
                except PlaywrightTimeout:
                    continue
        except PlaywrightTimeout:
            pass

        # Give extra time for content to render after loading finishes
        self.page.wait_for_timeout(3000)

        # Try to find and extract the output text
        output_text = self._extract_output()
        if not output_text:
            # Wait a bit more and retry
            self.page.wait_for_timeout(5000)
            output_text = self._extract_output()

        if not output_text:
            raise RuntimeError(
                "Could not extract output text. "
                "Processing may have failed or the site layout changed."
            )

        print(f"  Output received ({len(output_text)} chars).")
        return output_text

    def _extract_output(self):
        """Extract the output text from the page."""
        # Strategy 1: Look for configured output selectors
        output_el = self._find_element("output_area")
        if output_el:
            text = output_el.inner_text() or output_el.input_value()
            if text and text.strip():
                return text.strip()

        # Strategy 2: Look for textarea elements that now have content
        textareas = self.page.query_selector_all("textarea")
        if len(textareas) >= 2:
            # Often the second textarea is the output
            text = textareas[-1].input_value()
            if text and text.strip():
                return text.strip()

        # Strategy 3: Look for divs with result-like classes
        for cls in ["result", "output", "humanized", "paraphrased", "rewritten"]:
            els = self.page.query_selector_all(f'div[class*="{cls}"]')
            for el in els:
                text = el.inner_text()
                if text and text.strip() and len(text.strip()) > 20:
                    return text.strip()

        # Strategy 4: Check clipboard if a "copy" button was auto-triggered
        return None

    def process_text(self, text):
        """Full pipeline: input text, click process, return output.

        Args:
            text: The text to process through GPTINF.

        Returns:
            The processed output text.
        """
        self.navigate_to_gptinf()
        self.input_text(text)
        self.click_process()
        return self.wait_for_output()
