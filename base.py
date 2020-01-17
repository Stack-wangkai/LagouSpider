# -*- coding:utf-8 -*-
import json
import requests
import random
import os

DIR = os.path.dirname(os.path.abspath(__name__))


class Spider(object):
    '''
    顶级父类，提供爬取各大招聘网站公开职位的抽象方法和若公共方法，请继承并重写其中逻辑！
    '''
    domain = u""
    url = u""
    user_agent = [
        u"Mozilla/5.0 (Macintosh; Intel Mac OS X 10.6; rv:2.0.1) Gecko/20100101 Firefox/4.0.1",
        u"Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_6_8; en-us) AppleWebKit/534.50 (KHTML, like Gecko) Version/5.1 Safari/534.50",
        u"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_0) AppleWebKit/535.11 (KHTML, like Gecko) Chrome/17.0.963.56 Safari/535.11",
        u"Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/535.1 (KHTML, like Gecko) Chrome/14.0.835.163 Safari/535.1",
        u"Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.88 Mobile Safari/537.36"
    ]
    _headers = {
        u'user-agent': random.choice(user_agent)
    }
    _cookies = {}

    def __init__(self, project_name, method=u"GET"):
        self.name = project_name
        self.method = method
        self.session = requests.Session()

    def interface(self):
        '''实例对方入口方法'''
        raise TypeError(u"Function TypeError")

    def requests(self, method, url, headers=None, *args, **kwargs):
        '''URL请求方法，所有的请求都必须经由此方法发起'''

    def parse(self, response):
        '''响应数据解析方法'''

    def filter(self, data):
        '''self.parse处理后的数据进行过滤，主要包括去重'''

    def set_cookies(self, cookies):
        self._cookies.update(cookies)

    @property
    def get_cookies(self):
        return self._cookies

    def set_headers(self, headers):
        self._headers.update(headers)

    @property
    def get_headers(self):
        return self._headers


class FileSteam(object):
    mapping = {
        "vacancy_exist": "vacancy_exist.json",
        "company_exist": "company_exist.json",
        "logger": "logger.txt"
    }

    def __init__(self, name):
        self.name = name
        self.filename = os.path.join(DIR, "store", self.get_map)
        self.f = None

    @property
    def get_map(self):
        name_map = self.mapping.get(self.name)
        if not name_map:
            raise
        return name_map

    def read(self):
        self.f = open(self.filename, "r")
        return json.load(self.f)

    def write(self, data):
        self.f = open(self.filename, "w")
        return json.dump(data, self.f)

    def add(self, msg):
        self.f = open(self.filename, "a")
        self.f.write(msg)

    def __del__(self):
        if self.f:
            self.f.close()
