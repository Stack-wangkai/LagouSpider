# -*- coding:utf-8 -*-
import os
import requests
from lxml import etree

DIR = os.path.dirname(os.path.abspath(__name__))


class TestLagouJobHtmlSpider(object):
    '''
        抓取拉勾职位详情页面持久化，对xpath分析
    '''
    domain = u"https://www.lagou.com"
    job_id = ""

    def __init__(self, project_name, method=u"GET"):
        self.name = project_name
        self.method = method
        self.caiwu_index_url = self.domain + u"/jobs/list_%E8%B4%A2%E5%8A%A1/p-city_0"
        self.vacancy_url = self.domain + u"/jobs/{}.html"
        self.session = requests.session()
        self.filename = os.path.join(DIR, u"html", u"job_detail_html_{}.html".format(self.job_id))

    def main(self):
        # 发起第一次请求，获取Cookie
        self.requests(url=self.caiwu_index_url,
                      headers=self.get_headers,
                      params=dict(px=u"default"))

        # 发起第二次请求，成功会返回数据，获取html职位详情页
        response = self.requests(url=self.vacancy_url.format(self.job_id))
        if not (response.status_code == 200) and response.content:
            print response
            return
        # 持久化
        self.save_html(response)
        # 分析
        self.extractor_html(response.content)  # type: dict

    @property
    def get_headers(self):
        headers = {
            u"user-agent": u"Mozilla/5.0 (Macintosh; Intel Mac OS X 10.6; rv:2.0.1) Gecko/20100101 Firefox/4.0.1",
            u'referer': self.caiwu_index_url,
            u'Origin': self.domain,
            u'Accept': u'application/json, text/javascript, */*; q=0.01',
            u'Content-Type': u'application/x-www-form-urlencoded; charset=UTF-8'
        }
        return headers

    def requests(self, method=None, url=None, headers=None, *args, **kwargs):
        response = self.session.request(method or self.method,
                                        url=url,
                                        headers=headers or self.get_headers,
                                        *args, **kwargs)
        return response

    def extractor_html(self, content=None):
        '''xpath提取职位信息'''
        if content is None:
            content = self.read_html()
        selector = etree.HTML(content)

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
            print ("first", data)
            if data == []:
                data = _gather(u'//*[@id="job_detail"]/dd[2]/div/text()', False)
            print ("second", data)
            responsibility = u"\n\u2022 "
            for i in data:
                text = i.strip(":") + u"\n\u2022 "
                responsibility += text
            return responsibility.rstrip(u"\n\u2022 ")

        def full_location_func():
            prefix = _gather(u'//*[@id="job_detail"]/dd[3]/div[1]/a/text()', False)
            if not prefix == []:
                prefix.pop(-1)

            suffix = _gather(u'//*[@id="job_detail"]/dd[3]/div[1]/text()', False)
            suffix = prefix and suffix[len(prefix)].strip().strip(u" - ") or ""
            full_location = prefix and ("").join(prefix) + suffix
            return full_location or u"暂未提供详细地址"

        responsibility = responsibility_func()
        full_location = full_location_func()
        return dict(salary=salary, requirement=requirement, light=light,
                    responsibility=responsibility, website=website,
                    full_location=full_location)

    def save_html(self, response):
        with open(self.filename, "w") as f:
            f.write(response.content)

    def read_html(self):
        with open(self.filename, "r") as f:
            return f.read()


project_name = u"拉勾"
if __name__ == '__main__':
    pass
    # 抓取
    # TestLagouJobHtmlSpider(project_name).main()
    # 分析
    # TestLagouJobHtmlSpider(project_name).main()
