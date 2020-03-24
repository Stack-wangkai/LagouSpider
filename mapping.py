# -*- coding:utf-8 -*-
import re

from create import Vacancy, Company


class Mapping(object):
    location = {}

    def __init__(self, input_data):
        self.input_data = input_data or []
        self.output_data = []

    def main(self):
        for data in self.input_data:
            vacancy_data = self.vacancy_mapping(data)
            company_data = self.company_mapping(data)
            self.output_data.append({"vacancy": vacancy_data,
                                     "company": company_data})
        '''调用数据入库接口'''
        result = Vacancy(self.output_data).main()
        assert result, u"创建职位异常"
        return result

    def format(self, output, input, mapping):
        '''字段转化的公共方法，如果是方法，则执行获取返回值；如果是str对象，则用作键'''
        output = output or {}
        for k, v in input.items():
            res = mapping.get(k)
            if callable(res):
                output.update(res(v))
            else:
                output.update({res: v})
        return output

    def vacancy_mapping(self, obj):
        '''转化可用的格式'''
        map = {
            u"positionName": self.title,  # 职位title
            u"city": self.city,  # 深圳
            u"salary": self.salary,  # 10k-15k
            u"jobNature": self.job_type,  # 全职
            u"light": self.tags,  # [亮点]
            u"requirement": self.requirement,  # 经验 3-5年
            u"responsibility": u"responsibility",  # 岗位职责
        }
        obj_dic = {
            # 默认/公共字段
        }
        return self.format(obj_dic, obj, map)

    def title(self, value):
        return {
        }

    def city(self, value):
        return {
        }

    def company_city(self, value):
        return {
        }

    def salary(self, value):
        if isinstance(value, list):
            return {
            }
        res_tuple = re.findall("\d+", value)
        return {
        }

    def job_type(self, value):
        map = {
        }
        return {
        }

    def tags(self, value):
        return {}

    def requirement(self, value):
        return {
        }

    def company_mapping(self, obj):
        company_mapping = {
            u"full_locationation": u"address",  # 公司详细地址
            u"companyFullName": self.company_full_name,  # 公司全称
            u"companySize": self.company_size,  # 公司规模，50-100人
            u"city": self.company_city,  # 地级市
            u"website": self.website,  # 网站
        }

        company_obj = {
        }
        return self.format(company_obj, obj, company_mapping)

    def website(self, value):
        if not isinstance(value, str):
            value = ""
        return {
        }

    def company_full_name(self, value):
        return {
            "name": {
                "c_name": value
            }
        }

    def company_size(self, value):
        map = {
        }
        res = re.findall("\d+", value)
        val = 0 if res == [] else res[0]
        return {
        }

class CompanyMapping(Mapping):
    def __init__(self, input_data):
        super(CompanyMapping, self).__init__(input_data)

    def main(self):
        dic = {}
        for data in self.input_data:
            companyID = data.get("companyId")
            company_data = self.company_mapping(data)
            id = Company(company_data).main()
            if id:
                dic.update({str(companyID): id})
        return dic