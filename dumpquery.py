import sys
import re
from itertools import islice
from collections import defaultdict, Counter

from pywikibot.xmlreader import XmlDump
import mwparserfromhell

def main():
    arg = sys.argv[1]
    # search_report(iter_pages(arg), sys.argv[2])
    # comments_report(iter_pages(arg))
    # mixed_names_report(iter_pages(arg))
    sections_report(iter_pages(arg))


def sections_report(pages):
    sections = defaultdict(list)
    existing_pages = set()
    links = Counter()
    for page in pages:
        if page.ns != '0':
            continue
        existing_pages.add(page.title)
        code = mwparserfromhell.parse(page.text)
        for h in code.filter_headings():
            sections[normalize(h.title)].append(page.title)
        for l in code.filter_wikilinks():
            links[normalize(l.title.split('#')[0])] += 1
    for link, frequency in links.most_common():
        if link in existing_pages:
            continue
        if link not in sections:
            continue
        if frequency < 2:
            continue
        if len(sections[link]) > 5:
            continue
        print(f'* [[{link}]] ({frequency})')
        for page in sections[link]:
            print(f'** [[{page}#{link}]]')


def normalize(title):
    s = title.strip()
    if not s:
        return ''
    return s[0].upper() + s[1:]

def search_report(pages, substring):
    for page in pages:
        for line in page.text.splitlines():
            if substring in line:
                print(f'[[{page.title}]]:', line)


def mixed_names_report(pages):
    print('{| class="wikitable sortable"')
    print('|-')
    print('! Назва статті !! Варіант перейменування')
    from fix_layouts_mix import fix_page_text, find_mixes
    for page in pages:
        if page.ns == '0' or page.ns == '2':
            continue
        if not find_mixes(page.title):
            continue
        fixed_title = fix_page_text(page.title)
        if fixed_title == page.title:
            fixed_title = '???'
        print('|-')
        print(f'| [[{page.title}]] || [[{fixed_title}]]')
    print('|}')


def comments_report(pages):
    print('{| class="wikitable sortable"')
    print('|-')
    print('! Назва статті !! Закоментовано % !! Закоментовано символів ')
    for p in pages:
        c = comments(p)
        if not c:
            continue
        print('|-')
        print(f'| [[{c["title"]}]] || {c["commented_percent"]:.1f}% || {c["commented_len"]}')
    print('|}')

def comments(page):
    if page.ns != '0':
        return
    if len(page.text) < 10:
        return
    not_commented = re.sub('<!--.*?-->', '', page.text, flags=re.DOTALL)
    commented_len = len(page.text) - len(not_commented)
    commented_percent = 100.0 * commented_len / len(page.text)
    if not (commented_len >= 5000 or commented_percent >= 50.0):
        return
    return dict(
        title=page.title,
        commented_len=commented_len,
        commented_percent=commented_percent,
    )

def iter_pages(dump_filename):
    i = 0
    for page in XmlDump(dump_filename).parse():
        i += 1
        if i % 123 == 0:
            print('\033[K\r', i, page.title, file=sys.stderr, end='')

        yield page

if __name__ == '__main__':
    main()
