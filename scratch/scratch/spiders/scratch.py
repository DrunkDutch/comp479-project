import scrapy
from bs4 import BeautifulSoup


class ScratchSpider(scrapy.Spider):
    name = "scratch"
    start_urls = (
        "https://csu.qc.ca/content/student-groups-associations",
        "https://www.concordia.ca/artsci/students/associations.html",
        "http://www.cupfa.org",
        "http://cufa.net"
    )


    # TODO  Add check for relative urls and make absolute if case
    # TODO  Have it keep following new links
    def parse(self, response):
        # use lxml to get decent HTML parsing speed
        soup = BeautifulSoup(response.text, 'html')
        for link in soup.find_all('a', href=True):
            print link['href']
        yield {
            "url": response.url
            # "title": soup.h1.string
        }

