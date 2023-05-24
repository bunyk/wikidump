import re
import sys
import json
from collections import defaultdict, Counter
from urllib.parse import urlparse
 
import mwparserfromhell
from pywikibot.xmlreader import XmlDump
 
def main():
    filename = sys.argv[1]
    existing_pages = get_pages(filename)
    print(f'''
    Have:
        - {len(existing_pages)} pages
    ''')

    count_links(get_filename())
 
def count_links(filename):
    links_count = Counter(iter_links(filename))
    top = links_count.most_common(1)[0]
    print(f'''
        - {sum(links_count.values())} total links
        - {len(links_count)} different links
        - top link, [[{top[0]}]] is linked to {top[1]} times
    ''')
    with open('top_links.json', 'w') as f:
        json.dump(links_count, f, ensure_ascii=False, indent='')

def iter_links(dump_filename):
    i = 0
    for page in XmlDump(dump_filename).parse():
        if page.ns != '0':
            continue
        i += 1
        if i % 123 == 0:
            print('\033[K\r', i, page.title, file=sys.stderr, end='')

        for link in get_links(page):
            l = link.replace('‎', '')
            l = re.sub(' +', ' ', l)
            if len(link) < 3:
                continue
            yield l[0].upper() + l[1:]

def get_pages(dump_filename):
    try:
        with open('pages.lst') as f:
            existing_pages = set(
                p.strip() for p in f
            )
        if existing_pages:
            return existing_pages
    except FileNotFoundError:
        pass

    print('gathering list of pages')
    existing_pages = set()
    i = 0
    for page in XmlDump(dump_filename).parse():
        if page.ns != '0':
            continue
        existing_pages.add(page.title)
        i+=1
        if i % 123 == 1:
            print('\033[K\r', i, page.title, end='')

    with open('pages.lst', 'w') as f:
        f.write('\n'.join(existing_pages))

    return existing_pages

def get_links(page):
    content = mwparserfromhell.parse(page.text)
    for link in content.filter_wikilinks():
        r = str(link.title).strip()
        if ':' in r: # skip non-default namespaces
            continue
        r = r.split('#', 1)[0] # get rid of everything after '#'
        if r:
            yield r

def get_filename():
    if len(sys.argv) < 2:
        print('Please provide file name of dump')
        sys.exit(1)
    return sys.argv[1]
 
if __name__ == '__main__':
    main()
