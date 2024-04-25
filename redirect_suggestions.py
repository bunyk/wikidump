from collections import Counter
import json
import sys

import pywikibot

with open('pages.lst') as f:
    existing_pages = set(
        p.strip() for p in f
    )

ci_existing = {p.lower(): p for p in existing_pages}

with open('top_links.json') as f:
    top_links = Counter(json.load(f))


DRY_RUN = True
substitues = [
    ("ь", ''),
]


enwiki = pywikibot.Site('en', "wikipedia")

def iter_suggestions():
    for link, frequency in top_links.most_common():
        if frequency < 10:
            break
        if link in existing_pages:
            continue
        # print(link, frequency, file=sys.stderr)

        # try:
        #     page = pywikibot.Page(enwiki, link)
        #     exists = page.exists()
        #     if not exists:
        #         continue
        #     if page.isRedirectPage():
        #         page = page.getRedirectTarget()

        #     item = pywikibot.ItemPage.fromPage(page)
        #     sl = item.sitelinks.get("ukwiki")
        #     if sl:
        #         yield link, sl.ns_title(), frequency
        # except Exception as e:
        #     print(e, file=sys.stderr)
        #     continue

        for f, t in substitues:
            if f in link and (fix := link.replace(f, t)) in existing_pages:
                yield link, fix, frequency

import pywikibot
site = pywikibot.Site('uk', 'wikipedia')


for link, fix, frequency in iter_suggestions():
    page = pywikibot.Page(site, link)
    target = pywikibot.Page(site, fix)
    print(f'* [[{link}]] ({frequency})\n** [[{fix}]]')
    if DRY_RUN:
        continue
    if target.isRedirectPage():
        target = target.getRedirectTarget()
    if page.exists():
        print('exists')
        continue
    page.text = f'#ПЕРЕНАПРАВЛЕННЯ [[{target.title()}]]'
    page.save("зв'язність")
