import scrapy
import os
import re
import datetime
from bs4 import BeautifulSoup
from scrapy.exceptions import CloseSpider
from scrapy.spiders import Rule
from scrapy.linkextractors import LinkExtractor
import json


class ScratchSpider(scrapy.Spider):
    name = "scratch"
    documentCounter = 0
    # exclude social media, google and youtube
    linkExtract = LinkExtractor(deny=('twitter', 'facebook', 'linkedin', 'pinterest', 'google', 'youtube'))

    rules = (Rule(linkExtract,callback='parse'))
    
    def parse(self, response):
        # check time limit
        duration = (datetime.datetime.now() - self.timeStart)
        if duration.total_seconds() >= self.timeLimit:
            raise CloseSpider('Time limit reached')
        # stop if number of documents >= limit of number of docs
        if ScratchSpider.documentCounter >= self.docLimit:
            raise CloseSpider('Document limit reached')
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
        jsondump= {}
        jsondump['url'] = response.url
        jsondump['content'] = filteredContent
        # create new corpus files
        f = self.getResultFile()
        json.dump(jsondump, f)
        f.close()
        # insert next urls to crawl
        links = self.linkExtract.extract_links(response)
        for link in links:
             yield scrapy.Request(link.url, callback=self.parse)

    def getResultFile(self):
        # if results folder doesn't exist, create it
        if not os.path.exists(self.resultLocation):
            os.makedirs(self.resultLocation)
        ScratchSpider.documentCounter += 1   
        #create and return new json file
        f = open(self.resultLocation+'/'+self.documentPrefix+str(ScratchSpider.documentCounter)+".json", 'w')
        return f

