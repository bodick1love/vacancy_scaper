import os
import logging
import tempfile

import webbrowser


logger = logging.getLogger(__name__)


def save_and_open_html(response_text):
    """
    Saves the provided HTML content to a temporary file and opens it in the default web browser.

    This function:
    1. Creates a temporary directory.
    2. Writes the provided HTML content to a file named `page.html` in that directory.
    3. Attempts to open the saved HTML file in the default web browser.

    If any of the steps fail (directory creation, file writing, or file opening), the function logs the error.

    Args:
        response_text (str): The HTML content to be saved and opened in the browser.

    Returns:
        None
    """
    try:
        temp_dir = tempfile.mkdtemp()
    except OSError as e:
        logger.info(f"Failed to create temporary directory: {e}")
        return

    try:
        temp_file_path = os.path.join(temp_dir, "page.html")

        with open(temp_file_path, "w", encoding="utf-8") as file:
            file.write(response_text)
    except (OSError, IOError) as e:
        logger.info(f"Failed to write to the temporary file: {e}")
        return

    try:
        webbrowser.open(f"file://{temp_file_path}")
        logger.info(f"HTML file saved to {temp_file_path} and opened in browser.")
    except webbrowser.Error as e:
        logger.info(f"Failed to open the file in the web browser: {e}")
