"""
 	@author
        Anonymous authors of ICLR'24 submission (CRITIC)
 		Email: xxx@gmail.com
 		Github: https://github.com/xxx
 		GitLab: https://gitlab.com/xxx

 	@project
 		@create date xxx
 		@modify date xxx

	@license
		MIT License
		Copyright (c) 2023. Anonymous authors. All rights reserved
        Do not distribute.
"""

from src.tools.web_tools.core import engines
from src.tools.web_tools.core.engines.aol import Search as AolSearch
from src.tools.web_tools.core.engines.ask import Search as AskSearch
from src.tools.web_tools.core.engines.baidu import Search as BaiduSearch
from src.tools.web_tools.core.engines.bing import Search as BingSearch
from src.tools.web_tools.core.engines.github import Search as GithubSearch
from src.tools.web_tools.core.engines.google import Search as GoogleSearch
from src.tools.web_tools.core.engines.googlescholar import \
    Search as GoogleScholarSearch
from src.tools.web_tools.core.engines.stackoverflow import \
    Search as StackOverflowSearch

name = "llm-agent-web-tools"  # pylint: disable=invalid-name
__version__ = "0.2.1"
