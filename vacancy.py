# -*- coding:utf-8 -*-
import json
import time
from lxml import etree
from random import randint, random, choice
from datetime import datetime
from urllib import quote

from base import Spider, FileSteam
from mapping import Mapping, CompanyMapping


class LagouSpider(Spider):
    domain = u"https://www.lagou.com"
    start = 1
    page = 3
    page_num = 15
    vacancy_totals = 18
    max_circle_num = 2
    current_circle_num = 1

    def __init__(self):
        super(LagouSpider, self).__init__()
        self.sub_category = self._sub_category()
        self.caiwu_index_url = self.domain + u"/jobs/list_{}/p-city_0".format(self.url_string)
        self.caiwu_data_url = self.domain + u"/jobs/positionAjax.json"
        self.vacancy_url = self.domain + u"/jobs/{}.html"
        self.end = self.start + self.page
        self.vacancy_temp = []
        self.sid = ""
        self.exists_vacancy = 1
        self.result = []
        self.tip = ""
        self.depend()

    def _sub_category(self):
        values = ["财务", "会计", "审计", "出纳", "结算", "风控"]
        return choice(values)

    @property
    def url_string(self):
        return quote(self.sub_category)

    def depend(self):
        self.requests(url=self.caiwu_index_url,
                      headers=self.user_agent_header,
                      params=dict(px=u"default"))

    def main(self):
        print self.sub_category
        for index in range(self.start, self.end):
            data = {u"pn": index, u"kd": self.sub_category}
            if index == self.start == 1:
                branch_data = {u"first": u"true"}
            else:
                branch_data = {u"first": u"false", u"sid": self.sid}
            data.update(branch_data)
            response = self.requests(u"POST", self.caiwu_data_url,
                                     params=dict(px=u"default", needAddtionalResult=u"false"),
                                     data=data,
                                     headers=self.get_headers)
            resp = self.parse(response)
            if not resp:
                print u"第{}页爬取失败".format(index)
            else:
                self.result += resp or []
                print u"第{}页爬取完毕".format(index)
            time.sleep(random() + randint(1, 4))
        assert len(self.result), self.set_tip(u"爬取的数据为空，已中止")
        self.end_spider()

    def end_spider(self):
        '''爬虫流程结束的函数，首先判断数据量是否足够'''
        num = len(self.result) - max(self.page * self.page_num, self.vacancy_totals)

        if num < 0 and self.current_circle_num < self.max_circle_num:
            self.start = self.end
            self.end += num.__abs__() / self.page_num + 1
            self.current_circle_num += 1
            self.main()
            return
        else:
            result = Mapping(self.result).main()
            if result:
                self.write_vacancy_ids()
            print self.set_tip(u"本次职位采集完毕，共爬取{}个职位，入库{}个".format(len(self.vacancy_temp), result))

    def requests(self, method=None, url=None, headers=None, *args, **kwargs):
        response = self.session.request(method or self.method,
                                        url=url or self.url,
                                        headers=headers or self.get_headers,
                                        allow_redirects=False,
                                        *args, **kwargs)
        return response

    def parse(self, response):
        '''作进一步的响应信息校验'''
        status_code = response.status_code
        assert status_code == 200, self.set_tip(u"{}主页Ajax响应状态码为{}，完整响应消息".format(self.name, status_code))
        content = response.content and json.loads(response.content)
        if content and (content.get(u"code") == 0):
            data = content.get(u"content")
            vacancy_objs = data and data.get(u"positionResult").get(u"result")  # type:list
            assert vacancy_objs, self.set_tip(u"Ajax响应数据为空")
            assert isinstance(vacancy_objs, list), self.set_tip(u"Ajax响应数据格式有误")
            self.sid = data.get(u"showId")
            return self.filter(vacancy_objs)

    def filter(self, vacancy_objs):
        filter_vacancy_summary, filter_vacancy_ids = [], []
        for obj in vacancy_objs:
            positionId = obj.get(u"positionId")  # type: int
            if positionId in self.vacancy_exist:
                print u"已存在职位数量：{}".format(self.exists_vacancy)
                self.exists_vacancy += 1
                continue
            filter_vacancy_summary.append(obj)
            filter_vacancy_ids.append(positionId)
        self.vacancy_temp += filter_vacancy_ids
        if filter_vacancy_ids:
            vacancy_datas = self.spider_vacancy(filter_vacancy_ids)

            return self.merge(filter_vacancy_summary, vacancy_datas)

    def spider_vacancy(self, vacancy_ids):
        assert isinstance(vacancy_ids, list), u"参数请传List对象"
        objs = []
        for i in vacancy_ids:
            response = self.requests(url=self.vacancy_url.format(i))
            if not (response.status_code == 200) and response.content:
                if response.status_code == 302:
                    self.vacancy_temp.remove(i)
                    continue
            dic = self.extractor_html(response.content)  # type: dict
            if not dic:
                continue
            dic.update({u"positionId": i})
            objs.append(dic)
        return objs

    def extractor_html(self, content):
        '''xpath提取职位信息'''
        try:
            selector = etree.HTML(content)
        except etree.XMLSyntaxError as e:
            return
        if selector is None:
            return

        def _gather(x_path, fllter=True):
            value = selector.xpath(x_path)
            if fllter:
                return value and value[0].strip("/").strip()
            return value

        salary = _gather(u"/html/body/div[5]/div/div[1]/dd/h3/span[1]/text()")
        requirement = _gather(u"/html/body/div[5]/div/div[1]/dd/h3/span[3]/text()")
        light = _gather(u'//*[@id="job_detail"]/dd[1]/p/text()', False)
        website = _gather(u'//*[@id="job_company"]/dd/ul/li/a/@href')

        def responsibility_func():
            data = _gather(u'//*[@id="job_detail"]/dd[2]/div/p/text()', False)
            if data == []:
                data = _gather(u'//*[@id="job_detail"]/dd[2]/div/text()', False)
            responsibility = u"\n\u2022 "
            for i in data:
                text = i.strip(":") + u"\n\u2022 "
                responsibility += text
            responsibility = responsibility.rstrip(u"\n\u2022 ")
            return responsibility

        def full_location_func(selector):
            prefix = selector.xpath(u'//*[@id="job_detail"]/dd[3]/div[1]/a/text()')
            if not prefix == []:
                prefix.pop(-1)

            suffix = selector.xpath(u'//*[@id="job_detail"]/dd[3]/div[1]/text()')
            suffix = prefix and suffix[len(prefix)].strip().strip(u" - ") or ""
            full_location = prefix and ("").join(prefix) + suffix
            return full_location or u"暂未提供详细地址"

        responsibility = responsibility_func()
        full_location = full_location_func(selector)
        return dict(salary=salary, requirement=requirement, light=light,
                    responsibility=responsibility, website=website,
                    full_location=full_location)

    def merge(self, summary, vacancies):
        """
        :param summary:  []
        :param vacancies: []
        :return: []
        """
        max_lis, min_lis = max(summary, vacancies), min(summary, vacancies)
        if len(min_lis) == 0:
            return
        datas = []
        for i in range(len(min_lis)):
            positionId = min_lis[i].get(u"positionId")
            data = {}
            if max_lis[i].get(u"positionId") == positionId:
                data.update(min_lis[i])
                data.update(max_lis[i])
            datas.append(data)
        return datas

    @property
    def user_agent_header(self):
        return super(LagouSpider, self).get_headers

    @property
    def get_headers(self):
        headers = self.user_agent_header
        headers.update({
            u'Referer': self.caiwu_index_url + u"?px=default",
            u'Origin': self.domain,
            u'Accept': u'application/json, text/javascript, */*; q=0.01',
            u'Content-Type': u'application/x-www-form-urlencoded; charset=UTF-8',
            u"X-Requested-With": u"XMLHttpRequest",
            u"Host": u"www.lagou.com",
        })
        return headers

    @property
    def vacancy_exist(self):
        return FileSteam("vacancy_exist").read()

    def set_tip(self, tip):
        self.tip = tip
        return tip

    def __del__(self):
        if self.tip:
            self.logger()

    def write_vacancy_ids(self):
        ve = FileSteam("vacancy_exist").read()
        FileSteam("vacancy_exist").write(ve + self.vacancy_temp)

    def logger(self):
        dt = datetime.now().strftime('%Y-%m-%d %H:%M')
        msg = dt + self.tip + u"\n"
        FileSteam("logger").add(msg.encode("utf-8"))


class LagouCompanySummary(LagouSpider):
    def __init__(self):
        super(LagouCompanySummary, self).__init__()
        self.company_index_url = self.domain + "/gongsi/0-0-0-6"
        self.company_index_ajax_url = self.domain + "/gongsi/0-0-0-6.json"
        self.company_detail_index_url = self.domain + "/gongsi/{}.html"
        self.company_detail_job_url = self.domain + "/gongsi/j{}.html"
        self.company_detail_ajax_url = self.domain + "/gongsi/searchPosition.json"
        self.company_ids = []
        self.exists_company = 0
        self.f_data = FileSteam("company_summary")
        self.depend()

    def update_referer(self, referer):
        headers = self.get_headers
        headers.update({
            "Referer": referer
        })
        return headers

    def depend(self):
        self.requests(url=self.domain + "/gongsi/0-0-0-6",
                      headers=self.user_agent_header)

    def main(self):
        headers = self.update_referer(self.company_index_url)
        resp = []
        for i in range(1, 3):
            data = {u"first": u"false", u"pn": i, u"sid": self.sid,
                    u"sortField": 0, u"havemark": 0}
            response = self.requests(method="POST",
                                     url=self.company_index_ajax_url,
                                     headers=headers,
                                     data=data)
            res = self.parse(response)
            if isinstance(res, list):
                resp += res
            time.sleep(random() + randint(1, 4))

        self.mapping(resp)

    def parse(self, response):
        status_code = response.status_code
        assert status_code == 200, self.set_tip(u"{}公司主页响应状态码异常：{}".format(self.name, status_code))
        content = response.content
        if content and isinstance(content, str):
            content = json.loads(content)
            return self.filter(content)

    def filter(self, data):
        objs = data and data.get("result")  # type:list
        if not objs:
            return
        self.sid = data["showId"]
        return objs

    def mapping(self, data):
        company_map = CompanyMapping(data).main()
        if company_map:
            self.write_company(company_map)
        print u"爬取公司数量：{}".format(len(company_map))

    def write_company(self, data):
        f_data = self.f_data.read()  # type:dict
        if not f_data:
            self.f_data.write(data)
            return
        f_data.update(data)
        self.f_data.write(f_data)


class LagouCompanyVacancy(LagouCompanySummary):
    def __init__(self):
        super(LagouCompanyVacancy, self).__init__()
        self.temp = 1
        self.depend()
        self.result = []

    def main(self):
        f_data = self.f_data.read()  # type:dict
        count = 0
        ks = [k for k in f_data.keys()]
        for i in range(3):
            k = choice(ks)
            self.c_company_id = f_data[k]
            self.spider_company(k)
            print u"爬取公司成功{}个".format(self.temp)
            self.temp += 1
            if count == 4:
                break
            count += 1

        assert len(self.result), self.set_tip(u"爬取的数据为空，已中止")
        self.end_spider()

    def spider_company(self, id):
        """
        爬取相应公司
        :param id: 需要爬取的拉勾公司ID
        :return:
        """
        job_url = self.company_detail_job_url.format(id)
        ref_url = self.domain + "/gongsi/0-0-0-6"
        headers = self.update_referer(ref_url)
        self.requests(url=job_url,
                      headers=headers)
        for i in range(1, 3):
            data = {"companyId": id,
                    "positionFirstType": "全部",
                    "city": "",
                    "salary": "",
                    "workYear": "",
                    "schoolJob": "false",
                    "pageNo": i,
                    "pageSize": 10}
            response = self.requests(method="POST", url=self.company_detail_ajax_url,
                                     data=data,
                                     headers=headers
                                     )

            resp = self.parse(response)
            if isinstance(resp, list):
                self.result += resp
            time.sleep(random() + randint(1, 4))

    def end_spider(self):
        result = Mapping(self.result).main()
        if result:
            # 保存临时的职位id
            self.write_vacancy_ids()
        print self.set_tip(u"本次职位采集完毕，共爬取{}个职位，入库{}个".format(len(self.vacancy_temp), result))

    def parse(self, response):
        '''作进一步的响应信息校验'''
        status_code = response.status_code
        assert status_code == 200, self.set_tip(u"{}主页Ajax响应状态码为{}，完整响应消息".format(self.name, status_code))
        data = response.content and json.loads(response.content)
        if data and (data.get(u"state") == 1):
            vacancy_objs = data["content"]["data"]["page"]["result"]  # type:list
            self.sid = data["content"]["data"]["showId"]
            assert vacancy_objs, self.set_tip(u"Ajax响应数据为空")
            assert isinstance(vacancy_objs, list), self.set_tip(u"Ajax响应数据格式有误")
            self.sid = data.get(u"showId")
            return self.filter(vacancy_objs)

    def filter(self, vacancy_objs):
        # 主页爬取的职位列表，过滤后的职位ID列表
        filter_vacancy_summary, filter_vacancy_ids = [], []
        # 读取已同步的职位，校验是否已存在
        for obj in vacancy_objs:
            positionId = obj.get(u"positionId")  # type: int
            # 判断id是否已存在
            if positionId in self.vacancy_exist:
                if self.exists_vacancy % 10 == 0:
                    print u"已存在职位数量：{}".format(self.exists_vacancy)
                self.exists_vacancy += 1
                continue
            obj["company_id"] = self.c_company_id
            filter_vacancy_summary.append(obj)
            filter_vacancy_ids.append(positionId)
        self.vacancy_temp += filter_vacancy_ids
        if filter_vacancy_ids:
            vacancy_datas = self.spider_vacancy(filter_vacancy_ids)

            return self.merge(filter_vacancy_summary, vacancy_datas)
