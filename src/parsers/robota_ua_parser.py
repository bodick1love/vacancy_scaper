import os
import json
import logging

import requests

import models
import utils
from parsers.base_parser import BaseParser


logger = logging.getLogger(__name__)


class RobotaUaParser(BaseParser):
    """
    A parser for interacting with the Robota.ua website to search resumes and handle related data.

    Attributes:
        base_url (str): The base URL of Robota.ua.
        __token (str): The authentication token for API requests.
        __headers (dict): The headers required for authenticated requests.
        REGIONS (dict): A dictionary of regions, where the key is the region name and the value is the region ID.
        EXPERIENCE_OPTIONS (dict): A dictionary of experience options for filtering search results.
    """

    base_url = "https://robota.ua"

    def __init__(self):
        """
        Initializes the RobotaUaParser by logging in, setting headers, and loading regions and experience options.
        """
        self.__login()
        self.__set_headers()
        self.__load_regions()
        self.__load_experience_options()

    def __load_regions(self) -> None:
        """
        Loads the region data either from a JSON file or from a remote URL if the file is unavailable.
        If fetched from the URL, the data is saved to the JSON file for future use.

        Raises:
            Exception: If fetching regions from the URL fails.
        """
        json_file_path = os.getenv("ROBOTA_UA_REGIONS_JSON_PATH")

        try:
            with open(json_file_path, "r") as json_file:
                regions = json.load(json_file)
                self.REGIONS = regions
                return
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.info(f"Failed to load regions from file: {e}. Fetching from URL...")

        url = os.getenv("ROBOTA_UA_REGIONS_URL")
        response = requests.get(url)

        if response.status_code != 200:
            raise Exception("Failed to fetch regions from Robota.ua")

        data = response.json()
        regions = {city["en"]: city["id"] for city in data}

        with open(json_file_path, "w") as json_file:
            json.dump(regions, json_file, indent=4)
            logger.info(f"Regions fetched and saved to {json_file_path}.")

        self.REGIONS = regions
        return

    def __load_experience_options(self) -> None:
        """
        Loads the experience options data from a JSON file. If the file doesn't exist or is invalid,
        the method logs the error and does nothing.
        """
        json_file_path = os.getenv("ROBOTA_UA_EXPERIENCE_OPTIONS_JSON_PATH")

        try:
            with open(json_file_path, "r") as json_file:
                experience_options = json.load(json_file)
                self.EXPERIENCE_OPTIONS = experience_options
                return
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.info(f"Failed to load experience options from file: {e}.")
            return

    def __login(self) -> None:
        """
        Logs in to the Robota.ua website and retrieves a token for authentication.

        Raises:
            Exception: If login fails.
        """
        url = os.getenv("ROBOTA_UA_LOGIN_URL")

        username = os.getenv("ROBOTA_UA_USERNAME")
        password = os.getenv("ROBOTA_UA_PASSWORD")

        payload = {"username": username, "password": password}

        response = requests.post(url, json=payload)

        if response.status_code == 200:
            self.__token = response.json()
        else:
            raise Exception("Failed to login to Robota.ua")

    def __set_headers(self) -> None:
        """
        Sets the HTTP headers required for making authenticated requests.
        """
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.__token}",
        }

        self.__headers = headers

    @staticmethod
    def format_salary_expectation(salary: str) -> str:
        """
        Formats the salary expectation by stripping extra spaces and replacing non-breaking spaces.

        Args:
            salary (str): The salary string to format.

        Returns:
            str: The formatted salary string.
        """
        return salary.strip().replace("\xa0", " ")

    @staticmethod
    def unpack_resume_from_response(resume: models.Resume) -> dict:
        """
        Unpacks a resume from the response into a structured dictionary.

        Args:
            resume (models.Resume): The resume data to unpack.

        Returns:
            dict: A structured dictionary containing the resume details.
        """
        resume_json = {
            "href": f"{RobotaUaParser.base_url}/candidates/{resume["resumeId"]}",
            "salary_expectation": RobotaUaParser.format_salary_expectation(
                resume["salary"]
            ),
            "experience": [
                {
                    "position": exp["position"],
                    "duration": exp["datesDiff"],
                    "details": exp["company"],
                }
                for exp in resume["experience"]
            ],
            "filling_percentage": resume["fillingPercentage"],
        }

        return resume_json

    def __unpack_search_options(self, params: models.SearchOptions) -> dict:
        """
        Prepares the search payload based on the user's search options.

        Args:
            params (models.SearchOptions): The search options provided by the user.

        Returns:
            dict: The payload for the search request.
        """
        region_name = utils.get_most_similar_word(params.region, self.REGIONS.keys())
        region_id = self.REGIONS[region_name] if region_name else None

        payload = {
            "cityId": region_id,
            "keyWords": params.search,
            "salary": {
                "from": params.salary_from,
                "to": params.salary_to,
            },
            "experienceIds": [
                self.EXPERIENCE_OPTIONS.get(exp)
                for exp in params.experience
                if self.EXPERIENCE_OPTIONS.get(exp)
            ],
        }

        if "More than 5 years" in params.experience:
            payload["experienceIds"].append(self.EXPERIENCE_OPTIONS["5 to 10 years"])
            payload["experienceIds"].append(
                self.EXPERIENCE_OPTIONS["More than 10 years"]
            )

        return payload

    def search_resumes(
        self, params: models.SearchOptions = None
    ) -> list[models.Resume]:
        """
        Searches for resumes on Robota.ua based on the provided search options.

        Args:
            params (models.SearchOptions): The search options.

        Returns:
            list[models.Resume]: A list of resumes matching the search criteria.

        Raises:
            Exception: If the search request fails.
        """
        url = os.getenv("ROBOTA_UA_RESUMES_URL")

        headers = self.__headers
        payload = self.__unpack_search_options(params)

        response = requests.post(url, json=payload, headers=headers)

        total = response.json()["total"]
        logger.info(f"Found {total} resumes on Robota.ua")

        payload["count"] = total
        response = requests.post(url, json=payload, headers=headers)

        resumes = []
        if response.status_code == 200:
            data = response.json()

            for resume in data["documents"]:
                resume_json = RobotaUaParser.unpack_resume_from_response(resume)
                resumes.append(models.Resume(**resume_json))

            return resumes

        else:
            logger.info(
                f"Request failed with status code {response.status_code}: {response.text}"
            )
            response.raise_for_status()
