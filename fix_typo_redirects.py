import pywikibot
from pywikibot import pagegenerators
import mwparserfromhell
import time

site = pywikibot.Site('uk', 'wikipedia')
cat = pywikibot.Category(site, 'Категорія:Перенаправлення з помилок')

for r in pagegenerators.PreloadingGenerator(cat.articles(), 100):
    pages2fix = list(r.getReferences()) # skip not referenced redirects
    if not pages2fix:
        continue

    r_from = r.title()
    r_to = r.getRedirectTarget().title()
    print('Виправляю %s -> %s' % (r_from, r_to))
    time.sleep(1)

    for p in pages2fix:

        if p.namespace().canonical_name in {'User', 'User talk', 'Project'}: # ingore some namespaces
            continue
        if p.title().endswith('/Червоні посилання') or p.title().endswith('Нова стаття/Архів'):
            continue

        print('\tНа сторінці', p.title())
        # time.sleep(1)
        
        wikicode = mwparserfromhell.parse(p.text)

        for link in wikicode.filter_wikilinks():
            if link.title == r_from:
                link.title = r_to
            elif link.title == r_from[0].lower() + r_from[1:]:
                link.title == r_to[0].lower() + r_to[1:]
        new_text = str(wikicode)
        new_text = new_text.replace(
            '|посилання=%s|' % r_from, 
            '|посилання=%s|' % r_to, 
        )
        if p.text == new_text:
            print('\tПосилання не знайдено')
            continue
        pywikibot.showDiff(p.text, new_text)
        p.text = new_text
        try: 
            p.save('[[:Категорія:Перенаправлення з помилок|Виправлено помилки]]')
        except pywikibot.exceptions.OtherPageSaveError as e:
            print(e)
