from tehbot.plugins.challenge import *
import urllib
import urllib2
import urlparse
import lxml.html
import re

challurl = "https://www.rankk.org/stats.py"
userurl = "https://www.rankk.org/user/%s"

class Site(BaseSite):
    def prefix(self):
        return u"[Rankk]"

    def siteurl(self):
        return "https://www.rankk.org"

    def userstats(self, user):
        url = userurl % urllib.quote_plus(plugins.to_utf8(user))
        tree = lxml.html.parse(urllib2.urlopen(url, timeout=5))

        content = tree.xpath("//div[@id='main']")
        
        if content and content[0].text_content().lower().strip() == "user not found":
            raise NoSuchUserError

        table = tree.xpath("//div[@id='user']/div[@class='profile']/table")
        h1 = tree.xpath("//div[@id='main']/h1")
        li = tree.xpath("//div[@id='page']/ul[@id='events']/li[@id='counted']")
        etotal = tree.xpath("//div[@id='page']/div[@id='right']/div[@id='rankkometer']/ul/li[1]")
        
        if not table or not h1 or not li or not etotal:
            raise UnknownReplyFormat

        erank = table[0].xpath("tr[3]/td[2]")
        epoints = table[0].xpath("tr[5]/td[2]")
        esolved = table[0].xpath("tr[6]/td[2]")
        mprofile = re.search(r"Profile of (.*)", h1[0].text_content())
        mcounted = re.search(r"Counted:\s*(\d+)", li[0].text_content())
        mtotal = re.search(r"Total:\s*(\d+)", etotal[0].text_content())

        if not erank or not epoints or not esolved or not mprofile or not mcounted or not mtotal:
            raise UnknownReplyFormat

        real_user = mprofile.group(1)
        challs_total = int(mtotal.group(1))
        user_count = int(mcounted.group(1))

        return real_user, str(int(esolved[0].text_content())), challs_total, str(int(erank[0].text_content())), user_count, int(epoints[0].text_content()), None, None

    def str2nr(self, s):
        match = re.search(r'^(\d+)/(\d+)$', s)
        if not match:
            raise ValueError('invalid string for pattern %s: %s' % (r'^\d+/d+$', s))

        return (int(match.group(1)), int(match.group(2)))

    def nr2str(self, nr):
        return "%d/%d" % nr

    @staticmethod
    def parse(script):
        match = re.search(r"var\s+views\s*=\s*{\s*'solved'\s*:\s*'((?:[^'\\]|(?:\\'))*)'", script)
        return match.group(1).replace("\\'", "'") if match else ""

    def solvers(self, challname, challnr, user):
        tree = lxml.html.parse(urllib2.urlopen(challurl, timeout=5))
        escript = tree.xpath("//div[@id='page']/script")

        if not escript:
            raise UnknownReplyFormat

        content = Site.parse(escript[0].text_content())
        tree = lxml.html.fromstring(content)
        rows = tree.xpath("//table/tr")

        if not rows:
            raise UnknownReplyFormat

        res = None

        for row in rows:
            enr = row.xpath("td[@class='td'][1]")
            ename = row.xpath("td[@class='td'][2]")
            ecnt = row.xpath("td[@class='td'][3]")

            if not ename or not enr or not ecnt:
                continue

            nr = self.str2nr(enr[0].text_content().strip())
            name = ename[0].text_content().strip()
            cnt = int(ecnt[0].text_content().strip())

            if (challnr and nr == challnr) or (challname and name.lower().startswith(challname.lower())):
                res = (nr, name, cnt)
                break

            if not res and challname and challname.lower() in name.lower():
                res = (nr, name, cnt)

        if not res:
            raise NoSuchChallengeError

        nr, name, cnt = res
        solvers = None
        solved = Site.user_solved(user, name) if user else False
        return user, nr, name, cnt, solvers, solved

    @staticmethod
    def user_solved(user, challname):
        url = userurl % urllib.quote_plus(plugins.to_utf8(user))
        tree = lxml.html.parse(urllib2.urlopen(url, timeout=5))

        content = tree.xpath("//div[@id='main']")
        
        if content and content[0].text_content().lower().strip() == "user not found":
            raise NoSuchUserError

        rows = tree.xpath("//div[@id='allsolved']/ul[@class='solved']/li")

        if not rows:
            raise UnknownReplyFormat

        for row in rows:
            e = row.xpath("span")

            if not e:
                continue

            match = re.search(r'(\d+)/(\d+)\s*-\s*(.*)', e[0].text_content().strip())

            if not match:
                continue

            a, b, name = match.groups()
            nr = (int(a), int(b))

            if challname == name:
                return True

        return False

    @staticmethod
    def get_last5_solvers(nr):
        url = solversurl % (nr, "dummy", 1)
        tree = lxml.html.parse(urllib2.urlopen(url))
        pages = tree.xpath("//div[@id='page']/div[@class='gwf_pagemenu']//a")
        solvers = []

        if not pages:
            for row in tree.xpath("//div[@id='page']/table//tr"):
                e = row.xpath("td[2]/a[1]")
                if e:
                    n = e[0].text_content()
                    solvers.append(n)
        else:
            lastpage = int(pages[-1].text_content())
            for p in [lastpage - 1, lastpage]:
                url = solversurl % (nr, "dummy", p)
                tree = lxml.html.parse(urllib2.urlopen(url))

                for row in tree.xpath("//div[@id='page']/table//tr"):
                    e = row.xpath("td[2]/a[1]")
                    if e:
                        n = e[0].text_content()
                        solvers.append(n)

        return solvers[::-1][:5]
