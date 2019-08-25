from datetime import datetime
import time
import sys

import pywikibot
from pywikibot import pagegenerators
import mwparserfromhell

PROBLEM_TEMPLATES = {
    'проблеми',
    'недоліки',
}

SCOPE = {
    "Статті з сумнівною значимістю": dict(
        template_names = {
            'значимість',
            'значимість розділу',
        },
        problems_parameters = {
            'notability',
            'значимість'
        },
    ),
    "Статті, які слід категоризувати": dict(
        template_names = [
            'без категорій',
            'категорія',
            'recat',
            'категоризувати'
        ],
        # 'problemsParameters': {u'cat', u'без категорій'},
    ),
    "Статті до об'єднання": dict(
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
    ),
    'Статті, в яких потрібно виправити стиль': dict(
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
        problems_parameters={'style', 'стиль', 'abbr', 'абр'},
    ),
    'Статті, які потрібно переписати': dict(
        template_names=[
            'переписати',
            'rewrite',
            'cleanup-rewrite',
            'cleanup rewrite',
        ]
    ),
    'Статті, які потрібно розширити': dict(
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
    ),
    'Статті до вікіфікації': dict(
        template_names={
            'вікіфікувати',
            'вікіфікувати розділ',
            'wikify',
            'wikification',
            'вікі',
            'вікіфікація'
        },
        problems_parameters={'wikify', 'вікіфікація', 'вікіфікувати'},
    ),
    'Статті, з яких нема посилань': dict(
        template_names=[
            'безвихідна стаття',
            'стаття, з якої нема посилань',
            'статті, з яких нема посилань',
            'тупикова стаття',
        ]
    ),
    'Статті з сумнівною нейтральністю': dict(
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
    ),
    'Статті без джерел': dict(
        template_names={
            'без джерел',
            'unref',
            'безджерел',
            'no sources',
            'nosources',
            'джерела',
            'sources',
            'unreferenced',
        },
        problems_parameters={
            'sources',
            'джерела',
            'без джерел',
            'refless',
            'source',
        },
    )
}

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

ALL_TEMPLATE_NAMES = PROBLEM_TEMPLATES.union({
    name
    for work in SCOPE.values()
    for name in work['template_names']
})
TEMPLATES_2_PROBLEMS = {
    template: problem
    for problem, work in SCOPE.items()
    for template in work['template_names']
}
PARAMS_2_PROBLEMS = {
    param: problem
    for problem, work in SCOPE.items()
    for param in work.get('problems_parameters', {})
}

def main():
    site = pywikibot.Site()
    for category_name, work in SCOPE.items():
        add_dates(site, category_name, work['template_names'])

def add_dates(site, category_name, template_names):
    print('Розчищаємо', category_name)
    cat = pywikibot.Category(site, 'Категорія:' + category_name)

    for page in pagegenerators.PreloadingGenerator(cat.articles(), 10):
        fix_page(site, page)
        return


def fix_page(site, page):
    print()
    print(page.title())

    problems = find_problems(page.text)
    if problems:
        print('\n'.join(problems))
    else:
        print("Не знайдено шаблонів недоліків")
        return

    noticed = problems_first_noticed(page, problems)
    new_text = page.text
    code = mwparserfromhell.parse(page.text)
    for problem, date in noticed.items():
        assert date is not None
        ensure_category_existence(site, problem, date)
        formatted_date = get_template_date_for(date)
        for template in code.filter_templates():
            if match_template(template, SCOPE[problem]['template_names']) and not template.has("дата"):
                template.add("дата", formatted_date)
            if match_template(template, PROBLEM_TEMPLATES):
                for param in template.params[:]:
                    if str(param) in SCOPE[problem]['problems_parameters']:
                        template.remove(param)
                        template.add(str(param), formatted_date)

    new_text = str(code)

    # new_text = new_text.replace("[[Категорія:%s]]" % category_name, '')
    pywikibot.showDiff(page.text, new_text)
    if page.text != new_text:
        page.text = new_text
        try:
            page.save('Додавання дати до шаблону')
        except Exception as e:
            print('ERROR', e)
        daylight_throttle()
    else:
        print('Нічого не міняли')

def find_problems(text):
    problems = set()
    code = mwparserfromhell.parse(text)
    for tmpl in code.filter_templates():
        tmpl_name = normalized_template_name(tmpl)
        if tmpl_name in TEMPLATES_2_PROBLEMS:
            problems.add(TEMPLATES_2_PROBLEMS[tmpl_name])
        if tmpl_name in PROBLEM_TEMPLATES:
            for param in tmpl.params:
                problems.add(PARAMS_2_PROBLEMS[str(param)])
    return problems

def problems_first_noticed(page, current_problems):
    prev_revision_time = None
    dates = {}
    for revision in page.revisions(content=True):
        problems = find_problems(revision.full_hist_entry().text)
        for problem in current_problems:
            if problem not in problems and problem not in dates:
                dates[problem] = prev_revision_time
        prev_revision_time = revision.timestamp
    return dates

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

def normalized_template_name(template):
    tmpl_name = template.name.lower()
    if tmpl_name.startswith('шаблон:'):
        tmpl_name = tmpl_name[len('шаблон:'):]
    return tmpl_name

def match_template(template, template_names):
    return normalized_template_name(template) in template_names

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
