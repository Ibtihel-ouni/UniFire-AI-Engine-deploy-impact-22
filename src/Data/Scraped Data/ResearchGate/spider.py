from scrapy import Request
from requests_html import HTML
from util.helper import get_reference, parse, transform_number

import scrapy
import json
import os
import path as path


class PaperSpider(scrapy.Spider):
    name = 'paperspider'

    custom_settings = {
        'LOG_LEVEL': 'INFO',
        'DEPTH_LIMIT': 1,
        'DOWNLOAD_DELAY': 5,
    }

    def start_requests(self):
        yield scrapy.Request(self.url)

    def parse(self, response):
        follow_urls = set()

        paper_info = {
           'title': response.xpath(path.TITLE).get(),
           'url': response.url,
           'date': response.xpath(path.DATE).get(),
           'DOI': response.xpath(path.DOI).get(),
           'conference': response.xpath(path.CONFERENCE).get(),
           'citation count': transform_number(response.xpath(path.CITATIONS_COUNT).get()),
           'reference count': transform_number(response.xpath(path.REFERENCES_COUNT).get())
        }

        self.file_name = paper_info['title'].replace(" ","_")

        target_file = open(f'../output/{self.file_name}.json', 'w')
        target_file.write('{"result": ['+json.dumps(paper_info, indent=4)+',\n')
        target_file.close()

        publication_id = paper_info['url'][paper_info['url'].find("publication")+12:paper_info['url'].find("_")]
        request_token = response.xpath(path.RG_REQUEST_TOKEN).attrib['content']
        offset = 10

        if get_reference(token=request_token, uid=publication_id, offset=offset).status_code != 200:
            self.logger.info(f"response status {get_reference(uid=publication_id, offset=offset).status_code} instead of 200, possibly need to update cookies & token")

        while get_reference(token=request_token, uid=publication_id, offset=offset).status_code == 200:
            ref_response = get_reference(token=request_token, uid=publication_id, offset=offset)
            if (ref_response.text == ''):
                break
            html = HTML(html=ref_response.text)
            links = html.xpath(path.REFERENCES_LINK)
            if len(links) == 0:
                break
            for link in links:
                follow_urls.add(path.BASE_URL+link)
            offset = offset + 5

        for reference in response.xpath(path.REFERENCES):
            reference_link = path.BASE_URL+reference.xpath(path.REFERENCES_LINK).get() if reference.xpath(path.REFERENCES_LINK).get() is not None else ""
            if (reference_link != ''):
                follow_urls.add(reference_link)

        self.logger.info(f"total urls to follow: {len(follow_urls)}")

        for url in follow_urls:
            if url is not None:
                yield response.follow(url, self.reference_parse)

    def reference_parse(self, response):
        ref_info = {
            'reference title': response.xpath(path.TITLE).get(),
            'url': response.url,
            'date': response.xpath(path.DATE).get(),
            'DOI': response.xpath(path.DOI).get(),
            'conference': response.xpath(path.CONFERENCE).get(),
            'citation count': transform_number(response.xpath(path.CITATIONS_COUNT).get()),
        }

        target_file = open(f'../output/{self.file_name}.json', 'a')
        target_file.write(json.dumps(ref_info, indent=4)+',\n')
        target_file.close()

    def closed(self, reason):
        with open(f'../output/{self.file_name}.json', 'rb+') as target_file:
            target_file.seek(-1, os.SEEK_END)
            target_file.truncate()
            target_file.seek(-1, os.SEEK_END)
            target_file.truncate()
            target_file.close()

        target_file = open(f'../output/{self.file_name}.json', 'a')
        target_file.write(']}')
        target_file.close()

        parse(self.file_name)