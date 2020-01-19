# -*- coding:utf-8 -*-
import json
import time
from lxml import etree
from random import randint, random
from datetime import datetime

from base import Spider, FileSteam
from mapping import Mapping


class LagouSpider(Spider):
    domain = u"https://www.lagou.com"
    start = 1
    page = 3
    page_num = 15
    vacancy_totals = 18
    max_circle_num = 2
    current_circle_num = 1

    def __init__(self, project_name, method=u"GET"):
        super(LagouSpider, self).__init__(project_name, method)
        self.caiwu_index_url = self.domain + u"/jobs/list_%E8%B4%A2%E5%8A%A1/p-city_0"
        self.caiwu_data_url = self.domain + u"/jobs/positionAjax.json"
        self.vacancy_url = self.domain + u"/jobs/{}.html"
        self.end = self.start + self.page
        self.vacancy_temp = []
        self.sid = ""
        self.exists_vacancy = 0
        self.result = []
        self.tip = ""
        self.depend()

    def depend(self):
        # 发起第一次请求，获取Cookie
        self.requests(url=self.caiwu_index_url,
                      headers=self.user_agent_header,
                      params=dict(px=u"default"))

    def interface(self):
        # 针对Ajax动态刷新数据的请求
        for index in range(self.start, self.end):
            data = {u"pn": index, u"kd": u"财务"}
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
            # 适当的间隔
            time.sleep(random() + randint(1, 4))
        # 准备结束爬虫工作，进入mapping阶段
        assert len(self.result), self.set_tip(u"爬取的数据为空，已中止")
        self.end_spider()

    def end_spider(self):
        '''爬虫流程结束的函数，首先判断数据量是否足够'''
        num = len(self.result) - max(self.page * self.page_num, self.vacancy_totals)

        if num < 0 and self.current_circle_num < self.max_circle_num:
            self.start = self.end
            self.end += num.__abs__() / self.page_num + 1
            self.current_circle_num += 1
            self.interface()
            return
        else:
            # 进入数据映射阶段
            result = Mapping(self.result).interface()
            if result:
                # 保存临时的职位id
                self.write_vacancy_ids()
            print self.set_tip(u"本次职位采集完毕，共爬取{}个职位，入库{}个\n".format(len(self.vacancy_temp), result))

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
            return self.filter(content.get(u"content"))

    def filter(self, data):
        vacancy_objs = data and data.get(u"positionResult").get(u"result")  # type:list
        assert vacancy_objs, self.set_tip(u"Ajax响应数据为空")
        assert isinstance(vacancy_objs, list), self.set_tip(u"Ajax响应数据格式有误")
        # 设置sid，非第一页Ajax访问需要携带
        self.sid = data.get(u"showId")
        # 主页爬取的职位列表，过滤后的职位ID列表
        filter_vacancy_summary, filter_vacancy_ids = [], []
        # 读取已同步的职位，校验是否已存在
        for obj in vacancy_objs:
            positionId = obj.get(u"positionId")  # type: int
            # 判断id是否已存在
            if positionId in self.vacancy_exist:
                print u"已存在职位数量：{}".format(self.exists_vacancy)
                self.exists_vacancy += 1
                continue
            filter_vacancy_summary.append(obj)
            filter_vacancy_ids.append(positionId)
        # 汇总过滤后的职位ID
        self.vacancy_temp += filter_vacancy_ids
        # 抓取职位数据
        if filter_vacancy_ids:
            vacancy_datas = self.spider_vacancy(filter_vacancy_ids)

            return self.merge(filter_vacancy_summary, vacancy_datas)

    def spider_vacancy(self, vacancy_ids):
        assert isinstance(vacancy_ids, list), u"参数请传List对象"
        objs = []
        for i in vacancy_ids:
            response = self.requests(url=self.vacancy_url.format(i))
            if not (response.status_code == 200) and response.content:
                # 302，禁止重定向的原因
                print u"{}职位响应状态码：{}".format(self.name, response.status_code)
                continue
            dic = self.extractor_html(response.content)  # type: dict
            if not dic:
                continue
            # 和summary数据合并的判断条件
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
        # 校验个别职位爬取失败，导致总数不一致的的情况
        max_lis, min_lis = max(summary, vacancies), min(summary, vacancies)
        if len(min_lis) == 0:
            return
        if len(summary) != len(vacancies):
            print u"职位概要数量与职位详情数量不一致，titles:{}, vacancies:{}".format(len(summary), len(vacancies))
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
            u'referer': self.caiwu_index_url + u"?px=default",
            u'Origin': self.domain,
            u'Accept': u'application/json, text/javascript, */*; q=0.01',
            u'Content-Type': u'application/x-www-form-urlencoded; charset=UTF-8',
            u"X-Requested-With": u"XMLHttpRequest",
            u"Host": u"www.lagou.com",
            # u"Sec-Fetch-Site": u"same-origin",
            # u"Sec-Fetch-Mode": u"cors",
            # u"Accept-Encoding": u"gzip, deflate, br",
            # u"Accept-Language": u"zh-CN,zh;q=0.9,en;q=0.8,ja;q=0.7,zh-TW;q=0.6,es;q=0.5"
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
