import requests
import json
import re
import time
from urllib.parse import urlparse, parse_qs

class HotSearchData:
    def __init__(self, title: str, url:str) -> None:
        self._title = title
        self._url = url

    def get_title(self) -> str:
        return self._title

    def get_url(self) -> str:
        return self._url

class CommentData:
    def __init__(self, text: str, like_count: int, sub_comments: list[str]) -> None:
        self._text = text
        self._like_count = like_count
        self._sub_comments = []  # 这个是针对本评论的楼中评

    def get_text(self) -> str:
        return self._text

    def get_like_count(self) -> int:
        return self._like_count

    def get_sub_comments(self) -> list:
        return self._sub_comments

class DataCrawling:
    def __init__(self) -> None:
        # 加载headers和cookies，注意: cookies有时效性，过期之后需要手动更新config.json配置文件
        config: dict = json.load(open('config.json'))
        self._headers: dict = config['headers']

        self._cookies: dict = {}
        for cookie in config['cookies'].split(';'):
            name, value = cookie.split('=')
            self._cookies[name.strip()] = value.strip()

        # 微博热搜热榜
        self._hot_searches: list[HotSearchData] = []
        # 微博热搜总榜
        # self._overall_hot_search_list: list[HotSearchData] = []

    def get_hot_search_comments(self, top_k: int = 9) -> dict[str: list[CommentData]]:
        """
        获取所有热搜评论
        :param top_k: 指定获取热搜前几名，注意: 这个值最大为9。至于为什么，我没有做...
        :return: 返回一个字典，key为热搜名，value为所有评论组成的的列表
        """
        if top_k <= 0 or top_k > 9:
            print('只能指定1-9范围内的数字作为热搜排名')
            return {}

        hot_search_url: str = r'https://m.weibo.cn/api/container/getIndex?containerid=231583&page_type=searchall'
        self._get_hot_search(hot_search_url)  # 获取微博热搜榜前九名

        ret: dict[str: list[CommentData]] = {}
        for i in range(top_k):
            comments: list[CommentData] = self._get_comments(self._hot_searches[i].get_url())  # 获取话题评论
            ret[self._hot_searches[i].get_title()] = comments

        return ret

    def get_comments_via_keyword(self, keyword: str) -> list[str]:
        pass

    def _get_hot_search(self, url: str) -> None:
        responses = requests.get(url, headers = self._headers, cookies = self._cookies)
        data: dict = json.loads(responses.text)

        for hot_search in data['data']['cards'][0]['group']:
            title: str = hot_search['title_sub']
            url: str = hot_search['scheme']
            self._hot_searches.append(HotSearchData(title, url))

    def _get_comments(self, hot_search_url: str) -> list[CommentData]:
        # 获取该板块下的帖子ID
        parsed = urlparse(hot_search_url)   # URL解析
        # base_url: str = f'{parsed.scheme}://{parsed.netloc}'
        query_params: dict = parse_qs(parsed.query)
        query_params.update({'page_type': 'searchall'})

        responses = requests.get('https://m.weibo.cn/api/container/getIndex', headers = self._headers, params = query_params, cookies = self._cookies)
        if responses.status_code != 200:
            print(f'failed to get from {responses.url}, status code: {responses.status_code}')
            return []

        data: dict = json.loads(responses.text)  # 加载Json字符串

        posts: list = data['data']['cards']  # 获取热搜帖子条目
        post_ids: list = [posts[i]['mblog']['id'] for i in range(posts.__len__()) if posts[i]['card_type'] == 9]  # 获取帖子ID

        # 通过上面获取的帖子ID爬评论
        comments: list[CommentData] = []
        for post_id in post_ids:
            comment_base_url: str = 'https://m.weibo.cn/comments/hotflow'  # 帖子评论基础URL
            params: dict = {
                'id': post_id,
                'mid': post_id,
                'max_id_type': 0
            }

            first: bool = True
            max_id: int = 0
            while first or max_id:
                first = False
                comments_responses = requests.get(comment_base_url, headers = self._headers, params = params, cookies = self._cookies)
                if comments_responses.status_code != 200:
                    print(f'failed to get from {comment_base_url}, status code: {comments_responses.status_code}')
                    return []

                print(comments_responses.url)
                comments_data: dict = json.loads(comments_responses.text)
                if comments_data['ok'] == 1:
                    for comment in comments_data['data']['data']:
                        pattern = '<(span.+?</span|a.+?</a)>'  # 正则去除超链接和图片表情
                        text: str = re.sub(pattern, "", comment['text'])

                        # 获取楼中评
                        sub_comments = []
                        if comment['comments']:
                            for cms in comment['comments']:
                                sub_comments.append(re.sub(pattern, "", cms['text']))

                        like_count: int = comment['like_count']
                        comments.append(CommentData(text, like_count, sub_comments))

                    max_id = comments_data['data']['max_id']
                    params.update({'max_id': max_id})

                    time.sleep(1)  # 降低请求频次，你也不想被ban了吧
                else:
                    break

            if max_id == 0 and 'max_id' in params:
                del params['max_id']

        return comments

if __name__ == '__main__':
    comment_dict: dict[str: list[CommentData]] =  DataCrawling().get_hot_search_comments(4)
    for key in comment_dict.keys():
        with open(f'output/{key}.txt', 'w', encoding='utf-8') as file:
            for c in comment_dict[key]:
                file.write(f'{c.get_text()} 点赞: {c.get_like_count()}\n')
                if c.get_sub_comments():
                    for scms in c.get_sub_comments():
                        file.write(f'\t{scms}\n')
            file.close()