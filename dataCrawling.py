"""
author: 穗喵喵喵喵
created at: 2025-06-02
last update: 2025-06-04

description: 本程序为对微博评论进行抓取的爬虫
version: 1.0

functions: 1、获取当前微博热搜榜前51名的信息(数字在50-52间波动)  get_hot_searches_list
           2、获取指定热榜搜索帖子的评论  get_hot_search_comments
           3、获取通过指定关键词搜索帖子的评论  get_comments_via_keyword

notice: 1、爬虫程序需要进行浏览器伪装, 本程序未提供User-Agent以及网页cookies，这类信息请自行
        查找并按照本目录下的config.json文件中的示例添加到文件中
        2、获取cookies前请确保你已经登陆微博
        3、爬虫程序都有一定的时效性，如果无法爬取信息，请尝试更新cookies。如果无法解决
        请自行对网页抓包进行分析，如果确定本程序失效，请停止使用
"""

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
    def __init__(self, text: str, sub_comments: list[str]) -> None:
        self._text = text
        self._sub_comments = []  # 这个是针对本评论的楼中评

    def get_text(self) -> str:
        return self._text

    def get_sub_comments(self) -> list:
        return self._sub_comments

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

    def get_hot_searches_list(self) -> list[str]:
        """获取微博热搜总榜"""
        url_sim: str = 'https://m.weibo.cn/api/container/getIndex?containerid=231583'  # 热搜榜简化版，通过这个入口找到总榜
        response_sim = requests.get(url_sim, headers = self._headers, cookies = self._cookies)
        if response_sim.status_code != 200:
            print(f'cannot get simple hot searches list, status code: {response_sim.status_code}')
            return []

        data_sim: dict = json.loads(response_sim.text)

        entrance: str = ''  # 总榜入口
        for search_sim in data_sim['data']['cards'][0]['group']:
            if search_sim['title_sub'] == '微博热搜榜':
                entrance = search_sim['scheme']

        # 我们需要提取url中的参数
        parsed = urlparse(entrance)
        params: dict = parse_qs(parsed.query)

        # 通过上面获取的总榜入口查询总榜
        base_url: str = 'https://m.weibo.cn/api/container/getIndex'
        responses = requests.get(base_url, headers = self._headers, cookies = self._cookies, params = params)
        if responses.status_code != 200:
            print(f'cannot get hot searches list, status code: {responses.status_code}')
            return []

        data: dict = json.loads(responses.text)
        # with open('data.json', 'w', encoding='utf-8') as f:
        #     json.dump(data, f, ensure_ascii=False, indent=4)
        #     f.close()

        for search in data['data']['cards'][0]['card_group']:
            self._hot_searches.append(HotSearchData(search['desc'], search['scheme']))

        return [s.get_title() for s in self._hot_searches]  # 只返回标题，不返回url

    def get_hot_search_comments(self, start: int, end: int, scale: int = 1) -> dict[str: list[CommentData]]:
        """
        获取在总榜排名start到end范围内的热搜的评论
        :param start: 起始排名，1 <= start <= len(self._hot_searches)
        :param end: 最后排名，1 <= end <= len(self._hot_searches)
        :param scale: 搜索的web页计数，数字越大，查找的信息越多
        :return: 一个包含目标热搜所有评论的字典，key为热搜名，value为评论的列表
        """
        if scale < 1:
            print(f'scale参数只能是大于0的数字, 你当前的数字: {scale}')
            return {}
        if ((start < 0 or start > len(self._hot_searches)) or
            (end < 0 or end > len(self._hot_searches)) or
            (start > end)):
            print(f'只能指定0-{len(self._hot_searches) - 1}范围内的数字作为热搜排名')
            return {}

        ret: dict[str: list[CommentData]] = {}
        for index in range(start, end + 1):
            # 获取对应的url板块下的所有帖子的id
            parsed = urlparse(self._hot_searches[index].get_url())  # URL解析
            query_params: dict = parse_qs(parsed.query)
            query_params.update({'page_type': 'searchall', 'page': 1})
            query_params['type'] = 60  # 切换为'热门'板块

            base_url: str = 'https://m.weibo.cn/api/container/getIndex'
            while query_params['page'] < scale:
                responses = requests.get(base_url, headers=self._headers, params=query_params, cookies=self._cookies)
                if responses.status_code != 200:
                    print(f'failed to get from {responses.url}, status code: {responses.status_code}')
                    return []

                data: dict = json.loads(responses.text)  # 加载Json字符串
                if data['ok'] == 0:
                    break

                posts: list = data['data']['cards']  # 获取热搜帖子条目
                post_ids: list = [posts[i]['mblog']['id'] for i in range(len(posts)) if
                                  posts[i]['card_type'] == 9]  # 获取帖子ID

                comments: list[CommentData] = self._get_comments(post_ids)  # 获取话题评论
                if self._hot_searches[index].get_title() in ret:
                    ret[self._hot_searches[index].get_title()].extend(comments)
                else:
                    ret[self._hot_searches[index].get_title()] = comments

                query_params['page'] += 1

        return ret

    def get_comments_via_keyword(self, keyword: str, scale: int = 1) -> list[CommentData]:
        """
        通过关键词搜索查找评论
        :param keyword: 关键词
        :param scale: 搜索规模，这个值越大就搜多到的结果越多，当然，不能无限大，超过临界值，搜索的信息量不再增加
        :return: 评论的数组
        """
        if scale < 1:
            print(f'scale参数只能是大于0的数字, 你当前的数字: {scale}')
            return []

        base_url: str = 'https://m.weibo.cn/api/container/getIndex'

        params_via_keyword: dict = {
            'containerid': f'100103type=60&q={keyword}',
            'page_type': 'searchall',
            'page': 1
        }

        post_ids: list[int] = []  # 查找到的帖子ID
        while params_via_keyword['page'] <= scale:
            responses = requests.get(base_url, headers = self._headers, cookies = self._cookies, params = params_via_keyword)
            if responses.status_code != 200:
                print(f'cannot get hot searches list, status code: {responses.status_code}')
                return []

            data: dict = json.loads(responses.text)  # 加载Json字符串
            if data['ok'] == 0:  #   ok值为0, 说明到达了临界值, 跳出循环，直接开始查找评论
                break

            with open('data.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
                f.close()

            posts: list = data['data']['cards']  # 获取热搜帖子条目
            tmp: list = [posts[i]['mblog']['id'] for i in range(len(posts)) if
                              posts[i]['card_type'] == 9]  # 获取帖子ID
            post_ids.extend(tmp)

            params_via_keyword['page'] += 1  # 增加web页计数

        return self._get_comments(post_ids)  # 获取话题评论

    def _get_comments(self, post_ids: list[int]) -> list[CommentData]:
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
                        comments.append(CommentData(text, sub_comments))

                    max_id = comments_data['data']['max_id']
                    params.update({'max_id': max_id})

                    time.sleep(1)  # 降低请求频次，你也不想被ban了吧
                else:
                    break

            if max_id == 0 and 'max_id' in params:
                del params['max_id']

        return comments

if __name__ == '__main__':
    obj = DataCrawling()
    for i, v in enumerate(obj.get_hot_searches_list(), 1):
        print(f'{i}: {v}')

    # comment_dict: dict[str: list[CommentData]] =  obj.get_hot_search_comments(1, 1, 2)
    # for key in comment_dict.keys():
    #     with open(f'output/{key}.txt', 'w', encoding='utf-8') as file:
    #         for c in comment_dict[key]:
    #             file.write(f'{c.get_text()}\n')
    #             if c.get_sub_comments():
    #                 for scms in c.get_sub_comments():
    #                     file.write(f'\t{scms}\n')
    #         file.close()

    coms:list[CommentData] = obj.get_comments_via_keyword('doro', 10)
    with open('output/doro.txt', 'w', encoding='utf-8') as f:
        for i in coms:
            f.write(f'{i.get_text()}\n')
            if i.get_sub_comments():
                for sub in i.get_sub_comments():
                    f.write(f'{sub}\n')
        f.close()