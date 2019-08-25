from datetime import datetime
import time
import sys

import pywikibot
from pywikibot import pagegenerators
import mwparserfromhell

SCOPE = [dict(
    category_name="Статті з сумнівною значимістю",
    template_names = {
        'значимість',
        'значимість розділу',
    },
    problems_parameters = {'notability', 'значимість'},
), dict(
    category_name="Статті, які слід категоризувати",
    template_names = [
        'без категорій',
        'категорія',
        'recat',
        'категоризувати'
    ],
    # 'problemsParameters': {u'cat', u'без категорій'},
), dict(
    category_name="Статті до об'єднання",
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
    category_name='Статті, в яких потрібно виправити стиль',
    template_names=[
        'style',
        'стиль',
        'стиль розділу',
        'переписати розділ',
        'забагато цитат',
        'надмірне цитування',
        'скорочення',
        'unabbr',
        'абр',
        'багато скорочень',
        'розкрити скорочення',
        'removeabbr',
        'noabbr',
        'abbreviations',
        'abbreviation',
        'expandabbr',
        'expandabbrev',
        'розкрити-скорочення',
        'розкрити-скор',
        'розк-скор',
        'unabbreviate',
        'abbrev',
        'реклама',
    ],
    # 'problemsParameters': {u'style', u'стиль'}
    #'problemsParameters': {u'abbr', u'абр'}
), dict(
    category_name='Статті, які потрібно переписати',
    template_names=[
        'переписати',
        'rewrite',
        'cleanup-rewrite',
        'cleanup rewrite',
    ]
), dict(
    category_name='Статті, які потрібно розширити',
    template_names=[
        'розширити',
        'розширити розділ',
        'section-stub',
        'section stub',
        'sect-stub',
        'expand',
        'expand section',
        'розділ-доробити',
        'написати підрозділ',
        'доробити розділ',
    ]
), dict(
    category_name='Статті до вікіфікації',
    template_names=[
        'вікіфікувати',
        'вікіфікувати розділ',
        'wikify',
        'wikification',
        'вікі',
        'вікіфікація'
    ],
    # 'problemsParameters': {u'wikify', u'вікіфікація', u'вікіфікувати'},
), dict(
    category_name='Статті, з яких нема посилань',
    template_names=[
        'безвихідна стаття',
        'стаття, з якої нема посилань',
        'статті, з яких нема посилань',
        'тупикова стаття',
    ]
), dict(
    category_name='Статті з сумнівною нейтральністю',
    template_names=[
        'нейтральність-розділ',
        'pov-section',
        'нтз-розділ',
        'npov',
        'нтз під питанням',
        'нтз',
        'pov',
        'нейтральність під сумнівом',
        'нтз під сумнівом',
        'нейтральність',
        'перевірити нейтральність',
        'neutrality',
    ],
    # 'problemsParameters': {u'npov', u'НТЗ', u'нейтральність сумнівна'},
)]
'''
    {
        'templateName': u'Оригінальне дослідження',
        'templateAliases': {u'Оригінальні дослідження', u'Інформаційні помилки', u'Фактичні помилки', u'ОД'},
        'problemsParameters': {u'OR', u'ОД'},
        'categoryName': u'Статті, які можуть містити оригінальне дослідження'
    },
    {
        'templateName': u'Оновити',
        'templateAliases': {u'Update', u'Старі дані', u'Застарілі дані', u'Out of date', u'Outdated', u'OldInformation',
                            u'УРЕ1'},
        'problemsParameters': {u'update', u'оновити', u'старі дані'},
        'categoryName': u'Статті, що можуть бути застарілими'
    },
    {
        'templateName': u'Refimprove',
        'templateAliases': {u'Cleanup-verify', u'Достовірність', u'Недостовірність', u'Not verified',
                            u'Додаткові джерела', u'More sources', u'Першоджерела'},
        'problemsParameters': {u'недостовірність'},
        'categoryName': u'Статті, що потребують додаткових посилань на джерела'
    },
    {
        'templateName': u'Refimprovesect',
        'templateAliases': set(),
        'problemsParameters': set(),
        'categoryName': u'Статті, що потребують додаткових посилань на джерела'
    },
    {
        'templateName': u'Без джерел',
        'templateAliases': {u'Unref', u'БезДжерел', u'No sources', u'Nosources', u'Джерела', u'Sources',
                            u'Unreferenced'},
        'problemsParameters': {u'sources', u'джерела', u'без джерел', u'refless', u'source'},
        'categoryName': u'Статті без джерел'
    },
    {
        'templateName': u'Розділ без джерел',
        'templateAliases': set(),
        'problemsParameters': set(),
        'categoryName': u'Статті, що потребують додаткових посилань на джерела'
    },
    {
        'templateName': u'Без виносок',
        'templateAliases': {u'Без посилань'},
        'problemsParameters': {u'no footnotes', u'виноски', u'без виносок'},
        'categoryName': u'Статті без виносок'
    },
    {
        'templateName': u'Неавторитетні джерела',
        'templateAliases': {u'Без АД', u'НАД'},
        'problemsParameters': set(),
        'categoryName': u'Статті з неавторитетними джерелами'
    },
    {
        'templateName': u'Глобалізувати',
        'templateAliases': {u'Україніка', u'Ukrainika', u'Ukraine-specific', u'Country-specific', u'Globalize',
                            u'Internationalize'},
        'problemsParameters': {u'україніка'},
        'categoryName': u'Статті з обмеженим географічним охопленням'
    },
    {
        'templateName': u'Мовні помилки',
        'templateAliases': {u'Вичитати', u'Запит на вичитку', u'Помилки', u'Copy edit'},
        'problemsParameters': {u'mistakes', u'помилки', u'правопіс', u'вичитати'},
        'categoryName': u'Статті, що потребують вичитки'
    },
    {
        'templateName': u'Автопереклад',
        'templateAliases': {u'Автопереклад старий', u'Переклад поганої якості', u'Поганий переклад', u'Autotranslation',
                            u'Auto-translate', u'Autotranslate'},
        'problemsParameters': {u'machine-trans', u'автопереклад', u'переклад'},
        'categoryName': u'Статті, які потрібно виправити після перекладу'
    },
'''


def main():
    site = pywikibot.Site()
    for work in SCOPE:
        add_dates(site, work['category_name'], work['template_names'])

def add_dates(site, category_name, template_names):
    print('Розчищаємо', category_name)
    cat = pywikibot.Category(site, 'Категорія:' + category_name)

    for page in pagegenerators.PreloadingGenerator(cat.articles(), 10):
        print()
        print(page.title())

        if not has_template(page.text, template_names):
            print("Не має шаблону", ' або '.join('{{%s}}' % name for name in template_names))
            continue

        added = when_template_was_added(page, template_names)
        new_text = page.text
        if added is not None: # We know when added
            ensure_category_existence(site, category_name, added)

            code = mwparserfromhell.parse(page.text)
            for template in code.filter_templates():
                if match_template(template, template_names) and not template.has("дата"):
                    template.add("дата", get_template_date_for(added))

            new_text = str(code)
        else:
            print('Чомусь невідомо коли шаблон додали')
        new_text = new_text.replace("[[Категорія:%s]]" % category_name, '')
        pywikibot.showDiff(page.text, new_text)
        if page.text != new_text:
            page.text = new_text
            try:
                page.save('Додавання дати до шаблону')
            except Exception as e:
                print('ERROR', e)

            daylight_throttle()

# {{Проблеми|значимість|вікіфікувати|без виносок}} TODO

def ensure_category_existence(site, category_name, added):
    cat = pywikibot.Category(site, get_category_name_for_date(category_name, added))
    if cat.exists():
        return
    print("Нема", cat, "створюємо")
    cat.text = '{{Щомісячна категорія впорядкування}}'
    cat.save('Створення категорії впорядкування')

def daylight_throttle():
    """ Work slower at day to not disturb human editors much """
    n = datetime.now()
    if 1 < n.hour < 6: # night
        return
    print('"Обідня" перерва')
    time.sleep(30)

def when_template_was_added(page, template_names):
    last_time_saw_template = None
    for revision in page.revisions(content=True):
        if not has_template(revision.full_hist_entry().text, template_names):
            return last_time_saw_template
        else:
            last_time_saw_template = revision.timestamp
    return last_time_saw_template

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
    return 'Категорія:' + category_name + ' з ' + MONTHS_GENITIVE[timestamp.month - 1] + ' ' + str(timestamp.year)

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
