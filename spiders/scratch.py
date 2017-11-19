import scrapy
import os
import re
from bs4 import BeautifulSoup


class ScratchSpider(scrapy.Spider):
    name = "scratch"
    documentCounter = 0

    # should we remove external domain? Twitter is getting crawled
    # allowed_domains= [
    #     "csu.qc.ca",
    #     "www.concordia.ca",
    #     "www.cupfa.org",
    #     "cufa.net"
    # ]

    def parse(self, response):
        soup = BeautifulSoup(response.text,'html')
        # remove style tags
        while soup.style:
            soup.style.extract()
        # remove script tags
        while soup.script:
            soup.script.extract()
        # filter all text and remove blank spaces
        filteredContent = '\n'.join(filter(lambda x: not re.match(r'^\s*$', x), soup.get_text(" ").strip().encode('utf8').split('\n')))
        #create json output
        jsonOutput = '{"url": "'+response.url+'",\n"content": "'+filteredContent+'"\n}'
        # create new corpus files
        f = self.getResultFile()
        f.write(jsonOutput)
        # insert next urls to crawl
        counter = 0
        for url in response.xpath('//a/@href').extract():
            if ScratchSpider.documentCounter + counter >= self.docLimit:
                break
            if 'http' not in url:
                url = response.urljoin(url)
            yield scrapy.Request(url, callback=self.parse)
            counter += 1
        yield{
            url: response.url
        }

    def getResultFile(self):
        # if results folder doesn't exist, create it
        if not os.path.exists(self.resultLocation):
            os.makedirs(self.resultLocation)
        ScratchSpider.documentCounter += 1   
        #create and return new json file
        f = open(self.resultLocation+'/'+self.documentPrefix+str(ScratchSpider.documentCounter)+".json", 'w')
        return f

