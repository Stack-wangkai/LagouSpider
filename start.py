# -*- coding:utf-8 -*-
import sys

from vacancy import LagouSpider, LagouCompanyVacancy, LagouCompanySummary

if __name__ == '__main__':
    arg = sys.argv and sys.argv[1]
    if arg == u"vacancy":
        LagouSpider().main()
    elif arg == u"cv":
        LagouCompanyVacancy().main()
    elif arg == u"cs":
        LagouCompanySummary().main()
    else:
        print u"参数有误"
