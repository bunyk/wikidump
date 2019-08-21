import pywikibot
from pywikibot import pagegenerators
import mwparserfromhell
import time
import sys

SCOPE = [dict(
    category_name="Категорія:Статті до об'єднання",
    template_names = [
        'merge from',
        'merge into',
        'merge to',
        'merge with',
        'merge',
        'mergefrom',
        'об’єднати',
        "об'єднати",
        "об'єднати з",
        'приєднати до',
        'приєднати з',
        'приєднати',
    ]
), dict(
    category_name='Категорія:Статті, в яких потрібно виправити стиль',
    template_names=[
        'style',
        'стиль',
        'стиль розділу',
    ]
)]

def main():
    site = pywikibot.Site()
    for work in SCOPE:
        add_dates(site, work['category_name'], work['template_names'])

def add_dates(site, category_name, template_names):
    cat = pywikibot.Category(site, category_name)

    for page in pagegenerators.PreloadingGenerator(cat.articles(), 10):
        print()
        print(page.title())

        if not has_template(page.text, template_names):
            print("Не має шаблону", ' або '.join('{{%s}}' % name for name in template_names))
            continue

        added = when_template_was_added(page, template_names)
        new_text = page.text
        if added is not None: # We know when added
            cat = pywikibot.Category(site, get_category_name_for_date(category_name, added))
            if not cat.exists():
                print("Нема", cat, "створюємо")
                cat.text = '{{Щомісячна категорія впорядкування}}'
                cat.save('Створення категорії впорядкування')

            code = mwparserfromhell.parse(page.text)
            for template in code.filter_templates():
                if match_template(template, template_names) and not template.has("дата"):
                    template.add("дата", get_template_date_for(added))

            new_text = str(code)
        new_text = new_text.replace("[[%s]]" % category_name, '')
        pywikibot.showDiff(page.text, new_text)
        page.text = new_text
        page.save('Додавання дати до шаблону')
        time.sleep(20)



def when_template_was_added(page, template_names):
    last_time_saw_template = None
    for revision in page.revisions(content=True):
        if not has_template(revision.full_hist_entry().text, template_names):
            return last_time_saw_template
        else:
            last_time_saw_template = revision.timestamp

def match_template(template, template_names):
    tmpl_name = template.name.lower()
    if tmpl_name.startswith('шаблон:'):
        tmpl_name = tmpl_name[len('шаблон:'):]
    return tmpl_name in template_names

def has_template(text, template_names):
    code = mwparserfromhell.parse(text)
    for tmpl in code.filter_templates():
        if match_template(tmpl, template_names):
            return True

    return False

def get_category_name_for_date(category_name, timestamp):
    return category_name + ' з ' + MONTHS_GENITIVE[timestamp.month - 1] + ' ' + str(timestamp.year)

def get_template_date_for(timestamp):
    return MONTHS[timestamp.month - 1] + ' ' + str(timestamp.year)

MONTHS_GENITIVE = [
    'січня',
    'лютого',
    'березня',
    'квітня',
    'травня',
    'червня',
    'липня',
    'серпня',
    'вересня',
    'жовтня',
    'листопада',
    'грудня',
]
MONTHS = [
    'січень',
    'лютий',
    'березень',
    'квітень',
    'травень',
    'червень',
    'липень',
    'серпень',
    'вересень',
    'жовтень',
    'листопад',
    'грудень'
]

if __name__ == "__main__":
    main()
