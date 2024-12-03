from abc import ABC, abstractmethod


class BaseParser(ABC):
    @abstractmethod
    def search_resumes(self, **kwargs):
        """
        Search resumes on the website.
        """
        pass
