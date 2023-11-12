"""@desc
		Parser for google search results
"""
import sys
import asyncio
import re
from urllib.parse import (
    urljoin,
    parse_qs,
    unquote
)
import urllib.parse as urlparse
from fuzzysearch import find_near_matches

from src.tools.web_tools.core.base import BaseSearch, ReturnType
from src.tools.web_tools.core.utils import text_from_soup, post_processing, blocked_sites, soup2md


EXTRA_PARAMS = ('hl', 'tbs')


class Search(BaseSearch):
    """
    Searches Google for string
    """
    name = "Google"
    base_url = "https://www.google.com/"
    summary = "\tNo need for further introductions. The search engine giant holds the first "\
        "place in search with a stunning difference of 65% from second in place Bing.\n"\
        "\tAccording to the latest netmarketshare report (November 2018) 73% of searches "\
        "were powered by Google and only 7.91% by Bing.\n\tGoogle is also dominating the "\
        "mobile/tablet search engine market share with 81%!"

    def __init__(self, verbose=False, proxy=None):
        super(Search, self).__init__(proxy)

        # self.domain_list = get_data(file_path=DOMAIN_PATH)
        # self.ua_list = get_data(file_path=self.config.UA_PATH)
        # self.proxies = random.choice(proxies) if proxies else None

        # self.search_url = urljoin(self.base_url, "search")
        self.page_type = 1 # type in [1, 2]
        self.verbose = verbose
        self.end_year = None

    def get_params(self, query=None, offset=None, page=None, **kwargs):
        params = {}
        params["q"] = query
        params["gl"] = "US"
        if self.end_year:
            params['tbs']="cdr:1,cd_min:,cd_max:{}".format(self.end_year)
        # additional parameters will be considered
        for param in EXTRA_PARAMS:
            if kwargs.get(param):
                params[param] = kwargs[param]
        return params

    def parse_url(self, url):
        return self.clean_url(urljoin(self.base_url, url))

    def parse_soup(self, soup):
        """
        Parses Google Search Soup for results
        """
        # find all class_='g' => each result
        if self.verbose:
            print(soup.prettify())

        # first type of google page
        self.page_type = 1
        res = soup.find_all('div', {'class': ["Gx5Zad xpd EtOod pkphOe", "Gx5Zad fP1Qef xpd EtOod pkphOe"]})

        # second type of google page
        if len(res) == 0:
            self.page_type = 2
            res = soup.find_all('div', class_="ezO2md")
        return res

    def parse_single_result(self, single_result, return_type=ReturnType.FULL, **kwargs):
        """
        Parses the source code to return

        :param single_result: single result found in <div class="g">
        :type single_result: `bs4.element.ResultSet`
        :return: parsed title, link and description of single result
        :rtype: dict
        """
        # Some unneeded details shown such as suggestions should be ignore
        if (single_result.find("h2", class_="wITvVb") and single_result.find("div", class_="LKSyXe"))\
                or single_result.find("div", {"class": ["BmP5tf"]}) or single_result.find("span", class_="qXLe6d x3G5ab") \
                or single_result.find("span", class_="C7GS5b rkGIWe"):
            return

        results = dict()

        # remove time span
        for item in single_result.find_all("span", {'class': ['r0bn4c rQMQod', 'fYyStc YVIcad']}): 
            item.decompose()
        for item in single_result.find_all("sub", {'class': ['gMUaMb r0bn4c rQMQod']}):
            item.decompose()

        # remove image
        for item in single_result.find_all("div", {'class': ['synv3b']}): 
            item.decompose()
        for item in single_result.find_all("img"):
            item.decompose()

        if self.verbose:
            print("Single_result:", single_result.prettify())

        def get_title(title_tag):
            title = title_tag.get_text('...', strip=True)
            title_list = [d for d in title.split("...") if '›' not in d]
            title = "...".join(title_list)
            return title

        # type 1 & 2
        if self.page_type == 1:

            els = single_result.find_all('div', class_='kCrYT', recursive=True)

            if len(els) < 1:
                return

            if len(els) == 1:
                title_elem = None
                results['title'] = ""
            else:
                if self.verbose:
                    print("els[0]:", els[0].prettify())
                    print("els[1]:", els[1].prettify())

                # First div contains title and url
                title_elem, desc_elem = els[0], els[1]

                # title
                if return_type in (ReturnType.FULL, ReturnType.TITLE):
                    title_tag = title_elem.find('h3')
                    if not title_tag:
                        title_tag = title_elem.find('h2')
                    if not title_tag:
                        title_elem, desc_elem = els[1], els[0]
                        title_tag = title_elem.find('div', class_='BNeawe')

                    results['title'] = get_title(title_tag) if title_tag else ""

                # link
                if return_type in (ReturnType.FULL, ReturnType.LINK):
                    link_tag = title_elem.find('a')
                    if link_tag:
                        raw_link = link_tag.get('href')
                        raw_url = urljoin(self.base_url, raw_link)
                        results['raw_url'] = raw_url
                        results['link'] = self.clean_url(raw_url)

                # link & description
                if return_type in (ReturnType.FULL, ReturnType.DESCRIPTION):

                    desc = desc_elem.get_text(" ", strip=True)
                    for el in els[2:]:
                        desc += "...\n" + el.get_text(" ", strip=True)
                    desc_list = [d for d in desc.split("...") if len(d) > 10]
                    desc = "...".join(desc_list).strip()

                    results['description'] = desc

        elif self.page_type == 2:
            title_elem = single_result.find_all('a', class_='fuLhoc ZWRArf')
            desc_elem = single_result.find_all('span', class_='qXLe6d FrIlee')
            if len(title_elem) < 1 or len(desc_elem) < 1:
                results['title'] = ""
                results['description'] = single_result.get_text(" ", strip=True)
            else:
                # title & link
                results['title'] = get_title(title_elem[0])
                raw_link = title_elem[0].get('href')
                raw_url = urljoin(self.base_url, raw_link)
                results['raw_url'] = raw_url
                results['link'] = self.clean_url(raw_url)

                # description
                results['description'] = desc_elem[0].text.strip()

        # get pages, only keep those matched page 
        for site in blocked_sites:
            if site in results.get('link', ""):
                return

        # if results['link']:
        results['page'] = self.parse_page(results.get('link', ""), results.get('description', ""))

        if self.verbose:
            print("title:", results.get('title', ""))
        
        # if no page: return description
        if not results['page']:
            # get all description
            if self.page_type == 1:
                els = single_result.find_all('div', class_=['kCrYT', 'CgE3Ac', 'X7NTVe'], recursive=True)
                all_desc = []
                for el in els:
                    if el == title_elem:
                        continue
                    elif el['class'][0] == 'CgE3Ac':
                        # parse table
                        desc = soup2md(el).strip()
                        if len(all_desc) == 0:
                            desc = "\n" + desc
                    else:
                        desc = el.get_text(' ', strip=True)
                        desc_list = [d for d in desc.split("...")]
                        desc = "...".join(desc_list)
                        desc = desc.replace("\n", " ").strip()
                    all_desc.append(desc)
                    if self.verbose:
                        print(">" * 20)
                        print(el.prettify())
                        print(desc)
                results['page'] = "\n".join(all_desc)
            else:
                results['page'] = results['description']
        
        if len(results['page']) < 10:
            return

        return results

    def get_match_spans(self, src_text, match_parts):
        match_spans = []
        for part in match_parts:
            matchs = find_near_matches(part, src_text, max_l_dist=int(0.1 * len(part))) # fuzzy match
            if len(matchs) > 0:
                match = matchs[0]

                stop_char = "\n\t.}"
                # forward extent to a stop
                ind = next((i for i, ch in enumerate(src_text[match.end - 1:]) if ch in stop_char), None)
                end_idx = match.end + ind if ind else match.end

                start_idx = match.start
                # backward extend to a stop
                src_text = "." + src_text
                ind = next((i for i, ch in enumerate(src_text[:match.start + 1][::-1]) if ch in stop_char), None)
                start_idx = match.start - ind

                match_spans.append([start_idx, end_idx])
        return match_spans

 
    def parse_page(self, url, desc):
        if not url or not desc:
            return

        if self.verbose:
            print("-" * 10)
            print("Get page: {}".format(url))
        loop = asyncio.get_event_loop()
        soup = loop.run_until_complete(
            self.get_soup(url, cache=True))

        if not soup or not soup.body:
            return

        MAX_TEXT_LEN = 10000
        text = text_from_soup(soup)
        text = post_processing(text)[:MAX_TEXT_LEN]

        if self.verbose:
            print("text:", text[:4000])
            print("desc:", desc)
            print("len(text)={}, matching...".format(len(text)))

        if len(desc.strip()) < 30:
            return
 
        desc_parts = [p for p in desc.split("...") if len(p) > 25]

        match_spans = self.get_match_spans(text, desc_parts)
        match_spans = sorted(match_spans)
        if self.verbose:
            print("match_spans:", match_spans)

        # if not match, replace parentheses then match again
        if len(match_spans) == 0:
            text = re.sub("[\(\[].*?[\)\]]", "", text)
            match_spans = self.get_match_spans(text, desc_parts)
        
        # merge spans
        if len(match_spans) == 0:
            match_str = ""
        else:
            # merge spans
            merged_spans = []
            last_end_idx = -1
            for span in  match_spans:
                if span[0] <= last_end_idx:
                    merged_spans[-1][-1] = span[1]
                else:
                    merged_spans.append(span)
            # span idx -> span text
            spans_str = []
            for span in merged_spans:
                spans_str.append(text[span[0]: span[1]])
            match_str = "...".join(spans_str)
            
        # post-processing: replace multiple spaces / special chars
        match_str = post_processing(match_str)

        if self.verbose:
            print("Match:", match_str)
        return match_str

    def clean_url(self, url):
        """
        Extract clean URL from the SERP URL.

        >clean_url('https://www.google.com/url?q=https://english.stackexchange.com/questions/140710/what-is-the-opposite-of-preaching-to-the-choir&sa=U&ved=2ahUKEwi31MGyzvnuAhXyyDgGHXXACOYQFnoECAkQAg&usg=AOvVaw1GdXON-JIWGu-dGjHfgljl')
        https://english.stackexchange.com/questions/140710/what-is-the-opposite-of-preaching-to-the-choir
        """
        parsed = urlparse.urlparse(url)
        url_qs = parse_qs(parsed.query)
        if 'q' in url_qs:
            return unquote(url_qs['q'][0])
        elif 'url' in url_qs:
            return unquote(url_qs['url'][0])
        # Add more cases here.
        return url
