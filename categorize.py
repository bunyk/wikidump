'''
Adds categories to list of pages, by looking which categories are used for en versions
of the same page.

For every added category, check which pages are in en version of the category,
and add all the existing uk pages to that category.
'''
import sys

import pywikibot

def main():
    add_cats(sys.argv[1], sys.argv[2])

site = pywikibot.Site('uk', 'wikipedia')

def search_category_articles(category, out, prefix = '', depth=2):
    t = category.title(with_ns=False)
    for a in category.articles():
        out[a.title()] = prefix + t
    if depth == 0:
        return
    for c in category.subcategories():
        search_category_articles(c, out, prefix + t + ' -> ', depth-1)

def translate_category(pagename, uk_title):
    print('Translate category', pagename, uk_title)
    if isprefixed(uk_title,
        'Категорія:Модуль',
        'Категорія:Вікіпедія:',
        'Категорія:Шаблон',
        'Категорія:Сторінки, що',
        'Категорія:Усі не',
    ):
        print("Не перекладаємо категорію", uk_title)
        return
    print("Перекладаємо категорію", pagename, uk_title)
    cat = pywikibot.Category(site, pagename)

    uk_cat = pywikibot.Category(site, uk_title)
    if not uk_cat.exists():
        print(f'Створюю категорію {uk_cat}')
        uk_cat.text = get_uk_text(cat)
        uk_cat.save('Створення нової категорії')
        add_sitelink(cat, uk_title)


    already_categorized = dict()
    search_category_articles(uk_cat, already_categorized, depth=3)

    for uk_title in get_uk_articles(cat):
        if uk_title in already_categorized:
            print(f"{uk_title} вже в категорії {already_categorized[uk_title]}")
            continue
        add_page_to_category(uk_title, uk_cat)

def isprefixed(s, *args):
    s = s.strip()
    return any(s.startswith(a) for a in args)

def add_page_to_category(uk_title, uk_cat):
    print(f"Додаємо {uk_title} до категорії {uk_cat}")
    try:
        page = pywikibot.Page(site, uk_title)
        uk_cat_title = uk_cat.title()
        page.text += f'\n[[{uk_cat_title}]]'
        page.save('Категоризація')
    except Exception as e:
        print(e)

def add_sitelink(page, uk_title):
    return # TODO: need permissions
    item = pywikibot.ItemPage.fromPage(page)
    item.setSitelink(dict(site='ukwiki', title=uk_title), summary='set sitelink')

def get_uk_text(cat):
    uk_text = []
    for line in cat.text.splitlines():
        if isprefixed(line.lower(), '{{commons category',  '{{commonscat', '{{catmore'):
            uk_text.append(line)

    uk_text.append('')
    for cc in cat.categories():
        uk_version = get_uk_version(cc)
        if uk_version and not uk_version.startswith('Вікіпедія:'):
            uk_text.append(f'[[Категорія:{uk_version}]]')

    return '\n'.join(uk_text)


def get_uk_articles(cat):
    for a in cat.articles():
        uk_version = get_uk_version(a)
        if uk_version:
            yield uk_version

def get_translation(page, lang):
    try:
        item = pywikibot.ItemPage.fromPage(page)
    except pywikibot.exceptions.NoPageError as e:
        print('Not found', page)
        raise
        return
    sl = item.sitelinks.get(lang+'wiki')
    if sl:
        return sl.ns_title()

def get_uk_version(page):
    return get_translation(page, 'uk')

def add_cats(lang, pagename):
    page = pywikibot.Page(site, pagename)
    entitle = get_translation(page, lang)
    if not entitle:
        print(f"{pagename} не має відповідника в {lang} вікіпедії")
        return
    enpage = pywikibot.Page(site, lang + ':'+entitle)
    if page.is_categorypage():
        if not enpage.is_categorypage():
            print(f"{pagename} - категорія, а {entitle} - ні")
            return
        cats = [pywikibot.Category(site, lang + ':' + enpage.title(with_ns=False))]
    else:
        cats = reversed(list(enpage.categories()))
    for cat in cats:
        if isprefixed(cat.title(),
                'Category:All articles',
                'Category:Wikipedia articles ',
                'Category:Articles ',
            ):
            print("Skip", cat)
            continue
        uk_cat = get_uk_version(cat)
        if not uk_cat:
            uk_cat = input(f'Як перекласти {cat.title()}?')
        else:
            if input(f'Категоризувати в {uk_cat}?') != 'y':
                uk_cat = ''
        if uk_cat.startswith('Категорія:'):
            uk_cat = uk_cat[len('Категорія:'):]
        if uk_cat.startswith('Category:'):
            uk_cat = uk_cat[len('Category:'):]
        if uk_cat:
            translate_category(lang + ':' + cat.title(), 'Категорія:' + uk_cat)

if __name__ == "__main__":
    main()
