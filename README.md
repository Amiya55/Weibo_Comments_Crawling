## Weibo_Comments_Crawling  
Python微博热搜评论抓取以及情感分析工具

### 基本类  
```Python
# 热搜相关数据，包括热搜主题，热搜的url
# 这个类主要是配合下面的DataCrawling类，不单独使用
class HotSearchData:
    def __init__(self, title: str, url:str) -> None:
        self._title = title
        self._url = url
```
```Python
# 评论数据存储类，包括评论文本和对应楼的楼中评
class CommentData:
    def __init__(self, text: str, sub_comments: list[str]) -> None:
        self._text = text
        self._sub_comments = []  # 这个是针对本评论的楼中评
```
```Python
# 数据爬取核心类
class DataCrawling:
    def __init__(self) -> None:
        # 加载headers和cookies，注意: cookies有时效性，过期之后需要手动更新config.json配置文件
        config: dict = json.load(open('config.json'))
        self._headers: dict = config['headers']

        self._cookies: dict = {}
        for cookie in config['cookies'].split(';'):
            name, value = cookie.split('=', 1)
            self._cookies[name.strip()] = value.strip()

        # 微博热搜热榜(容量为51，包含一个榜首和其他50个热搜)
        self._hot_searches: list[HotSearchData] = []
```
### 函数接口与使用方法(DataCrawling类)  
```Python
def get_hot_searches_list(self) -> list[str]:
    pass
# 获取当前微博的热搜，获取量为热搜榜前51，包括一个置顶榜和50个热搜榜
# 这个数字可能在50-52之间波动，这与微博本身有关
```
```Python
def get_hot_search_comments(self, start: int, end: int, scale: int = 1) -> dict[str: list[CommentData]]:
    """
    获取在总榜排名start到end范围内的热搜的评论
    :param start: 起始排名，1 <= start <= len(self._hot_searches)
    :param end: 最后排名，1 <= end <= len(self._hot_searches)
    :param scale: 搜索的web页计数，数字越大，查找的信息越多
    :return: 一个包含目标热搜所有评论的字典，key为热搜名，value为评论的列表
    """
    pass
# 获取微博热搜榜排名start到end之间的所有帖子的评论，可以指定搜索量scale，搜索量越大
# 查找的数据越多，注意，scale过大可能导致搜索相关性降低
```
```Python
def get_comments_via_keyword(self, keyword: str, scale: int = 1) -> list[CommentData]:
    """
    通过关键词搜索查找评论
    :param keyword: 关键词
    :param scale: 搜索规模，这个值越大就搜多到的结果越多，当然，不能无限大，超过临界值，搜索的信息量不再增加
    :return: 评论的数组
    """
    pass
# 通过关键词查找搜索web界面，获取评论，代码逻辑和索取热搜榜评论类似，只不过提供了
# 参数来传递你指定的关键字，比如说我要搜索doro，搜索Python，C++，搜索为什么空腹不能吃饭，都是可以的
```

### 注意  
1、爬虫程序需要进行浏览器伪装, 本程序未提供User-Agent以及网页cookies，这类信息请自行查找并按照本目录下的config.json文件中的示例添加到文件中  
2、获取cookies前请确保你已经登陆微博  
3、爬虫程序都有一定的时效性，如果无法爬取信息，请尝试更新cookies。如果无法解决，请自行对网页抓包进行分析，如果确定本程序失效，请停止使用

