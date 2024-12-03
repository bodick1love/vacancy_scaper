import os
import re
import math
import json
import logging

import nltk
import requests
from urllib.parse import urlencode
from bs4 import BeautifulSoup
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords

import models
import utils
from parsers.base_parser import BaseParser


nltk.download("punkt")
nltk.download("punkt_tab")
nltk.download("stopwords")

logger = logging.getLogger(__name__)


class WorkUaParser(BaseParser):
    """
    A parser for interacting with the Work.ua website to search resumes and handle related data.

    Attributes:
        base_url (str): The base URL of Work.ua.
        __headers (dict): HTTP headers for requests.
        REGIONS (dict): A dictionary of regions and their IDs.
        SALARY_FROM_OPTIONS (dict): Salary range options (minimum salary).
        SALARY_TO_OPTIONS (dict): Salary range options (maximum salary).
        EXPERIENCE_OPTIONS (dict): Experience options (e.g., junior, mid, senior).
    """

    base_url = os.getenv("WORK_UA_URL")

    def __init__(self):
        """
        Initializes the Work.ua parser with the base URL for resumes.
        """
        self.__set_headers()
        self.__load_regions()
        self.__load_salary_options()
        self.__load_experience_options()

    def __load_regions(self) -> None:
        """
        Loads the cities data from a JSON file. If the file doesn't exist or is invalid,
        it fetches the data from the JavaScript file URL and saves it to the JSON file.
        """
        json_file_path = os.getenv("WORK_UA_REGIONS_JSON_PATH")

        try:
            with open(json_file_path, "r") as json_file:
                regions = json.load(json_file)
                self.REGIONS = regions
                return
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.info(f"Failed to load regions from file: {e}. Fetching from URL...")

        min_js_url = os.getenv("WORK_UA_MIN_JS_URL")
        response = requests.get(min_js_url)
        if response.status_code != 200:
            raise Exception(
                f"Failed to fetch JavaScript content: {response.status_code}"
            )

        js_content = response.text

        pattern = r"citiesTH\s*=\s*\[(.*?)];"
        match = re.search(pattern, js_content, re.DOTALL)

        if match:
            cities_th_raw = match.group(1)
            cities_th_json = re.sub(r"(\w+):", r'"\1":', cities_th_raw)

            try:
                cities_th_list = json.loads(f"[{cities_th_json}]")
                regions = {city["en"]: city["id"] for city in cities_th_list}

                with open(json_file_path, "w") as json_file:
                    json.dump(regions, json_file, indent=4)
                    logger.info(f"Regions fetched and saved to {json_file_path}.")

                self.REGIONS = regions
                return

            except json.JSONDecodeError as e:
                raise Exception(f"Error decoding JSON: {e}")
        else:
            raise Exception("citiesTH list not found in the JavaScript content.")

    def __load_salary_options(self) -> None:
        """
        Loads the salary options data from a JSON file. If the file doesn't exist or is invalid,
        it fetches the data from the JavaScript file URL and saves it to the JSON file.
        """
        json_file_path = os.getenv("WORK_UA_SALARY_OPTIONS_JSON_PATH")

        try:
            with open(json_file_path, "r") as json_file:
                salary_options = json.load(json_file)
                self.SALARY_FROM_OPTIONS = salary_options["SALARY_FROM_OPTIONS"]
                self.SALARY_TO_OPTIONS = salary_options["SALARY_TO_OPTIONS"]
                return
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.info(f"Failed to load salary options from file: {e}.")
            return

    def __load_experience_options(self) -> None:
        """
        Loads the experience options data from a JSON file. If the file doesn't exist or is invalid,
        it fetches the data from the JavaScript file URL and saves it to the JSON file.
        """
        json_file_path = os.getenv("WORK_UA_EXPERIENCE_OPTIONS_JSON_PATH")

        try:
            with open(json_file_path, "r") as json_file:
                experience_options = json.load(json_file)
                self.EXPERIENCE_OPTIONS = experience_options
                return
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.info(f"Failed to load experience options from file: {e}.")
            return

    def __set_headers(self) -> None:
        """
        Sets the headers for the requests to the Robota.ua website.
        """
        self.__headers = {
            "User-Agent": os.getenv("ROBOTA_UA_USER_AGENT"),
            "Referer": os.getenv("ROBOTA_UA_REFERER"),
        }

    @staticmethod
    def get_total_candidates(html: str) -> int:
        """
        Parses the HTML content to extract the total number of candidates.
        Searches for the word 'candidate' or 'candidates' and extracts the number preceding it.
        :param html: Raw HTML content of the first page.
        :return: Total number of candidates as an integer.
        """
        soup = BeautifulSoup(html, "html.parser")
        text_content = soup.get_text()

        # Regular expression to match a number followed by 'candidate' or 'candidates'
        match = re.search(
            r"(\d+)\s+(candidate|candidates)", text_content, re.IGNORECASE
        )

        if match:
            total_candidates = int(match.group(1))
            return total_candidates
        else:
            raise Exception("Unable to find candidate count in the HTML content.")

    @staticmethod
    def build_resumes_url(params: dict) -> str:
        """
        Builds the URL for fetching resume data using query parameters.
        :param params: Dictionary of search parameters.
        :return: Formatted URL string.
        """
        return f"{WorkUaParser.base_url}{os.getenv('WORK_UA_RESUMES_URL')}?{urlencode(params)}"

    @staticmethod
    def format_experience_detail(experience: str) -> str:
        """
        Formats the experience detail by removing unnecessary characters.
        :param experience: Raw experience text.
        :return: Cleaned-up experience string.
        """
        return experience.strip().replace("\xa0", " ")

    def __unpack_search_options(self, params: models.SearchOptions) -> dict:
        """
        Converts the provided search options into a dictionary suitable for API requests.
        :param params: SearchOptions object containing search parameters.
        :return: Dictionary containing search parameters for the request.
        """
        payload = {
            "search": params.search,
        }

        if params.region:
            region = utils.get_most_similar_word(params.region, self.REGIONS.keys())
            payload["region"] = self.REGIONS[region] if region else None
        if params.salary_from:
            payload["salaryfrom"] = self.SALARY_FROM_OPTIONS[str(params.salary_from)]
        if params.salary_to:
            payload["salaryto"] = self.SALARY_TO_OPTIONS[str(params.salary_to)]
        if params.experience:
            payload["experience"] = "+".join(
                self.EXPERIENCE_OPTIONS[exp] for exp in params.experience
            )

        return payload

    def get_resume_pages(self, params: models.SearchOptions) -> list[str]:
        """
        Fetches HTML content of the Work.ua resume section, formatted with pagination and search parameters.
        :param params: Search options for filtering resumes.
        :return: List of HTML page contents.
        """
        headers = self.__headers
        payload = self.__unpack_search_options(params)

        page = 1
        payload["page"] = page

        url = WorkUaParser.build_resumes_url(payload)
        scraper_api_url = utils.build_url_with_scraper_api(url)

        html_pages = []
        try:
            response = requests.get(scraper_api_url, timeout=60, headers=headers)
            response.raise_for_status()

            html = response.text

            total_candidates = WorkUaParser.get_total_candidates(html)
            total_pages = math.ceil(total_candidates / 14)
            logger.info(
                f"Total candidates: {total_candidates}, Total pages: {total_pages} on Work.ua"
            )

            html_pages.append(html)
            logger.info(f"Page {page} fetched successfully.")

            # Fetch add and even pages to avoid Forbidden error
            for page in range(2, total_pages + 1, 2):
                payload["page"] = page

                url = self.build_resumes_url(payload)
                scraper_api_url = utils.build_url_with_scraper_api(url)

                response = requests.get(scraper_api_url, timeout=60, headers=headers)
                response.raise_for_status()

                html_pages.append(response.text)
                logger.info(f"Page {page} fetched successfully.")

            for page in range(3, total_pages + 1, 2):
                payload["page"] = page

                url = self.build_resumes_url(payload)
                scraper_api_url = utils.build_url_with_scraper_api(url)

                response = requests.get(scraper_api_url, timeout=60, headers=headers)
                response.raise_for_status()

                html_pages.append(response.text)
                logger.info(f"Page {page} fetched successfully.")

        except requests.RequestException as e:
            logger.info(f"Error fetching URL {url} on page {page}: {e}")
            raise

        return html_pages

    @staticmethod
    def get_resume_href_from_html(html: str) -> list[str]:
        """
        Parses the HTML content and extracts relevant data from the Work.ua resume section.
        :param html: Raw HTML content as a string.
        :return: List of resume URLs (href attributes).
        """
        soup = BeautifulSoup(html, "html.parser")

        divs = soup.find_all(
            "div",
            class_=lambda class_name: class_name
            and "card" in class_name
            and "resume-link" in class_name,
        )

        hrefs = []
        for div in divs:
            a_tag = div.find("a", href=True)
            if a_tag:
                hrefs.append(a_tag["href"])

        return hrefs

    @staticmethod
    def get_resume_html_from_href(href: str) -> str | None:
        """
        Fetches the HTML content of a resume page from Work.ua using the provided URL.

        This method takes a resume URL (relative path), constructs the full URL,
        and fetches the raw HTML content of the resume page. If the request is
        successful, it returns the HTML content; otherwise, it logs an error and
        returns `None`.

        :param href: The relative URL of the resume page (from Work.ua).

        :return: The raw HTML content of the resume page as a string if the request is successful,
                 or `None` if there is an error fetching the URL.
        """
        url = f"{WorkUaParser.base_url}{href}"

        scraper_api_url = utils.build_url_with_scraper_api(url)

        try:
            response = requests.get(scraper_api_url, timeout=60)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            logger.info(f"Error fetching URL {url}: {e}")
            return None

    @staticmethod
    def parse_resume(html: str) -> dict:
        """
        Parses the HTML content of a resume page and extracts relevant details.
        :param html: Raw HTML content of a resume.
        :return: Resume object with parsed details.
        """
        soup = BeautifulSoup(html, "html.parser")

        # Initialize result dictionary
        resume = {
            "salary_expectation": "",
            "experience": [],
            "filling_percentage": 0,
        }

        # Extract salary expectation
        description_meta = soup.find("meta", attrs={"name": "Description"})
        if description_meta:
            description_content = description_meta.get("content", "")
            if "salary starting at" in description_content:
                salary_part = description_content.split("salary starting at")[-1]
                salary = salary_part.split()[0].strip()
                resume["salary expectation"] = salary

        # Extract work experience
        work_experience_header = soup.find("h2", string="Work experience")
        if work_experience_header:
            experience_section = work_experience_header.find_next_siblings(
                "h2", class_=lambda class_name: class_name and "h4" in class_name
            )
            for position_tag in experience_section:
                position = position_tag.text.strip()

                details_tag = position_tag.find_next_sibling("p", class_="mb-0")
                if details_tag:
                    duration_tag = details_tag.find("span", class_="text-default-7")
                    if duration_tag:
                        duration = WorkUaParser.format_experience_detail(
                            duration_tag.text
                        )
                    else:
                        duration = None

                    details_text = details_tag.get_text(separator=" ", strip=True)
                    details = WorkUaParser.format_experience_detail(
                        details_text.replace(duration or "", "")
                    )

                    experience = {
                        "position": position,
                        "duration": duration,
                        "details": details,
                    }
                    resume["experience"].append(experience)

        # Analyze resume text to calculate filling percentage
        all_text = soup.get_text(separator=" ", strip=True)
        tokens = word_tokenize(all_text.lower())

        stop_words = set(stopwords.words("english"))
        meaningful_words = [
            word for word in tokens if word.isalnum() and word not in stop_words
        ]

        total_words = len(tokens)
        meaningful_words_count = len(meaningful_words)

        filling_percentage = (
            (meaningful_words_count / total_words) * 100 if total_words else 0
        )

        resume["filling_percentage"] = round(filling_percentage)

        return resume

    def search_resumes(self, params: models.SearchOptions) -> list[models.Resume]:
        """
        Searches for resumes on Work.ua based on the provided search options.

        This method first fetches the pages containing resume listings, extracts the
        resume links from each page, and then fetches and parses each resume's HTML
        content to extract relevant details.

        The method performs the following steps:
        1. Fetches HTML content of the resume listing pages.
        2. Extracts the resume URLs from the pages.
        3. Fetches the HTML content of each individual resume.
        4. Parses the HTML content of each resume into a structured `Resume` object.

        Logs the progress of each step, including the number of pages and resumes fetched and parsed.

        :param params: The search options that define the search criteria for resumes.
                       This is an instance of `models.SearchOptions` containing filters
                       such as region, salary, and experience.

        :return: A list of `models.Resume` objects representing the parsed resumes.
        """
        page_htmls = self.get_resume_pages(params)
        logger.info(f"Fetched {len(page_htmls)} pages.")

        hrefs = []
        for html in page_htmls:
            hrefs.extend(WorkUaParser.get_resume_href_from_html(html))
        logger.info(f"Fetched {len(hrefs)} resume links.")

        resume_htmls = []
        for i, href in enumerate(hrefs, start=1):
            resume_html = WorkUaParser.get_resume_html_from_href(href)
            if resume_html:
                resume_htmls.append(resume_html)
                logger.info(f"Resume {i} fetched successfully.")
            else:
                logger.info(f"Resume {i} failed to fetch.")

        logger.info(f"Fetched {len(resume_htmls)} resumes.")

        resumes = []
        for i, resume_html in enumerate(resume_htmls, start=1):
            resume = WorkUaParser.parse_resume(resume_html)
            if resume:
                resume_json = {"href": WorkUaParser.base_url + hrefs[i - 1], **resume}

                resumes.append(models.Resume(**resume_json))
                logger.info(f"Resume {i} parsed successfully.")
            else:
                logger.info(f"Resume {i} failed to parse.")

        return resumes
