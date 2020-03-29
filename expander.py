from datetime import datetime
import re
import io

import requests
import lxml.html
import pywikibot

from constants import MONTHS_GENITIVE

url_regexp = r'\[?(https?://(?:[\w_-]+(?:(?:\.[\w_-]+)+))(?:[\w.,@?^=%&:/~+#-]*[\w@?^=%&/~+#-])?)\]?'

def metadata(url):
    resp = requests.get(url)
    t = lxml.html.parse(io.StringIO(resp.text))
    return dict(
        title = t.find(".//title").text.strip()
    )

def expand_url(match):
    url = None
    for g in match.groups():
        if g:
            url = g
    assert url
    m = metadata(url)
    now = datetime.now()
    today = f'{now.day} {MONTHS_GENITIVE[now.month - 1]} {now.year}'

    return f'''{{{{cite web
 |url          = {url}
 |назва        = {m['title']} <!-- заголовок згенерований ботом -->
 |прізвище     =
 |ім'я         =
 |дата         =
 |веб-сайт     =
 |видавець     =
 |дата-доступу = {today}
}}}}'''

def templetify_links(text):
    raw_urls = rf'^\* {url_regexp}$|<ref>{url_regexp}</ref>'
    return re.sub(raw_urls, expand_url, text, flags=re.M)

def expand_page(page):
    page.text = templetify_links(page.text)
    page.save('оформлення')

def main():
    site = pywikibot.Site()
    page = pywikibot.Page(site, 'Туалетний папір')
    expand_page(page)
    # expanded = templetify_links(text)
    # print(expanded)


text = '''
{{Infobox programming language
| latest_release_date = {{Дата релізу та вік|2019|12|15|df=yes}}<ref>{{cite web |url= https://code.jsoftware.com/wiki/System/ReleaseNotes/J901 |title= J901 release 15 December 2019}}</ref>
| typing = [[Система типізації#Динамічна типізація|динамічна]]
| influenced = [[NumPy]]<ref name="Python for Data Analysis">[http://traims.tumblr.com/post/33883718232/python-for-data-analysis-18-oct-2012-london Wes McKinney at 2012 meeting Python for Data Analysis]</ref><br/>[[SuperCollider]]<ref name="SuperCollider documentation">[http://doc.sccode.org/Reference/Adverbs.html SuperCollider documentation, Adverbs for Binary Operators]</ref>
| operating_system = [[Багатоплатформність]]: [[Microsoft Windows]], [[Linux]], [[macOS]]
| license = [[GNU General Public License|GPLv3]]
| website = {{URL|www.jsoftware.com}}
}}

== Приклади ==
Отако виглядає код [[Життя (гра)|гри "Життя"]] на J<ref>https://copy.sh/jlife/</ref>:

Для порівняння, так виглядає аналогічний код на [[APL]]<ref>https://dfns.dyalog.com/c_life.htm</ref>:


== Примітки ==
{{reflist|2}}

* http://bunyk.wordpress.com/about
* [http://bunyk.wordpress.com/about]

== Посилання ==
*{{Official website|www.jsoftware.com}} {{ref-en}}
'''

if __name__ == '__main__':
    main()
