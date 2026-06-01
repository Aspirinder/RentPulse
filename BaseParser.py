from abc import ABC, abstractmethod

class BaseParser(ABC):
    @abstractmethod
    async def parse_list(self, content):
        # Method of collecting links from the main page
        pass

    @abstractmethod
    async def parse_details(self, page, ad_item):
        # Method for collecting descriptions and photos inside an ad
        pass

    @abstractmethod
    def change_page(self, url, number):
        # Method for change page on website
        pass

    @abstractmethod
    async def start_parse(self, engine, url, output, page_number):
        # Method for start parsiong
        pass