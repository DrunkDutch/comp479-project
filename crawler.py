import subprocess
import json
import scrapy
import datetime
from scrapy.crawler import CrawlerProcess
from spiders.scratch import ScratchSpider

# Get properties file
fCrawlerProperties = open("crawlerProperties.json", 'r')
properties = json.loads(fCrawlerProperties.read())

spiderStartUrl = properties['spiderStartUrl']
spiderResultLocation = properties['spiderResult']
spiderDocumentPrefix = properties['spiderDocumentPrefix']
spiderDocumentLimit = properties['spiderDocumentFetchLimit']
spiderTimeOut = properties['spiderTimeOut']

# Create crawler process with robot elimination enabled
process = CrawlerProcess({
    'ROBOTSTXT_OBEY': True 
})
#start crawl
process.crawl(ScratchSpider, 
    start_urls=spiderStartUrl, 
    resultLocation=spiderResultLocation, 
    documentPrefix=spiderDocumentPrefix, 
    docLimit=spiderDocumentLimit, 
    timeLimit=spiderTimeOut, 
    timeStart=datetime.datetime.now()
)
process.start()


