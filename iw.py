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

IWTMPLS = ["Не перекладено", "Нп", "Iw", "Нп5", "Iw2"]
TITLE_EXCEPTIONS = [
    "Користувач:",
    "Вікіпедія:Кнайпа",
    "Обговорення:",
    "Обговорення користувача:",
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
            till=(datetime.now() + timedelta(days=7 if res[0] else 1)).strftime(TIME_FORMAT)
        )
        return res

    def _fetch_page_and_wikidata(self, lang, title):
        print('fetching', lang, title)
        if lang == 'd':
            site = self.get_site('d')
            repo = site.data_repository()
            item = pywikibot.ItemPage(repo, title)
            item.get()
            wikidata_id = item.id
            uk_version = item.sitelinks.get('ukwiki')
            return True, None, wikidata_id, uk_version

        page = pywikibot.Page(self.get_site(lang), title)
        exists = page.exists()
        if not exists:
            return False, None, None, {}

        redirect = None
        if page.isRedirectPage():
            page = page.getRedirectTarget()
            redirect = page.title()

        try:
            item = pywikibot.ItemPage.fromPage(page)
            wikidata_id = item.id
            uk_version = item.sitelinks.get('ukwiki')
        except pywikibot.exceptions.NoPage:
            wikidata_id, uk_version = None, None

        return exists, redirect, wikidata_id, uk_version

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

        try:
            for n, page in enumerate(generator, 1):
                duration = (datetime.now() - self.start).seconds
                print(f"{n}. ({duration}s) Processing [[{page.title()}]]")
                self.process(page)
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
                return
        new_text = page.text
        code = mwparserfromhell.parse(new_text)
        for tmpl in code.filter_templates():
            if not is_iw_tmpl(tmpl.name):
                continue
            replacement = False
            try:
                replacement = self.find_replacement(tmpl)
            except IwExc as e:
                self.add_problem(page, e.message)
            except Exception as e:
                self.add_problem(page, "Неочікувана помилка (%s) при роботі з шаблоном %s" % (e, tmpl))

            if replacement:
                new_text = new_text.replace(str(tmpl), replacement)
        if new_text == page.text:
            return

        # DO additional replacements
        new_text = re.sub(r'\[\[([^|]+)\|\1(\w*)]]', r'[[\1]]\2', new_text)
        update_page(page, new_text, REPLACE_SUMMARY, yes=True)

    def find_replacement(self, tmpl):
        """Return string to which template should be replaced, if it should
        Return None or other falsy value otherwise.
        """
        uk_title, text, lang, external_title = get_params(tmpl)

        if not lang in LANGUAGE_CODES:
            raise IwExc('Мовний код "%s" не підтримується' % lang)
        if not uk_title:
            raise IwExc("Шаблон %s не має параметра з назвою сторінки" % iw.text)

        exists, redirect, wikidata_id, translated_into = self.wiki_cache.get_page_and_wikidata(lang, external_title)
        if not exists:
            raise IwExc(f"Не знайдено сторінки [[:{lang}:{external_title}]]")
        if not wikidata_id:
            raise IwExc(f"Сторінка [[:{lang}:{external_title}]] не має пов'язаного елемента вікіданих")

        here_exists, here_redirect, here_wikidata_id, _ = self.wiki_cache.get_page_and_wikidata('uk', uk_title)

        if here_exists:
            if here_wikidata_id == wikidata_id:
                if not here_redirect:
                    return f'[[{uk_title}|{text}]]'
                else:
                    error_msg = "Сторінка %s перенаправляє на %s" % (
                        conv2wikilink(uk_title), conv2wikilink(here_redirect)
                    )
                    answer = self.turk.answer(
                        error_msg + '\n Що робити?',
                        'Замінити на посилання на пряму сторінку.',
                        'Замінити на посилання на перенаправлення.',
                        'Поки що лишити як є'
                    )
                    if answer == 1:
                        return f'[[{here_redirect}|{text}]]'
                    if answer == 2:
                        return f'[[{uk_title}|{text}]]'

                    raise IwExc(error_msg)

            else:
                raise IwExc(
                    "Сторінки [[:%s:%s]] та %s пов'язані з різними елементами вікіданих"
                    % (lang, external_title, conv2wikilink(uk_title))
                )
        else:
            if translated_into:
                pagelink = f'[[:{lang}:{external_title}]]'
                if redirect:
                    pagelink += f' (→ [[:{lang}:{redirect}]])'
                raise IwExc(f"Сторінка {pagelink} перекладена як [[{translated_into}]], хоча хотіли [[{uk_title}]]")

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

def confirmed(question):
    return pywikibot.input_choice(
        question,
        [('Yes', 'y'), ('No', 'n')],
        default='N'
    ) == 'y'

def is_iw_tmpl(name):
    return (name[0].upper() + name[1:]) in IWTMPLS

if __name__ == "__main__":
    # -cat:"Вікіпедія:Статті з неактуальним шаблоном Не перекладено"
    # -ns:10 -ref:"Шаблон:Не перекладено"
    robot = IwBot2("category")
    robot.run(time_limit=3600 * 20)
