#!/usr/bin/python
"""
(C) Wikipedia user Pavlo Chemist, 2015-2019
Distributed under the terms of the MIT license.

This bot will substitute iwtmpl {{Не перекладено}} and its aliases
with wiki-link, if the page-to-be-translated is already translated.

Arguments:
   -maxpages:n : process at most n pages
   -help       : print this help and exit
"""

import sys, re, json
from datetime import datetime, timedelta
import traceback
from typing import List, Dict

import pywikibot
from pywikibot import pagegenerators, Bot
import mwparserfromhell

from constants import LANGUAGE_CODES
from turk import Turk

IWTMPLS = ["Не перекладено", "Нп", "Iw", "Нп5", "Нп3", "Iw2"]
TITLE_EXCEPTIONS = [
    "Користувач:",
    # "Вікіпедія:Кнайпа",
    "Обговорення:",
    "Обговорення користувача:",
    "Обговорення шаблону:",
    "Шаблон:Не перекладено",
    "Вікіпедія:Завдання для роботів",
    "Вікіпедія:Проект:Біологія/Неперекладені статті",
]

REPLACE_SUMMARY = "[[User:PavloChemBot/Iw|автоматична заміна]] {{[[Шаблон:Не перекладено|Не перекладено]]}} вікі-посиланнями на перекладені статті"
TIME_FORMAT = "%d.%m.%Y, %H:%M:%S"

class IwExc(Exception):
    def __init__(self, message):
        self.message = message



def conv2wikilink(text):
    if text.startswith("Файл:") or text.startswith("Категорія:"):
        text = ":" + text
    return f"[[{text}]]"


class WikiCache:
    """Cache requests to wiki to avoid repeated requests"""

    def __init__(self, filename='cache.json'):
        self.sites = dict(d=pywikibot.Site("wikidata", "wikidata"))
        self.filename = filename
        try:
            with open(filename) as f:
                self.cache = json.load(f)
        except FileNotFoundError:
            self.cache = dict() # we will save it later

    def save(self):
        with open(self.filename, 'w', encoding='utf8') as f:
            json.dump(self.cache, f, indent=' ', ensure_ascii=False)

    def get_site(self, lang):
        """Get site by language"""
        if lang not in self.sites:
            self.sites[lang] = pywikibot.Site(lang, "wikipedia")
        return self.sites[lang]

    def get_page_and_wikidata(self, lang, title):
        key = lang + ':' + title
        if (
            (key in self.cache) and
            (datetime.strptime(
                self.cache[key]['till'],
                TIME_FORMAT
            ) >= datetime.now())
        ):
            return self.cache[key]['val']

        res = self._fetch_page_and_wikidata(lang, title)
        self.cache[key] = dict(
            val=res,
            till=(datetime.now() + timedelta(days=7 if res['exists'] else 1)).strftime(TIME_FORMAT)
        )
        return res

    def _fetch_page_and_wikidata(self, lang, title):
        res = dict(
            exists=False,
            redirect=None,
            wikidata_id=None,
            uk_version=None,
            redirect_wikidata_id=None,
            redirect_version=None,
        )
        if lang == 'd':
            site = self.get_site('d')
            repo = site.data_repository()
            item = pywikibot.ItemPage(repo, title)
            item.get()
            res['exists'] = True
            res['wikidata_id'] = item.id
            res['uk_version'] = item.sitelinks.get('ukwiki'),
            return res

        page = pywikibot.Page(self.get_site(lang), title)
        exists = page.exists()
        if not exists:
            return res

        res['exists'] = True
        if page.isRedirectPage():
            redirect = page.getRedirectTarget()
            try:
                item = pywikibot.ItemPage.fromPage(redirect)
                res['redirect_wikidata_id'] = item.id
                res['redirect_uk_version'] = item.sitelinks.get('ukwiki')
            except pywikibot.exceptions.NoPage:
                pass
            res['redirect'] = redirect.title()

        try:
            item = pywikibot.ItemPage.fromPage(page)
            res['wikidata_id'] = item.id
            res['uk_version'] = item.sitelinks.get('ukwiki')
        except pywikibot.exceptions.NoPage:
            pass

        return res

class IwBot2:
    problems: Dict[str, List[str]] = {}

    def __init__(self, method):
        self.method = method
        self.wiki_cache = WikiCache()
        self.turk = Turk()

    def run(self, time_limit=None):
        self.start = datetime.now()
        if self.method == "category":
            cat = pywikibot.Category(
                pywikibot.Site(),
                "Категорія:Вікіпедія:Статті з неактуальним шаблоном Не перекладено",
            )
            generator = cat.articles()
        if self.method == "search":
            search_query = r'insource:/\{\{(%s|%s)/' % ('|'.join(IWTMPLS), '|'.join(n.lower() for n in IWTMPLS))
            print("Searching for", search_query)
            generator = pagegenerators.SearchPageGenerator(
                search_query
                # namespaces=[0],
            )

        try:
            for n, page in enumerate(generator, 1):
                duration = (datetime.now() - self.start).seconds
                print(f"{n}. ({duration}s) Processing [[{page.title()}]]")
                try:
                    self.process(page)
                except Exception as e:
                    self.add_problem(page, 'Неочікувана помилка: %s %s' % (type(e), e))
                if time_limit and duration >= time_limit:
                    break
        except KeyboardInterrupt:
            pass

        self.wiki_cache.save()
        self.turk.save()

        page = pywikibot.Page(
            pywikibot.Site(),
            'Користувач:BunykBot/Сторінки з неправильно використаним шаблоном "Не перекладено"',
        )
        update_page(page, self.format_problems(), 'Автоматичне оновлення таблиць')

        print("%d pages were processed" % n)
        print("Finished in %s seconds" % (datetime.now() - self.start).seconds)

    def process(self, page):
        """Process page to remove unnecessary iw templates"""
        for exc in TITLE_EXCEPTIONS:
            if page.title().startswith(exc):
                print("Skipping page because of title")
                return
        new_text = page.text
        new_text = re.sub(r'<!-- Проблема вікіфікації: .+? \(BunykBot\)-->', '', new_text)
        code = mwparserfromhell.parse(new_text)
        summary = set()
        for tmpl in code.filter_templates():
            if not is_iw_tmpl(tmpl.name):
                continue
            replacement = False
            problem = False
            try:
                replacement = self.find_replacement(tmpl)
            except IwExc as e:
                self.add_problem(page, e.message)
                problem = str(tmpl) + '<!-- Проблема вікіфікації: ' + e.message + ' (BunykBot)-->'
            except Exception as e:
                traceback.print_exc()
                self.add_problem(page, "Неочікувана помилка (%s %s) при роботі з шаблоном %s" % (type(e), e, tmpl))

            if replacement:
                new_text = new_text.replace(str(tmpl), replacement)
                summary.add(REPLACE_SUMMARY)
            if problem:
                new_text = new_text.replace(str(tmpl), problem)
                summary.add('повідомлення про помилки вікіфікації')

        new_text = re.sub(r'<!--(.+?)-->(<!--\1-->)+', r'<!--\1-->', new_text)

        if new_text == page.text:
            return

        # DO additional replacements
        new_text = re.sub(r'\[\[([^|]+)\|\1(\w*)]]', r'[[\1]]\2', new_text)
        update_page(page, new_text, ', '.join(summary), yes=True)

    def find_replacement(self, tmpl):
        """Return string to which template should be replaced, if it should
        Return None or other falsy value otherwise.
        """
        uk_title, text, lang, external_title = get_params(tmpl)

        if not lang in LANGUAGE_CODES:
            raise IwExc('Мовний код "%s" не підтримується' % lang)
        if not uk_title:
            raise IwExc("Шаблон %s не має параметра з назвою сторінки" % tmpl)

        there = self.wiki_cache.get_page_and_wikidata(lang, external_title)
        if not there['exists']:
            raise IwExc(f"Не знайдено сторінки [[:{lang}:{external_title}]]")
        if not there['wikidata_id'] or there['redirect_wikidata_id']:
            return None # this is not a big deal, it will be created when page will have interwiki
            # raise IwExc(f"Сторінка [[:{lang}:{external_title}]] не має пов'язаного елемента вікіданих")

        here = self.wiki_cache.get_page_and_wikidata('uk', uk_title)
        # print(tmpl)
        # print('there:', there)
        # print('here:', here)
        # print()

        if here['exists']:
            if (here['wikidata_id'] is not None) and (here['wikidata_id'] == there['wikidata_id']):
                return f'[[{uk_title}|{text}]]'
            elif here['redirect'] and not there['redirect'] and (here['redirect_wikidata_id'] == there['wikidata_id']): # where we redirect to is bound to their article
                return f"[[{here['redirect']}|{text}]]"
            elif here['redirect'] and there['redirect'] and (here['redirect_wikidata_id'] == there['redirect_wikidata_id']):
                return f"[[{here['redirect']}|{text}]]"
            else:
                error_msg = "Сторінки [[:%s:%s]] та %s пов'язані з різними елементами вікіданих" % (
                    lang, external_title, conv2wikilink(uk_title)
                )
                raise IwExc(error_msg)
        else:
            if there['uk_version']:
                pagelink = f'[[:{lang}:{external_title}]]'
                if there['redirect']:
                    pagelink += f' (→ [[:{lang}:{redirect}]])'
                error_msg = (f"Сторінка {pagelink} перекладена як "
                    f"{conv2wikilink(there['uk_version'])}, "
                    f"хоча хотіли {conv2wikilink(uk_title)}"
                )
                answer = self.turk.answer(
                    error_msg + '\n Що робити?',
                    'Створити перенаправлення і послатись на основну статтю.',
                    'Створити перенаправлення і послатись на перенаправлення.',
                    'Послатись на основну статтю.',
                    'Перейменувати і послатись на перейменовану назву.',
                    'Поки що нічого'
                )
                if answer == 1:
                    create_redirect(uk_title, there['uk_version'])
                    return f"[[{there['uk_version']}|{text}]]"
                if answer == 2:
                    create_redirect(uk_title, there['uk_version'])
                    return f'[[{uk_title}|{text}]]'
                if answer == 3:
                    return f"[[{there['uk_version']}|{text}]]"
                if answer == 4:
                    rename(there['uk_version'], uk_title)
                    return f'[[{uk_title}|{text}]]'
                raise IwExc(error_msg)

    def add_problem(self, page, message):
        page_title = page.title()
        if not page_title in self.problems.keys():
            self.problems[page_title] = []
        self.problems[page_title].append(message)
        print("\t>>> " + message)

    def format_problems(self):
        probl = '{| class="standard sortable"\n'
        probl += "! Стаття з проблемами || Опис проблеми || N\n"
        for problem in sorted(self.problems.keys()):
            Nproblems = 0
            tablAppend = ""
            for prob in self.problems[problem]:
                Nproblems += 1
                if Nproblems == 1:
                    firstMessage = prob
                else:
                    tablAppend += "|-\n| %s\n" % prob

            problemText = conv2wikilink(problem)

            if Nproblems == 1:
                probl += "|-\n| %s || %s || %d\n" % (
                    problemText,
                    firstMessage,
                    Nproblems,
                )
            else:
                probl += '|-\n| rowspan="%d" | %s || %s || rowspan="%d" | %d\n' % (
                    Nproblems,
                    problemText,
                    firstMessage,
                    Nproblems,
                    Nproblems,
                )
                probl += tablAppend
        probl += "|}"

        probl = (
            "== Сторінки, які можливо потребують уваги ==\n\nСтаном на %s - %s. Всього таких статей %d.\n\n%s"
            % (
                self.start.strftime(TIME_FORMAT),
                datetime.now().strftime(TIME_FORMAT),
                len(self.problems),
                probl,
            )
        )
        return probl

def get_params(tmpl):
    """Return values of params for iw template"""

    uk_title, text, lang, external_title = "", "", "", ""
    for p in tmpl.params:
        if p.name == "треба" or p.name == "1":
            uk_title = p.value
        if p.name == "текст" or p.name == "2":
            text = p.value
        if p.name == "мова" or p.name == "3":
            lang = p.value
        if p.name == "є" or p.name == "4":
            external_title = p.value

    if not text:
        text = uk_title
    if not lang:
        lang = "en"
    if not external_title:
        external_title = uk_title

    return str(uk_title), str(text), str(lang).strip(), str(external_title)

def update_page(page, new_text, comment, yes=False):
    if page.text == new_text:
        print("Nothing changed, not saving")
        return
    pywikibot.showDiff(page.text, new_text)

    if yes or confirmed('Робимо заміну?'):
        page.text = new_text
        page.save(comment)

def create_redirect(from_title, to_title):
    page = pywikibot.Page(
        pywikibot.Site(),
        from_title
    )
    page.text = f'#ПЕРЕНАПРАВЛЕННЯ [[{to_title}]]'
    page.save('нове перенаправлення')

def rename(from_title, to_title):
    page = pywikibot.Page(
        pywikibot.Site(),
        from_title
    )
    page.move(to_title, 'посилання на назву')

def confirmed(question):
    return pywikibot.input_choice(
        question,
        [('Yes', 'y'), ('No', 'n')],
        default='N'
    ) == 'y'

def is_iw_tmpl(name):
    n = name.strip()
    return (n[0].upper() + n[1:]) in IWTMPLS

if __name__ == "__main__":
    # -cat:"Вікіпедія:Статті з неактуальним шаблоном Не перекладено"
    # -ns:10 -ref:"Шаблон:Не перекладено"
    robot = IwBot2("category")
    # title = 'Обговорення шаблону:Не перекладено'
    # title = 'Мелані Лінскі'
    # robot.process(pywikibot.Page(pywikibot.Site(), title))
    robot.run(time_limit=3600 * 20)
