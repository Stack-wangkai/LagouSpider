# -*- coding:utf-8 -*-
import sys
import json
import requests
from datetime import datetime
from random import randint

from base import FileSteam

Debug = False if "linux" in sys.platform else True


class Vacancy(object):
    domain = ""

    def __init__(self, data):
        self.data = data
        self._session = requests.session()
        self.channel_url = self.domain + ""
        self.vacancy_url = self.domain + ""
        self.company_url = self.domain + ""
        self.login_url = self.domain + ""
        self.password = ""
        self.username = ""
        self.company_file_stream = FileSteam("company_exist")
        self.insert_van_num = 0

        self.login()

    def interface(self):
        for obj in self.data:
            vacancy_data, company_data = obj.get("vacancy"), obj.get("company")
            # 增加了一步数据的校验，因为个别字段爬取异常
            if not self.check_vacancy_data(vacancy_data):
                continue
            # 冗余引用
            self.vacancy_data = vacancy_data
            self.company_data = company_data
            # 先创建公司，拿到返回id，再创建职位
            company_id = self.create_company(company_data)
            if not company_id:
                continue
            # 创建职位
            van_id = self.create_vacancy(vacancy_data, company_id)
            if van_id:
                self.insert_van_num += 1
        return self.insert_van_num

    def check_vacancy_data(self, data):
        ''''''

    def create_vacancy(self, data, company_id):
        data.update({
            "company_id": company_id
        })
        res = self.requests(url=self.vacancy_url, data=data)
        assert res.status_code == 200, \
            u"创建职位请求错误，状态码:{}，请求数据:{}".format(res.status_code, data)
        id = json.loads(res.content).get("id")
        print u"*" * 30 + u"\n" + u"创建职位成功，id: " + str(id)
        return id

    def create_company(self, data):
        # 判断公司是否创建过
        company_id = self.filter_company(data)
        if company_id:
            return company_id
        res = self.requests(url=self.company_url, data=data)
        if res.status_code == 200:
            content = json.loads(res.content)
            # 创建信息持久化
            self.add_filter({self.get_company_name(data): content.get("id")})
            return content.get("id")
        print u"创建公司请求错误，状态码:{}，请求数据:{}".format(res.status_code, data)

    def filter_company(self, data):
        # 判断公司是否创建过，因为ID没有爬取，所以使用公司全称
        cxr = self.company_file_stream.read()
        name = self.get_company_name(data)
        return name and cxr.get(name)

    def add_filter(self, dic):
        cxr = self.company_file_stream.read()  # type:dict
        cxr.update(dic)
        self.company_file_stream.write(cxr)

    def get_company_name(self, data):
        if data and isinstance(data, dict):
            name = data.get("name")
            return name and name.get("c_name")

    @property
    def session(self):
        return self._session

    def requests(self, url, data, method="POST"):
        return self.session.request(method=method, url=url, json=data, headers=self.headers)

    @property
    def headers(self):
        return {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.142 Safari/537.36",
            "Connection": "keep-alive",
            "Content-Type": "application/json",
            "Accept-Language": "",
            "Accept": ""
        }

    def login(self):
        data = dict(username=self.username,
                    password=self.password,
                    remember_me=True)
        self.requests(url=self.login_url, data=data)

    def random_datetime(self):
        # 返回一个当天的随机datetime时间
        dt = datetime.now()
        return datetime(dt.year, dt.month, dt.day,
                        randint(8, 20), randint(1, 59), randint(1, 59))
