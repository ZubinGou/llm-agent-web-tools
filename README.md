
# LLM-Agent Web Tools

> Repo for web search tools of the paper [CRITIC: Large Language Models Can Self-Correct with Tool-Interactive Critiquing](https://openreview.net/forum?id=Sx038qxjek) [ICLR'24], main repo at [CRITIC](https://github.com/microsoft/ProphetNet/tree/master/CRITIC).


Supported web tools:

- Google
- Bing
- Baidu
- Goolge Scholar
- DuckDuckGo
- GitHub
- StackOverflow
- Baidu
- YouTube
- ...


## Caching Mechanism for Replicability of CRITIC Paper
 
We build a caching system specifically designed for web searches. This system archives all API queries that are generated via greedy decoding for each model and evaluation sample, as well as their corresponding search outcomes. This approach ensures stability, fairness, and reproducibility in the results of CRITIC.


## Usage

```python
from src.tools.web_tools.core.engines.google import Search as GoogleSearch

# init a search engine
gsearch = GoogleSearch(proxy=None)

# will automatically parse Google and corresponding web pages
gresults = gsearch.search(query, cache=True, page_cache=True, topk=1, end_year=2024)

print(gresults)
```


## References

- Developed based on [search-engine-parser](https://github.com/bisohns/search-engine-parser). 
- We use [markdownify](https://pypi.org/project/markdownify/) to parse tables.
- We use [fuzzysearch](https://github.com/taleinat/fuzzysearch) to fuzzy-match the web page with the Google Snippet.

