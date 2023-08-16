#!/usr/bin/python
"""
(C) Wikipedia user Pavlo Chemist, 2015-2019
Distributed under the terms of the MIT license.

This bot will substitute iwtmpl {{Не перекладено}} and its aliases
with wiki-link, if the page-to-be-translated is already translated.
"""

import re, json
from datetime import datetime, timedelta
import traceback
import itertools
from collections import Counter
import random
import sys

import pywikibot
import mwparserfromhell
from tqdm import tqdm

from constants import LANGUAGE_CODES, BOT_NAME

MAX_SUPPORTED_TEXT_LEN = 250000


def main():
    print("lets go!")
    robot = IwBot(backlinks_backlog)
    delay = 0
    if len(sys.argv) > 1:
        delay = int(sys.argv[1])
    robot.last_problems_update = datetime.now() - PROBLEMS_UPDATE_PERIOD + timedelta(hours=delay)
    robot.run_forever()

    title = 'Вікіпедія:Чим не є Вікіпедія'
    # robot.process(pywikibot.Page(SITE, title))


# Template name variations
IWTMPLS = [
    "Не_перекладено",
    "Не перекладено",
    "Нп",
    "Iw",
    "Нп5",
    "Нп3",
    "Iw2",
    "НП5",
    "Неперекладено",
    "Не переведено 5",
]

DO_NOT_DISTURB_TMPLS = [
    "У роботі",
    "Edited-by",
    "В роботі",
    "Пишу",
    "In progress",
    "Inuse",
    "In process",
    "In use",
    "Editing",
    "Under construction",
    "Underconstruction",
    "Редагування",
    "Редагую",
    "Draft",
    "Inuse-by",
    "Edited",
]

# If page name has one of this prefixes - skip it:
TITLE_EXCEPTIONS = [
    "Обговорення:",
    "Обговорення користувача:",
    "Обговорення шаблону:",
    "Шаблон:Не перекладено",
    "Вікіпедія:Завдання для роботів",
    "Вікіпедія:Проект:Біологія/Неперекладені статті",
]

PROBLEMS_UPDATE_PERIOD = timedelta(hours=24)  # Update problems page every

SITE = pywikibot.Site("uk", "wikipedia")

REPLACE_SUMMARY = "[[User:PavloChemBot/Iw|автоматична заміна]] {{[[Шаблон:Не перекладено|Не перекладено]]}} вікі-посиланнями на перекладені статті"

ERROR_REPORT_TITLE = f'Користувач:{BOT_NAME}/Сторінки з неправильно використаним шаблоном "Не перекладено"'
TIME_FORMAT = "%Y-%m-%d %H:%M"


class IwExc(Exception):
    def __init__(self, message):
        self.message = message


def conv2wikilink(text):
    if (text.startswith("Файл:") or text.startswith("Категорія:") or
       text.startswith("File:") or text.startswith("Category:")):
        text = ":" + text
    return f"[[{text}]]"


class WikiCache:
    """Cache requests to wiki to avoid repeated requests"""

    def __init__(self, filename="cache.json"):
        self.sites = dict(d=pywikibot.Site("wikidata", "wikidata"))
        self.cache = dict()

    def get_site(self, lang):
        """Get site by language"""
        if lang not in self.sites:
            self.sites[lang] = pywikibot.Site(lang, "wikipedia")
        return self.sites[lang]

    def get_page_and_wikidata(self, lang, title):
        key = lang + ":" + title
        if key in self.cache:
            return self.cache[key]

        try: 
            res = self._fetch_page_and_wikidata(lang, title)
        except pywikibot.exceptions.InvalidTitleError as e:
            raise IwExc(str(e))

        self.cache[key] = res
        return res

    def clear(self):
        self.cache.clear()

    def _fetch_page_and_wikidata(self, lang, title):
        res = dict(
            exists=False,
            redirect=None,
            wikidata_id=None,
            uk_version=None,
            redirect_wikidata_id=None,
            redirect_uk_version=None,
        )

        def get_uk_version(item):
            sl = item.sitelinks.get("ukwiki")
            if sl:
                return sl.ns_title()

        if lang == "d":
            site = self.get_site("d")
            repo = site.data_repository()
            item = pywikibot.ItemPage(repo, title)
            item.get()
            res["exists"] = True
            res["wikidata_id"] = item.id
            res["uk_version"] = get_uk_version(item)
            return res

        page = pywikibot.Page(self.get_site(lang), title)
        exists = page.exists()
        if not exists:
            return res

        res["exists"] = True
        if page.isRedirectPage():
            redirect = page.getRedirectTarget()
            try:
                item = pywikibot.ItemPage.fromPage(redirect)
                res["redirect_wikidata_id"] = item.id
                res["redirect_uk_version"] = get_uk_version(item)
            except pywikibot.exceptions.NoPageError:
                pass
            res["redirect"] = redirect.title()

        try:
            item = pywikibot.ItemPage.fromPage(page)
            res["wikidata_id"] = item.id
            res["uk_version"] = get_uk_version(item)
        except pywikibot.exceptions.NoPageError:
            pass

        return res


NAMESPACES = [
    0,  # main
    4,  # Вікіпедія
    6,  # File
    10,  # template
    14, # category
]


def category_backlog():
    cat = pywikibot.Category(
        SITE,
        "Категорія:Вікіпедія:Статті з неактуальним шаблоном Не перекладено",
    )
    return cat.articles()


def search_backlog():
    return itertools.chain(
        *[
            SITE.search(
                'insource:"{{' + name_form + '|"',
                namespaces=NAMESPACES,
            )
            for name_form in IWTMPLS + [n.lower() for n in IWTMPLS]
        ]
    )


def backlinks_backlog():
    tmpl_p = pywikibot.Page(SITE, "Шаблон:Не перекладено")
    return tmpl_p.getReferences(namespaces=NAMESPACES, only_template_inclusion=True)


def order_backlog(pages):
    titles = set(p.title() for p in pages)
    backlog = list(titles)
    backlog.sort()
    return backlog


HIBERNATE_FILE = "iwbot.json"


class IwBot:
    def __init__(self, pages):
        self.pages = pages
        self.backlog = []
        self.problems = {}
        self.last_problems_update = None
        self.to_translate = Counter()
        self.cursor = 0

        if not self.load():
            self.backlog = order_backlog(pages())

        self.wiki_cache = WikiCache()
        self.processed_pages = set()

    def save(self):
        with open(HIBERNATE_FILE, "w") as f:
            state = dict(
                backlog=self.backlog,
                to_translate=self.to_translate,
                cursor=self.cursor,
            )
            json.dump(state, f, ensure_ascii=False, indent=" ")

    def load(self):
        try:
            with open(HIBERNATE_FILE) as f:
                data = json.load(f)
                self.backlog = data["backlog"]
                self.to_translate = Counter(data["to_translate"])
                self.cursor = data["cursor"]
            return True
        except Exception:
            return False

    def reset(self):
        self.wiki_cache.clear()
        self.backlog = order_backlog(self.pages())
        self.cursor = 0
        self.to_translate = Counter()

    def run(self):
        try:
            with tqdm(total=len(self.backlog), initial=self.cursor) as pbar:
                while self.cursor < len(self.backlog):
                    title = self.backlog[self.cursor]
                    self.process_step(title)
                    self.cursor += 1
                    pbar.update(1)
                    pbar.set_postfix(page=title)
                    self.process_problems()  # maybe
            self.publish_stats()
            self.reset()
            return True
        except KeyboardInterrupt:
            print("Saving work")
            self.save()
            print("Stopping")
            return False

    def run_forever(self):
        while self.run():
            pass

    def process_problems(self):
        if self.last_problems_update is not None and (
            datetime.now() - self.last_problems_update < PROBLEMS_UPDATE_PERIOD
        ):
            return  # updated problems not so far ago
        self.wiki_cache.clear()
        self.problems = {}

        problem_titles = order_backlog(list_problem_pages())
        for title in (pbar := tqdm(problem_titles)):
            pbar.set_postfix(page=title)
            self.process_step(title)
        self.update_problems()

    def process_step(self, title):
        while True:
            page = pywikibot.Page(SITE, title)
            try:
                self.process(page)
                break
            except pywikibot.exceptions.EditConflictError as e:
                print("Edit conflict, trying again")
            except Exception as e:
                self.add_problem(page, "Неочікувана помилка: %s %s" % (type(e), e))
                break

    def publish_stats(self):
        page = pywikibot.Page(
            SITE,
            f"Користувач:{BOT_NAME}/Найпотрібніші переклади",
        )
        update_page(page, self.format_top(), "Автоматичне оновлення таблиць")

    def update_problems(self):
        page = pywikibot.Page(SITE, ERROR_REPORT_TITLE)
        update_page(page, self.format_problems(None), "Автоматичне оновлення таблиць")

        for pn, project in PROJECTS.items():
            page = pywikibot.Page(SITE, project['errors_page'])
            update_page(page, self.format_problems(pn), "Автоматичне оновлення таблиць")

        self.last_problems_update = datetime.now()

    def process(self, page):
        """Process page to remove unnecessary iw templates"""
        for exc in TITLE_EXCEPTIONS:
            if page.title().startswith(exc):
                print("Skipping page because of title")
                return
            
        new_text = page.text
        new_text = re.sub(
            rf"<!-- Проблема вікіфікації: .+?-->", "", new_text
        )
        summary = set()

        code = mwparserfromhell.parse(new_text)
        if do_not_disturb(code):
            print("Skipping because of edit template")
            return

        for tmpl in iw_templates(code):
            if len(page.text) > MAX_SUPPORTED_TEXT_LEN:
                print("Skipping page because of size", len(page.text), "characters")
                return
            replacement = False
            problem = False
            try:
                replacement = self.find_replacement(tmpl)
            except IwExc as e:
                self.add_problem(page, e.message)
                problem = (
                    str(tmpl)
                    + "<!-- Проблема вікіфікації: "
                    + e.message
                    + f" ({BOT_NAME})-->"
                )
            except Exception as e:
                traceback.print_exc()
                self.add_problem(
                    page,
                    "Неочікувана помилка (%s %s) при роботі з шаблоном %s"
                    % (type(e), e, tmpl),
                )

            if replacement:
                new_text = new_text.replace(str(tmpl), replacement)
                summary.add(REPLACE_SUMMARY)
            if problem:
                new_text = new_text.replace(str(tmpl), problem)
                summary.add("повідомлення про помилки вікіфікації")

        # avoid duplication of comments
        new_text = deduplicate_comments(new_text)

        # Cleanup category (yes, some people add it manually)
        new_text = new_text.replace(
            "[[Категорія:Вікіпедія:Статті з неактуальним шаблоном Не перекладено]]", ""
        )

        if new_text == page.text:
            # page.touch()
            return

        if not summary:
            summary.add("виправлена вікіфікація")
        # Do additional replacements
        new_text = re.sub(r"\[\[([^|\d]+)\|\1([^\W\d]*)]]", r"[[\1]]\2", new_text)
        try: 
            update_page(page, new_text, ", ".join(summary))
        except pywikibot.exceptions.OtherPageSaveError as e:
            if 'Editing restricted by' in str(e):
                return
            raise e


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
        here = self.wiki_cache.get_page_and_wikidata("uk", uk_title)
        if not there["exists"]:
            raise IwExc(f"Не знайдено сторінки [[:{lang}:{external_title}]]")

        self.to_translate.update([f"{lang}:{external_title}"])

        if not (there["wikidata_id"] or there["redirect_wikidata_id"]):
            if here["exists"]:
                raise IwExc(
                    f"Сторінка [[:{lang}:{external_title}]] не має пов'язаного елемента вікіданих"
                )
            else:
                return (
                    None  # this is not a big deal, maybe they will create it before us
                )

        if here["exists"]:
            if (here["wikidata_id"] is not None) and (
                (here["wikidata_id"] == there["wikidata_id"])
                or (here["wikidata_id"] == there["redirect_wikidata_id"])
            ):
                return f"[[{uk_title}|{text}]]"
            elif (
                here["redirect"]
                and (here["redirect_wikidata_id"] is not None)
                and (
                    (here["redirect_wikidata_id"] == there["wikidata_id"])
                    or (here["redirect_wikidata_id"] == there["redirect_wikidata_id"])
                )
            ):  # where we redirect to is bound to their article
                # return f"[[{here['redirect']}|{text}]]"
                return f"[[{uk_title}|{text}]]"
            else:
                error_msg = (
                    "Сторінки [[:%s:%s]] та %s пов'язані з різними елементами вікіданих"
                    % (lang, external_title, conv2wikilink(uk_title))
                )
                raise IwExc(error_msg)
        else:
            if there["uk_version"]:
                pagelink = f"[[:{lang}:{external_title}]]"
                if there["redirect"]:
                    pagelink += f' (→ [[:{lang}:{there["redirect"]}]])'
                error_msg = (
                    f"Сторінка {pagelink} перекладена як "
                    f"{conv2wikilink(there['uk_version'])}, "
                    f"хоча хотіли {conv2wikilink(uk_title)}"
                )
                raise IwExc(error_msg)
            if there["redirect_uk_version"]:
                pagelink = f"[[:{lang}:{external_title}]]"
                if there["redirect"]:
                    pagelink += f' (→ [[:{lang}:{there["redirect"]}]])'
                error_msg = (
                    f"Сторінка {pagelink} перекладена як "
                    f"{conv2wikilink(there['redirect_uk_version'])}, "
                    f"хоча хотіли {conv2wikilink(uk_title)}"
                )
                raise IwExc(error_msg)

    def add_problem(self, page, message):
        page_title = page.title()
        page_project = detect_project(page)

        if not page_project in self.problems:
            self.problems[page_project] = {}

        if not page_title in self.problems[page_project]:
            self.problems[page_project][page_title] = []

        self.problems[page_project][page_title].append(message)
        print("\t>>> " + message)

    def format_top(self, n=500):
        top = f'Потребують перекладу {len(self.to_translate)} різних сторінок.\n'
        top += f'Загальна кількість червоних посилань до перекладу: {sum(self.to_translate.values())}.\n\n'
        top += f'{n} найпотрібніших перекладів:\n'
        top += '{| class="standard sortable"\n'
        top += "! Сторінка до перекладу || N\n"
        for page, n in self.to_translate.most_common(n):
            top += "|-\n| [[:%s]] || %d\n" % (page, n)
        top += "|}"
        return top

    def format_problems(self, project):
        probl = '{| class="standard sortable"\n'
        probl += "! Стаття з проблемами || Опис проблеми || N\n"
        for problem in sorted(self.problems[project].keys()):
            Nproblems = 0
            tablAppend = ""
            for prob in self.problems[project][problem]:
                Nproblems += 1
                if Nproblems == 1:
                    firstMessage = prob
                else:
                    tablAppend += "|-\n| %s\n" % prob
            if Nproblems == 0:
                continue  # no problems

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

        probl = f"""Ситуація станом на {datetime.now().strftime(TIME_FORMAT)}.

== Сторінки до виправлення ==

{probl}

[[Категорія:Упорядкування Вікіпедії]]"""
        return probl


LANGUAGE_MAPPINGS = dict(  # common language code mistakes
    cz="cs",
    jp="ja",
    rup="roa-rup",
)


def get_params(tmpl):
    """Return values of params for iw template"""

    sstr = lambda v: str(v).strip()
    uk_title, text, lang, external_title = "", "", "", ""
    for p in tmpl.params:
        name = sstr(p.name)
        val = sstr(p.value)
        if name == "1":
            uk_title = val
        if name == "2":
            text = val
        if name == "3":
            lang = val
        if name == "4":
            external_title = val

    for p in tmpl.params:
        val = sstr(p.value)
        name = sstr(p.name)
        if name == "треба":
            uk_title = val
        if name == "текст":
            text = val
        if name == "мова":
            lang = val
        if name == "є":
            external_title = val

    if not text:
        text = uk_title
    if not lang:
        lang = "en"
    if not external_title:
        external_title = uk_title

    lang = LANGUAGE_MAPPINGS.get(lang, lang)

    return uk_title, text, lang.lower(), external_title


def update_page(page, new_text, comment):
    if page.text == new_text:
        print("Nothing changed, not updating")
        return

    pywikibot.showDiff(page.text, new_text)

    page.text = new_text
    page.save(comment)


def name_in_list(name, lst):
    n = name.strip()
    return (n[0].upper() + n[1:]) in lst

def do_not_disturb(code):
    for tmpl in code.filter_templates():
        if name_in_list(tmpl.name, DO_NOT_DISTURB_TMPLS):
            return True
    return False

def iw_templates(code):
    for tmpl in code.filter_templates():
        if name_in_list(tmpl.name, IWTMPLS):
            yield tmpl

    for tag in code.filter_tags():
        if str(tag.tag) != "gallery":
            continue

        for l in str(tag.contents).splitlines():
            if not l.strip():
                continue
            if not "|" in l:
                continue
            _, desc = l.split("|", 1)
            yield from iw_templates(mwparserfromhell.parse(desc))


def deduplicate_comments(text):
    return re.sub(
        rf"<!-- Проблема вікіфікації: (.+?)-->(<!-- Проблема вікіфікації: \1-->)+",
        rf"<!-- Проблема вікіфікації: \1-->",
        text,
    )


def list_problem_pages():
    for pn, project in PROJECTS.items():
        pp = pywikibot.Page(SITE, project['errors_page'])
        titles = re.findall(r'^\| (?:rowspan="\d+" \| )?\[\[([^\]]+)]]', pp.text, re.M)
        for title in titles:
            yield pywikibot.Page(SITE, title)

    pp = pywikibot.Page(SITE, ERROR_REPORT_TITLE)
    titles = re.findall(r'^\| (?:rowspan="\d+" \| )?\[\[([^\]]+)]]', pp.text, re.M)
    for title in titles:
        yield pywikibot.Page(SITE, title)

    for page in SITE.search("insource:/\<!-- Проблема вікіфікації/"):
        if page.title() not in titles:
            yield page


PROJECTS = dict(
    comp=dict(
        cat="Категорія:Статті проєкту Комп'ютерні науки",
        errors_page='Вікіпедія:Проєкт:Комп\'ютерні науки/Сторінки з неправильно використаним шаблоном "Не перекладено"',
        page="Вікіпедія:Проєкт:Комп'ютерні науки",

    ),
    anime=dict(
        cat="Категорія:Статті проєкту Аніме та манґа",
        errors_page='Вікіпедія:Проєкт:Аніме та манґа/Сторінки з неправильно використаним шаблоном "Не перекладено"',
        page='Вікіпедія:Проєкт:Аніме та манґа',
    ),
    bio=dict(
        cat="Категорія:Статті проєкту Біологія",
        errors_page='Вікіпедія:Проєкт:Біологія/Сторінки з неправильно використаним шаблоном "Не перекладено"',
        page='Вікіпедія:Проєкт:Біологія',
    ),
    math=dict(
        cat="Категорія:Статті проєкту Математика",
        page='Вікіпедія:Проєкт:Математика',
        errors_page='Вікіпедія:Проєкт:Математика/Сторінки з неправильно використаним шаблоном "Не перекладено"',
    ),
    med=dict(
        cat="Категорія:Статті проєкту Медицина",
        errors_page='Вікіпедія:Проєкт:Медицина/Сторінки з неправильно використаним шаблоном "Не перекладено"',
        page='Вікіпедія:Проєкт:Медицина',
    ),
    femin=dict(
        cat="Категорія:Статті проєкту Фемінізм",
        errors_page='Вікіпедія:Проєкт:Фемінізм/Сторінки з неправильно використаним шаблоном "Не перекладено"',
        page='Вікіпедія:Проєкт:Фемінізм',
    ),
)

def detect_project(p):
    tp = p.toggleTalkPage()
    talk_cats = {c.title() for c in tp.categories()}
    for pn, project in PROJECTS.items():
        if project['page'] in p.title():
            return pn
        if project['cat'] in talk_cats:
            return pn

if __name__ == "__main__":
    main()
