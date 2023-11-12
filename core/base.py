"""@desc
		Base class inherited by every search engine
"""

import os
import hashlib
import asyncio
import random
import pickle
import time
from urllib.parse import urljoin, parse_qs, unquote
from abc import ABCMeta, abstractmethod
from contextlib import suppress
from enum import Enum, unique
from urllib.parse import urlencode, urlparse

import aiohttp
from bs4 import BeautifulSoup

from src.tools.web_tools.core import utils
from src.tools.web_tools.core.exceptions import NoResultsOrTrafficError


def get_data(file_path):
    """Read data from file and output data in list format

    Args:
        file_path ([str]): file path
    """
    text_list = []
    with open(file_path, encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if line:
                text_list.append(line)
    return text_list

@unique
class ReturnType(Enum):
    FULL = "full"
    TITLE = "title"
    DESCRIPTION = "description"
    LINK = "link"

class BaseSearch:

    __metaclass__ = ABCMeta

    """
    Search base to be extended by search parsers
    Every subclass must have two methods `search` amd `parse_single_result`
    """
    # Summary of engine
    summary = None
    # Search Engine Name
    name = None
    # Search Engine unformatted URL
    search_url = None
    # The url after all query params have been set
    _parsed_url = None
    # boolean that indicates cache hit or miss
    _cache_hit = False
    
    def __init__(self, proxy=None):
        self.proxy = proxy
        self.page_cache_path = os.path.join(utils.FILEPATH, "cache/pages")
        self.domain_list = get_data(file_path=os.path.join(utils.FILEPATH, "data/all_domain.txt"))
        # remove blocked domains
        self.domain_list = list(set(self.domain_list) - set(utils.blocked_domains))
        self.agent_list = get_data(file_path=os.path.join(utils.FILEPATH, "data/user_agents.txt"))
        print("Number of domains: {}".format(len(self.domain_list)))

        if not os.path.exists(self.page_cache_path):
            os.makedirs(self.page_cache_path)

    @abstractmethod
    def parse_soup(self, soup):
        """
        Defines the results contained in a soup
        """
        raise NotImplementedError("subclasses must define method <parse_soup>")

    @abstractmethod
    def parse_single_result(self, single_result, return_type=ReturnType.FULL, **kwargs):
        """
        Every div/span containing a result is passed here to retrieve
        `title`, `link` and `descr`
        """
        raise NotImplementedError(
            "subclasses must define method <parse_results>")

    def get_cache_handler(self):
        """ Return Cache Handler to use"""

        return utils.CacheHandler()

    @property
    def cache_handler(self):
        return self.get_cache_handler()

    def parse_result(self, results, num_pages, **kwargs):
        """
        Runs every entry on the page through parse_single_result

        :param results: Result of main search to extract individual results
        :type results: list[`bs4.element.ResultSet`]
        :returns: dictionary. Containing lists of title, link, description and other possible\
            returns.
        :rtype: dict
        """
        search_results = []
        for each in results:
            # get at leat num_pages results
            if len(search_results) >= num_pages:
                break
            rdict = self.parse_single_result(each, **kwargs)
            if rdict is not None:
                search_results.append(rdict)
        return search_results

    def get_params(self, query=None, page=None, offset=None, **kwargs):
        """ This  function should be overwritten to return a dictionary of query params"""
        return {'q': query, 'page': page}

    def headers(self):
        headers = {
            "Cache-Control": 'no-cache',
            "Connection": "keep-alive",
            # "User-Agent": utils.get_rand_user_agent()
            "User-Agent": random.choice(self.agent_list),
        }
        return headers

    def clear_cache(self, all_cache=False):
        """
        Triggers the clear cache function for a particular engine

        :param all_cache: if True, deletes for all engines
        """
        if all_cache:
            return self.cache_handler.clear()
        return self.cache_handler.clear(self.name)

    async def get_source(self, url, cache=True):
        """
        Returns the source code of a webpage.
        Also sets the _cache_hit if cache was used

        :rtype: string
        :param url: URL to pull it's source code
        :param proxy: proxy address to make use off
        :type proxy: str
        :param proxy_auth: (user, password) tuple to authenticate proxy
        :type proxy_auth: (str, str)
        :return: html source code of a given URL.
        """
        # get random headers

        # try:
        html, cache_hit = None, False
        for i in range(1, 4):
            try:
                html, cache_hit = await self.cache_handler.get_source(self.name, url, self.headers(), cache, self.proxy)
                if html:
                    break
            except BaseException as e: # jump wrong case
                print(">" * 30, "exception:", e)
                print("URL:", url)
                print("Try again...")
                time.sleep(i)

        # except:
        if not html:
            print(">" * 10, "failed to scrape `{}`".format(url))
            print("html", html)

        self._cache_hit = cache_hit
        return html

    async def get_soup(self, url, cache):
        """
        Get the html soup of a query
        :param url: url to obrain soup from
        :type url: str
        :param cache: cache request or not
        :type cache: bool
        :param proxy: proxy address to make use off
        :type proxy: str
        :param proxy_auth: (user, password) tuple to authenticate proxy
        :type proxy_auth: (str, str)

        :rtype: `bs4.element.ResultSet`
        """
        html = await self.get_source(url, cache)
        return BeautifulSoup(html, 'lxml') if html else None

    def get_search_url(self, query=None, page=None, **kwargs):
        """
        Return a formatted search url
        """
        # Some URLs use offsets
        offset = (page * 10) - 9

        params = self.get_params(query=query, page=page, offset=offset, **kwargs)
        base_url = "https://" + random.choice(self.domain_list)
        # base_url = "https://www.google.com/"
        search_url = urljoin(base_url, "search")
        url = urlparse(search_url)
        # For localization purposes, custom urls can be parsed for the same engine
        # such as google.de and google.com

        if kwargs.get("url"):
            new_url = urlparse(kwargs.pop("url"))
            # When passing url without scheme e.g google.de, url is parsed as path
            if not new_url.netloc:
                url = url._replace(netloc=new_url.path)
            else:
                url = url._replace(netloc=new_url.netloc)
            self.base_url = url.geturl()

        self._parsed_url = url._replace(query=urlencode(params))

        # print(self._parsed_url.geturl())
        # exit()

        return self._parsed_url.geturl()

    def get_results(self, soup, **kwargs):
        """ Get results from soup"""

        results = self.parse_soup(soup)

        if not results:
            print(">" * 10 + "ENGINE FAILURE: {}\n".format(self.name))
            return [{"title": None, "page": None}]
            # raise NoResultsOrTrafficError(
            #     "The result parsing was unsuccessful. It is either your query could not be found"
            #     " or it was flagged as unusual traffic")

        search_results = self.parse_result(results, **kwargs)
        return search_results

    def search(self, query=None, page=1, retry=1, cache=True, page_cache=True, topk=1, end_year=None, **kwargs):
        """
        Query the search engine
        """
        self.end_year = end_year
        # Pages can only be from 1-N

        # load cache
        encoded_query = query.encode("utf-8")
        query_hash = hashlib.sha256(encoded_query).hexdigest()
        cache_path = os.path.join(self.page_cache_path, query_hash)

        if page_cache and os.path.exists(cache_path):
            with open(cache_path, 'rb') as stream:
                search_results = list(pickle.load(stream))
                if isinstance(search_results, list) and len(search_results) >= topk and \
                    isinstance(search_results[topk-1], dict) and isinstance(search_results[topk-1]['page'], str):
                    print(">>> Using Page Cache")
                    return search_results[topk-1]

        if page <= 0:
            page = 1

        # Get search Page Results
        loop = asyncio.get_event_loop()

        # construct url
        url = self.get_search_url(
                    query, page, **kwargs)

        soup = loop.run_until_complete(
            self.get_soup(url, cache=cache))

        res = self.get_results(soup, num_pages=topk, **kwargs)

        # retry
        if retry and ((len(res) < topk or not res[topk-1]["page"]) or isinstance(res[topk-1]["page"], list)):
            print("Failed url: {}".format(url))
            print("Retrying without loading cache {} ...".format(retry))
            return self.search(query, page, retry - 1, cache=False, page_cache=page_cache, topk=topk, end_year=end_year)

        if len(res) < topk:
            return {"page": "No evidence found, please change query."}
       
        # save cache
        if res[topk-1]["page"]:
            with open(cache_path, 'wb') as stream:
                pickle.dump(tuple(res), stream)

        return res[topk - 1]
    

    async def async_search(self, query=None, page=1, cache=True, **kwargs):
        """
        Query the search engine but in async mode

        :param query: the query to search for
        :type query: str
        :param page: Page to be displayed, defaults to 1
        :type page: int
        :param proxy: proxy address to make use off
        :type proxy: str
        :param proxy_auth: (user, password) tuple to authenticate proxy
        :type proxy_auth: (str, str)
        :return: dictionary. Containing title, link, netlocs and description.
        """
        # Pages can only be from 1-N
        if page == 0:
            page = 1
        soup = await self.get_soup(self.get_search_url(query, page, **kwargs), cache=cache)
        return self.get_results(soup, **kwargs)
