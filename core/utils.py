import os
import re
import random
import pickle
import hashlib
import aiohttp
from aiohttp_retry import RetryClient, ExponentialRetry
from src.tools.web_tools.markdownify import MarkdownConverter

from fake_useragent import UserAgent
from bs4 import BeautifulSoup
from bs4.element import Comment


FILEPATH = os.path.dirname(os.path.abspath(__file__))

# prevent caching
USER_AGENT_LIST = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.7; rv:11.0) Gecko/20100101 Firefox/11.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/72.0.3626.121 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:22.0) Gecko/20100 101 Firefox/22.0",
    "Mozilla/5.0 (Windows NT 6.1; rv:11.0) Gecko/20100101 Firefox/11.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_4) AppleWebKit/536.5 (KHTML, like Gecko) "
    "Chrome/19.0.1084.46 Safari/536.5",
    "Mozilla/5.0 (Windows; Windows NT 6.1) AppleWebKit/536.5 (KHTML, like Gecko) "
    "Chrome/19.0.1084.46 Safari/536.5",
]

statuses = {x for x in range(100, 600)}
statuses.remove(200)
statuses.remove(429)


def get_rand_user_agent():
    # user_agent = random.choice(USER_AGENT_LIST)
    # try:
    # user_agent = UserAgent().random
    # except:
    #    pass
    return user_agent
    

class CacheHandler:
    def __init__(self):
        self.cache = os.path.join(FILEPATH, "cache")
        engine_path = os.path.join(FILEPATH, "engines")
        if not os.path.exists(self.cache):
            os.makedirs(self.cache)
        enginelist = os.listdir(engine_path)
        self.engine_cache = {i[:-3]: os.path.join(self.cache, i[:-3]) for i in enginelist if i not in
                             ("__init__.py")}
        for cache in self.engine_cache.values():
            if not os.path.exists(cache):
                os.makedirs(cache)

    async def get_source(self, engine, url, headers, cache=True,
                        proxy=None, proxy_auth=None):
        """
        Retrieves source code of webpage from internet or from cache

        :rtype: str, bool
        :param engine: engine of the engine saving
        :type engine: str
        :param url: URL to pull source code from
        :type url: str
        :param headers: request headers to make use of
        :type headers: dict
        :param cache: use cache or not
        :type cache: bool
        :param proxy: proxy address to make use off
        :type proxy: str
        :param proxy_auth: (user, password) tuple to authenticate proxy
        :type proxy_auth: (str, str)
        """
        encodedUrl = url.encode("utf-8")
        urlhash = hashlib.sha256(encodedUrl).hexdigest()
        engine = engine.lower()
        cache_path = os.path.join(self.engine_cache[engine], urlhash)
        # load cache
        if os.path.exists(cache_path) and cache:
            with open(cache_path, 'rb') as stream:
                return pickle.load(stream), True

        get_vars = { 'url':url, 'headers':headers}
        if proxy:
            get_vars.update({'proxy':proxy})

        async with aiohttp.ClientSession() as client_session:
            # retry_client = RetryClient(client_session=client_session)
            async with client_session.get(**get_vars) as resp:
                html = await resp.text()
                # save to cache
                with open(cache_path, 'wb') as stream:
                    pickle.dump(str(html), stream)
            # await retry_client.close()
            return str(html), False


    def clear(self, engine=None):
        """
        Clear the entire cache either by engine name
        or just all

        :param engine: engine to clear
        """
        if not engine:
            for engine_cache in self.engine_cache.values():
                for root, dirs, files in os.walk(engine_cache):
                    for f in files:
                        os.remove(os.path.join(engine_cache, f))
        else:
            engine_cache = self.engine_cache[engine.lower()]
            for _, _, files in os.walk(engine_cache):
                for f in files:
                    os.remove(os.path.join(engine_cache, f))


def tag_visible(element):
    if element.parent.name in ['style', 'script', 'head', 'title', 'meta', '[document]']:
        return False
    if isinstance(element, Comment):
        return False
    return True


def text_from_soup(soup):
    # all:
    # return soup.body.get_text(' ', strip=True)

    # wiki:
    text = ""
    for paragraph in soup.find_all('p'):
        text += paragraph.text + "\n"

    return text


def post_processing(text):
    text = text.strip()

    # clean [1]...
    text = re.sub(r'\[[0-9]*\]',' ',text)

    # clean multiple space
    text = re.sub(r'\s+',' ',text)

    # replace newline
    for sp in ["\n", "\r", "\t"]:
        text = text.replace(sp, "\n")

    return text


blocked_sites = [
    "amazon.com",
    "amazon.cn",
    ".pdf",
    ".ppt",
    ".xlsx",
    ".cgi",
    ".csv",
    ".xls",
    "linkedin.com",
    "linkedin.cn",
    "youtube.com",
    "facebook.com",
    "bestbuy.com",
    "ncpc.gov",
    "thevogue.com",
    "arkansas.gov",
    "ancestorium.com",
    # "alachuacounty.us",
]

blocked_domains = ["www.google.io", "www.google.com.lc", "www.google.cn"]

def soup2md(soup, **options):
    return MarkdownConverter(autolinks=False, **options).convert_soup(soup)

