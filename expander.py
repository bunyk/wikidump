'''
python3 expander.py $PAGE_NAME 

will expand links in wikipedia page using templates. Example:

https://uk.wikipedia.org/w/index.php?title=%D0%A2%D0%B0%D0%BD%D1%86%D1%8E%D0%B2%D0%B0%D0%BB%D1%8C%D0%BD%D1%96%D1%81%D1%82%D1%8C&type=revision&diff=27777964&oldid=27777749
'''
from datetime import datetime
import re
import io
import sys

import requests
import lxml.html
import pywikibot

from constants import MONTHS_GENITIVE

def main():
    site = pywikibot.Site('uk', 'wikipedia')
    page = pywikibot.Page(site, sys.argv[1])

    page.text = templetify_links(page.text)
    page.save('оформлення')

now = datetime.now()

def templetify_links(text):
    def templetify_context(context):
        nonlocal text
        text = re.sub(context, expand_url, text, flags=re.M)

    templetify_context(rf'^\* {url_regexp}$')
    templetify_context(rf'^\# {url_regexp}$')
    templetify_context(rf'<ref(?: name=.+?)?>{url_regexp}</ref>')
    templetify_context(rf'^\* {ext_link_regexp}$')
    templetify_context(rf'<ref(?: name=.+?)?>{ext_link_regexp}</ref>')
    return text

url_regexp = r'\[?(?P<url>https?://(?:[\w_-]+(?:(?:\.[\w_-]+)+))(?:[\w\.,@?^=%&:/~+#-]*[\w@?^=%&/~+#-])?)\]?'
ext_link_regexp = r'\[(?P<url>https?://(?:[\w_-]+(?:(?:\.[\w_-]+)+))(?:[\w\.,@?^=%&:/~+#-]*[\w@?^=%&/~+#-])?) .*?\]'

def get_meta(tree, selector, attribute='content'):
    m = tree.find('//meta[%s]' % selector)
    print('property', selector, m)
    if m is None:
        return ''
    print(m.attrib)
    return m.attrib.get(attribute, '')

def get_og_property(tree, name):
    return get_meta(tree, '@property="og:%s"' % name)

def metadata(url):
    resp = requests.get(url)
    t = lxml.html.parse(io.StringIO(resp.text))
    return Fields(
        title = get_og_property(t, 'title') or t.find(".//title").text.strip(),
        site = get_og_property(t, 'site_name'),
        author = get_meta(t, '@name="author"'),
    )

class Fields:
    def __init__(self, **kwargs):
        self.data = kwargs

    def __getattr__(self, name):
        return self.data[name].replace('|', '{{!}}')

def expand_url(match):
    url = match.group('url')
    assert url
    try:
        m = metadata(url)
    except Exception as e:
        print(e)
        return match.group(0)
    today = f'{now.day} {MONTHS_GENITIVE[now.month - 1]} {now.year}'

    return match.group(0).replace(url, f'''{{{{cite web
 |url          = {url}
 |назва        = {m.title} <!-- заголовок згенерований ботом -->
 |автор        = {m.author}
 |дата         =
 |веб-сайт     = {m.site}
 |видавець     =
 |дата-доступу = {today}
}}}}''')



if __name__ == '__main__':
    main()
