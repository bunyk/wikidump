import pywikibot
from pywikibot import pagegenerators
import mwparserfromhell
import time
import sys

TEMPLATE_NAME = 'Приєднати до'
CATEGORY_NAME = "Категорія:Статті до об'єднання"


TEMPLATE_NAMES = [
    'приєднати з',
    'merge from',
    'mergefrom',
    'merge',
    'приєднати',
    'приєднати до',
    "об'єднати",
    'merge to',
    'об’єднати',
    "об'єднати з",
]

def main():
    site = pywikibot.Site()
    cat = pywikibot.Category(site, CATEGORY_NAME)

    for page in pagegenerators.PreloadingGenerator(cat.articles(), 10):
        print()
        print(page.title())

        if not has_template(page.text, TEMPLATE_NAMES):
            print("Не має шаблону {{%s}}" % TEMPLATE_NAMES[0])
            continue

        added = when_template_was_added(page, TEMPLATE_NAMES)
        new_text = page.text
        if added is not None: # We know when added
            cat = pywikibot.Category(site, get_category_name_for_date(added))
            if not cat.exists():
                print("Нема", cat, "створюємо")
                cat.text = '{{Щомісячна категорія впорядкування}}'
                cat.save('Створення категорії впорядкування')

            code = mwparserfromhell.parse(page.text)
            for template in code.filter_templates():
                if template.name.lower() in TEMPLATE_NAMES and not template.has("дата"):
                    template.add("дата", get_template_date_for(added))

            new_text = str(code)
        new_text = new_text.replace("[[Категорія:Статті до об'єднання]]", '')
        pywikibot.showDiff(page.text, new_text)
        page.text = new_text
        page.save('Додавання дати до шаблону')
        time.sleep(20)



def when_template_was_added(page, template_name):
    last_time_saw_template = None
    for revision in page.revisions(content=True):
        if not has_template(revision.full_hist_entry().text, template_name):
            return last_time_saw_template
        else:
            last_time_saw_template = revision.timestamp

def has_template(text, name):
    code = mwparserfromhell.parse(text)
    for tmpl in code.filter_templates():
        if tmpl.name.lower() in TEMPLATE_NAMES:
            return True

    return False

def get_category_name_for_date(timestamp):
    return CATEGORY_NAME + ' з ' + MONTHS_GENITIVE[timestamp.month - 1] + ' ' + str(timestamp.year)

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
