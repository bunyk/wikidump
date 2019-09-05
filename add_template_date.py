from datetime import datetime
import time
import sys

import pywikibot
from pywikibot import pagegenerators
import mwparserfromhell

PROBLEM_TEMPLATES = {
    'проблеми',
    'недоліки',
    'rq',
}

SCOPE = {
    'Статті, які потрібно розширити': dict(
        template_names=[
            'expand section',
            'expand',
            'sect-stub',
            'section stub',
            'section-stub',
            'дописати розділ',
            'доробити розділ',
            'заготівля розділу',
            'короткий вступ',
            'написати підрозділ',
            'незакінчений розділ',
            'розділ-доробити',
            'розширити розділ',
            'розширити',
        ]
    ),
    "Статті, написані занадто складно": dict(
        template_names={
            'незрозуміло',
        },
        problems_parameters={},
    ),
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
            'категоризувати',
            'категоризація',
        ],
        problems_parameters={'cat', 'без категорій'},
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
    'Статті до вікіфікації': dict(
        template_names={
            'вікіфікувати',
            'вікіфікувати розділ',
            'wikify',
            'wikification',
            'вікі',
            'вікіфікація',
            'доповнити голі посилання',
        },
        problems_parameters={
            'wikify',
            'вікіфікація',
            'вікіфікувати'
        },
    ),
    'Статті, з яких нема посилань': dict(
        template_names=[
            'безвихідна стаття',
            'стаття, з якої нема посилань',
            'статті, з яких нема посилань',
            'тупикова стаття',
        ]
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
            'немає джерел',
        },
        problems_parameters={
            'sources',
            'джерела',
            'без джерел',
            'refless',
            'source',
        },
    ),
    'Статті, що потребують додаткових посилань на джерела': dict(
        template_names={
            'cleanup-verify',
            'more sources',
            'moresources',
            'not verified',
            'refimprove',
            'refimprovesect',
            'додаткові джерела',
            'достовірність',
            'кращі джерела',
            'мало джерел',
            'недостатньо джерел',
            'недостовірність',
            'первинні джерела',
            'першоджерела',
            'розділ без джерел',
        },
        problems_parameters={
            'refimprove',
            'недостовірність',
            'первинні джерела',
        }
    ),
    'Статті без виносок': dict(
        template_names={
            'без виносок',
            'без посилань',
            'мало виносок',
            'без приміток',
            'недостатньо виносок',
        },
        problems_parameters={
            'no footnotes',
            'виноски',
            'без виносок',
        },
    ),
    'Статті, які можуть містити оригінальне дослідження': dict(
        template_names={
            'оригінальне дослідження',
            'оригінальні дослідження',
            'інформаційні помилки',
            'фактичні помилки',
            'од'
        },
        problems_parameters={
            'OR',
            'ОД',
            'оригінальне дослідження',
        },
    ),
    'Статті, що потребують вичитки': dict(
        template_names={
            'мовні помилки',
            'вичитати',
            'запит на вичитку',
            'помилки',
            'copy edit',
            'spelling',
        },
        problems_parameters={
            'mistakes',
            'помилки',
            'правопіс',
            'вичитати'
        },
    ),
    'Статті з обмеженим географічним охопленням': dict(
        template_names={
            'глобалізувати',
            'україніка',
            'ukrainika',
            'ukraine-specific',
            'country-specific',
            'globalize',
            'internationalize',
        },
        problems_parameters={
            'україніка',
            'глобалізувати',
        },
    ),
    'Статті, що можуть бути застарілими': dict(
        template_names={
            'оновити',
            'update',
            'старі дані',
            'застарілі дані',
            'out of date',
            'outdated',
            'oldinformation',
            'уре1',
            'застаріло',
        },
        problems_parameters={
            'update',
            'оновити',
            'старі дані',
        },
    ),
    'Статті з неавторитетними джерелами': dict(
        template_names={
            'неавторитетні джерела',
            'без ад',
            'над',
        },
        problems_parameters={
        },
    ),
    'Статті, які потрібно виправити після перекладу': dict(
        template_names={
            'auto-translate',
            'autotranslate',
            'autotranslation',
            'автопереклад старий',
            'автопереклад',
            'переклад поганої якості',
            'поганий переклад',
            'сирий переклад',
        },
        problems_parameters={
            'machine-trans',
            'автопереклад',
            'переклад',
        },
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
            'essay-like',
            'виправити розділ',
        ],
        problems_parameters={'style', 'стиль', 'abbr', 'абр'},
    ),
    'Статті, які потрібно переписати': dict(
        template_names={
            'переписати',
            'rewrite',
            'cleanup-rewrite',
            'cleanup rewrite',
            'rewrite-section',
        },
        problems_parameters={
            'переписати',
        }
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
            'нейтральність сумнівна',
        ],
        problems_parameters={
            'нейтральність',
            'npov',
            'НТЗ',
            'нейтральність сумнівна'
        },
    ),
}

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

def fix_page(site, page):
    print()
    print(page.title())

    new_text = page.text
    code = mwparserfromhell.parse(page.text)
    problems = find_problems(code)
    if problems:
        print('\n'.join(problems))
        noticed = problems_first_noticed(page, problems)
        for problem, date in noticed.items():
            assert date is not None
            ensure_category_existence(site, problem, date)
            formatted_date = get_template_date_for(date)
            for template in code.filter_templates():
                if match_template(template, SCOPE[problem]['template_names']):
                    if not template.has("дата"):
                        template.add("дата", formatted_date)
                    else: # template has дата
                        if not template.get('дата').value.strip():
                            template.add("дата", formatted_date)
                if match_template(template, PROBLEM_TEMPLATES):
                    params_to_update = {}
                    for param in template.params[:]:
                        param_name = str(param)
                        if '=' in param_name:
                            _, param_name = param_name.split('=', 1)
                        if any(weak_equal(param_name, param) for param in SCOPE[problem].get('problems_parameters', [])):
                            template.remove(param)
                            template.add(param_name, formatted_date)

        new_text = str(code)
    else:
        print("Не знайдено шаблонів недоліків. Є такі:")
        for tmpl in code.filter_templates():
            print('{{%s}}' % normalized_template_name(tmpl))

    for category_name in SCOPE:
        new_text = new_text.replace("[[Категорія:%s]]" % category_name, '')

    pywikibot.showDiff(page.text, new_text)
    if page.text != new_text:
        page.text = new_text
        try:
            page.save('Впорядкування категорій впорядкування')
        except Exception as e:
            print('ERROR', e)
        daylight_throttle()
    else:
        print('Нічого не міняли')

def find_problems(code):
    if isinstance(code, str):
        code = mwparserfromhell.parse(code)
    problems = set()
    if code is None:
        return problems
    for tmpl in code.filter_templates():
        tmpl_name = normalized_template_name(tmpl)
        if tmpl_name in TEMPLATES_2_PROBLEMS:
            problems.add(TEMPLATES_2_PROBLEMS[tmpl_name])
        if tmpl_name in PROBLEM_TEMPLATES:
            for param in tmpl.params:
                if not str(param).strip():
                    continue
                if not any(weak_equal(param, p2p) for p2p in PARAMS_2_PROBLEMS):
                    print("UNKNOWN PARAM", param)
                    continue
                for p2p in PARAMS_2_PROBLEMS:
                    if weak_equal(param, p2p):
                        problems.add(PARAMS_2_PROBLEMS[p2p])
    return problems

def weak_equal(a, b):
    a = str(a).strip()
    b = str(b).strip()
    if a == b:
        return True
    if not a:
        return False
    if not b:
        return False
    if a[0].lower() != b[0].lower():
        return False
    return a[1:] == b[1:]


def problems_first_noticed(page, current_problems):
    prev_revision_time = None
    dates = {}
    for revision in page.revisions(content=True):
        problems = find_problems(revision.full_hist_entry().text)
        for problem in current_problems:
            if problem not in problems and problem not in dates:
                dates[problem] = prev_revision_time
        prev_revision_time = revision.timestamp

    for problem in current_problems: # Set problems from first revision
        if dates.get(problem) is None:
            dates[problem] = prev_revision_time
    return dates

def ensure_category_existence(site, category_name, added):
    cat = pywikibot.Category(site, get_category_name_for_date(category_name, added))
    if cat.exists():
        print(cat, 'існує')
        return
    print("Нема", cat, "створюємо")
    cat.text = '{{Щомісячна категорія впорядкування}}'
    cat.save('Створення категорії впорядкування')

def daylight_throttle():
    """ Work slower at day to not disturb human editors much """
    n = datetime.now()
    if 'quick' in sys.argv:
        return
    if 1 < n.hour < 6: # night
        return
    print('"Обідня" перерва')
    time.sleep(30)

def normalized_template_name(template):
    tmpl_name = template.name.lower().strip()
    tmpl_name = tmpl_name.replace('_', ' ')
    if tmpl_name.startswith('шаблон:'):
        tmpl_name = tmpl_name[len('шаблон:'):]
    return tmpl_name.strip()

def match_template(template, template_names):
    return normalized_template_name(template) in template_names

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
