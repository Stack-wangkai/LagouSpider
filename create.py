# -*- coding:utf-8 -*-
import sys
import json
import requests
from datetime import datetime
from random import randint

from base import FileSteam

Debug = False if "linux" in sys.platform else True


class CohirerBase(object):
    domain = "" if not Debug else ""

    def __init__(self, data):
        self.data = data
        self._session = requests.session()
        self.channel_url = self.domain + ""
        self.vacancy_url = self.domain + ""
        self.company_url = self.domain + ""
        self.login_url = self.domain + ""
        self.password = "" if Debug else ""
        self.username = ""
        self.company_file_stream = FileSteam("company_exist")

        self.login()

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
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,ja;q=0.7,zh-TW;q=0.6,es;q=0.5",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3"
        }

    def login(self):
        data = dict(username=self.username,
                    password=self.password,
                    remember_me=True)
        self.requests(url=self.login_url, data=data)

    def random_datetime(self):
        dt = datetime.now()
        return datetime(dt.year, dt.month, dt.day,
                        randint(8, 20), randint(1, 59), randint(1, 59))

    def create_company(self, data):
        company_id = self.filter_company(data)
        if company_id:
            return company_id
        res = self.requests(url=self.company_url, data=data)
        if res.status_code == 201:
            content = json.loads(res.content)
            self.add_filter({self.get_company_name(data): content.get("id")})
            return content.get("id")

    def filter_company(self, data):
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


class Vacancy(CohirerBase):

    def __init__(self, data):
        super(Vacancy, self).__init__(data)

    def main(self):
        insert_van_num = 0
        for obj in self.data:
            vacancy_data, company_data = obj.get("vacancy"), obj.get("company")
            if not self.check_vacancy_data(vacancy_data):
                continue
            company_id = vacancy_data.get("company_id")
            if not company_id:
                company_id = self.create_company(company_data)
                if not company_id:
                    continue
            van_id = self.create_vacancy(vacancy_data, company_id)
            self.publish_channel(van_id)
            insert_van_num += 1
        return insert_van_num

    def check_vacancy_data(self, data):
        if data.get("responsibility"):
            return True

    def create_vacancy(self, data, company_id):
        ''''''

    def publish_channel(self, vacancy_id):
        ''''''


class Company(CohirerBase):

    def __init__(self, data):
        super(Company, self).__init__(data)

    def main(self):
        company_id = self.create_company(self.data)
        if company_id:
            return company_id
