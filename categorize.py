import pywikibot
import turk

site = pywikibot.Site()

def translate_category(pagename, uk_title):
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

    already_categorized = set()
    for a in uk_cat.articles():
        already_categorized.add(a.title())

    for uk_title in get_uk_articles(cat):
        if uk_title in already_categorized:
            print(f"{uk_title} вже в категорії {uk_cat}")
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
        return
    sl = item.sitelinks.get(lang+'wiki')
    if sl:
        return sl.title

def get_uk_version(page):
    return get_translation(page, 'uk')

def add_en_cats(pagename):
    page = pywikibot.Page(site, pagename)
    entitle = get_translation(page, 'en')
    if not entitle:
        print(pagename, "не має відповідника в англійській вікіпедії")
        return
    enpage = pywikibot.Page(site, 'en:'+entitle)
    for cat in reversed(list(enpage.categories())):
        if cat.title().startswith('Category:Wikipedia articles '):
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
        if uk_cat:
            translate_category('en:' + cat.title(), 'Категорія:' + uk_cat)

TODO = """
Ґуд бай, Ленін!
"""


def main():
    for pn in TODO.splitlines():
        if pn.strip():
            add_en_cats(pn.strip())
    turk.save()

if __name__ == "__main__":
    main()
