from datetime import datetime
import re
import io
import sys

import requests
import lxml.html
import pywikibot

from constants import MONTHS_GENITIVE

url_regexp = r'\[?(?P<url>https?://(?:[\w_-]+(?:(?:\.[\w_-]+)+))(?:[\w.,@?^=%&:/~+#-]*[\w@?^=%&/~+#-])?)\]?'

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
    m = metadata(url)
    now = datetime.now()
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

def templetify_links(text):
    def templetify_context(context):
        nonlocal text
        text = re.sub(context, expand_url, text, flags=re.M)

    templetify_context(rf'^\* {url_regexp}$')
    templetify_context(rf'<ref(?: name=.+?)?>{url_regexp}</ref>')
    return text

def expand_page(page):
    page.text = templetify_links(page.text)
    page.save('оформлення')

def main():
    TEST = False
    if not TEST:
        site = pywikibot.Site()
        page = pywikibot.Page(site, sys.argv[1])
        expand_page(page)
    else:
        expanded = templetify_links(text)
        print(expanded)


text = """
== Зноски ==
<references>
<ref name="spotify">https://developer.spotify.com/documentation/web-api/reference/tracks/get-audio-features/</ref>
<ref name="qz">https://qz.com/1331549/these-are-the-best-songs-to-dance-to-according-to-computer-science/</ref>
</references>

== Література ==
*{{МД}}

{{music-stub}} 
{{Ізольована стаття}}

[[Категорія:Музичні терміни]]
"""

if __name__ == '__main__':
    main()
