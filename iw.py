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
from datetime import datetime
import traceback
from typing import List, Dict

import pywikibot
from pywikibot import pagegenerators, Bot

from generalmodule import TmplOps
from constants import LANGUAGE_CODES


class IwExc(Exception):
    def __init__(self, message): 
        self.message = message

class IwBot(Bot):
    problems: Dict[str, List[str]] = {}
    all_args = []

    def __init__(self, locargs=[]):
        # Allowed command line arguments (in addition to global ones)
        # and their associated options with default values
        addargs = {"-maxpages": {"maxpages": "all"}}

        # Allow additional options
        addargs["-catrdepth"] = {"catrdepth": "infinite"}
        for key in addargs.keys():
            arg = addargs[key]
            k, v = list(arg.items())[0]
            self.availableOptions.update({k: v})

        self.botsite = None
        pywikibot._sites = {}
        # Read commandline arguments.
        self.all_args = pywikibot.handle_args(locargs)
        # Now we can create site object
        self.botsite = pywikibot.Site()

        # Get pages defined by global parameters
        # and parse options from the dictionary of command line arguments
        genFactory = pagegenerators.GeneratorFactory()
        options = {}
        options["catrdepth"] = "infinite"
        catrargs = []
        for arg in self.all_args:
            if arg.startswith("-catrdepth"):
                options["catrdepth"] = arg.split(":")[1]
            elif arg.startswith("-catr"):
                catrargs.append(arg)
                continue
            elif genFactory.handleArg(arg):
                continue
            elif arg == "-always":
                options["always"] = True
            elif not arg.split(":")[0] in addargs.keys():
                pywikibot.output('Option "%s" is not supported' % arg)
                pywikibot.showHelp(showHelp)
                sys.exit()
            else:
                splarg = arg.split(":")
                argcmd = splarg[0]
                optname = list(addargs[argcmd].keys())[0]
                if len(splarg) == 1:
                    options[optname] = True
                elif len(splarg) == 2:
                    argvalue = splarg[1]
                    options[optname] = argvalue
                elif len(splarg) > 2:
                    splreg = re.search(
                        r"(?P<argcmd>.*?)\:(?P<argvalue>.*)",
                        arg,
                        flags=re.UNICODE | re.MULTILINE | re.DOTALL | re.IGNORECASE,
                    )
                    if splreg:
                        options[optname] = splreg.group("argvalue")

        old = False  # On non-updated Windows machine, where -cat and -catr work
        if old:
            recurse = True
            if not options["catrdepth"] == "infinite":
                recurse = int(options["catrdepth"])
            for arg in catrargs:
                gen = genFactory.getCategoryGen(
                    arg,
                    recurse=recurse,
                    gen_func=pagegenerators.CategorizedPageGenerator,
                )
                if gen:
                    genFactory.gens.append(gen)
        else:
            for arg in catrargs:
                recurse = False
                catname = ""
                if arg.startswith("-catr:"):
                    recurse = True
                    if not options["catrdepth"] == "infinite":
                        recurse = int(options["catrdepth"])
                    catname = arg[len("-catr:") :]
                elif arg.startswith("-cat:"):
                    catname = arg[len("-cat:") :]
                gen = genFactory.getCategoryGen(
                    catname,
                    recurse=recurse,
                    gen_func=pagegenerators.CategorizedPageGenerator,
                )
                if gen:
                    genFactory.gens.append(gen)

        gen = genFactory.getCombinedGenerator()
        if not gen:
            super(IwBot, self).__init__(**options)
        else:
            preloadingGen = pagegenerators.PreloadingGenerator(gen)
            super(IwBot, self).__init__(generator=preloadingGen, **options)

        self.titleExceptions = [
            "Користувач:",
            "Вікіпедія:Кнайпа",
            "Обговорення:",
            "Обговорення користувача:",
            "Шаблон:Не перекладено",
            "Вікіпедія:Завдання для роботів",
            "Вікіпедія:Проект:Біологія/Неперекладені статті",
        ]
        self.wiki_cache = WikiCache()

    def run(self):
        self.Ntotal = 0

        self.start = datetime.now()

        try:
            for page in self.generator:
                if not self.getOption("maxpages") == "all":
                    if self.Ntotal == int(self.getOption("maxpages")):
                        break
                try:
                    self.treat(page)
                except Exception as e:
                    traceback.print_exc()
                    self.addProblem(
                        page,
                        "Сталася несподівана помилка (%s) під час роботи зі сторінкою [[%s]]"
                        % (e, page.title()),
                    )
        except KeyboardInterrupt:
            pass

        page = pywikibot.Page(
            pywikibot.Site(),
            'Користувач:BunykBot/Сторінки з неправильно використаним шаблоном "Не перекладено"',
        )
        self.userPut(
            page,
            page.text,
            self.format_problems(),
            summary="Автоматичне оновлення таблиць",
        )

        print("%d pages were processed" % self.Ntotal)
        print("%d pages were changed" % self._save_counter)
        print("%d pages were not changed" % (self.Ntotal - self._save_counter))
        print("Finished in %s seconds" % (datetime.now() - self.start).seconds)

    def treat(self, page):
        for exc in self.titleExceptions:
            if page.title().startswith(exc):
                return

        self.ok = True
        self.Ntotal += 1
        print("%d. Processing page [[%s]]" % (self.Ntotal, page.title()))

        iwtmpls = ["Не перекладено", "Нп", "Iw", "Нп5", "Iw2"]

        text = page.text
        for iwtmpl in iwtmpls:
            for iw in reversed(TmplOps.findTmpls(text, iwtmpl)):
                analyzed = self.iwanalyze(page, text, iw)
                if analyzed:
                    text = self.iwreplace(
                        text, iw, treba=analyzed[0], tekst=analyzed[1]
                    )

        if self.ok:
            self.userPut(
                page,
                page.text,
                text,
                summary="[[User:PavloChemBot/Iw|автоматична заміна]] {{[[Шаблон:Не перекладено|Не перекладено]]}} вікі-посиланнями на перекладені статті",
            )
        else:
            print(
                "Page [[%s]] was not changed because of the above problems"
                % page.title()
            )
            print("=" * 80)

    def iwanalyze(self, page, pageText, iw):
        # Extract all fields
        try:
            treba, tekst, mova, ee = self.getFields(pageText, iw)
        except IwExc as e:
            self.addProblem(page, e.message)
            return
        # print('{{iw|' + '|'.join([treba, tekst, mova, ee]) + '}}')

        # Find, whether the page was translated
        if not mova in LANGUAGE_CODES:
            self.addProblem(page, 'Мовний код "%s" не підтримується' % mova)
            return

        try:
            WikidataID, redirect, redirectTitle, tranlsatedInto = self.wiki_cache.get_iw_data(mova, ee)
        except IwExc as e:
            self.addProblem(page, e.message)
            return

        if not treba:
            self.addProblem(page, "Шаблон %s не має параметра з назвою сторінки" % iw.text)
            return
        # Now check, whether page with title needed already exists
        HEREexist = False
        HEREredirect = False
        HEREredirectTitle = None
        HEREWikidataID = None
        trebaPage = self.wiki_cache.get_page("uk", treba)

        if trebaPage.exists():
            HEREexist = True
            if trebaPage.isRedirectPage():
                HEREredirect = True
                trebaPage = trebaPage.getRedirectTarget()
                HEREredirectTitle = trebaPage.title()

        if HEREexist:
            try:
                HEREitem = pywikibot.ItemPage.fromPage(trebaPage)
                HEREitem.get()
                HEREWikidataID = HEREitem.id
            except Exception as e:
                self.addProblem(
                    page,
                    "Page %s does not have Wikidata element" % conv2wikilink(treba),
                )
                return

        # Make text substitutions for pages that translated, but first check them
        if HEREexist:
            if WikidataID == HEREWikidataID:
                if not HEREredirect:
                    return treba, tekst
                else:
                    self.addProblem(
                        page,
                        "Сторінка %s перенаправляє на %s"
                        % (conv2wikilink(treba), conv2wikilink(HEREredirectTitle)),
                    )
            else:
                self.addProblem(
                    page,
                    "Сторінки [[:%s:%s]] та %s пов'язані з різними елементами вікіданих"
                    % (mova, ee, conv2wikilink(treba)),
                )
                return
        elif tranlsatedInto:
            if redirect:
                self.addProblem(
                    page,
                    "Сторінка [[:%s:%s]] (→ [[:%s:%s]]) перекладена як %s, хоча хотіли %s"
                    % (
                        mova,
                        ee,
                        mova,
                        redirectTitle,
                        conv2wikilink(tranlsatedInto),
                        conv2wikilink(treba),
                    ),
                )
            else:
                self.addProblem(
                    page,
                    "Сторінка [[:%s:%s]] перекладена як %s, хоча хотіли %s"
                    % (mova, ee, conv2wikilink(tranlsatedInto), conv2wikilink(treba)),
                )

    def addProblem(self, page, message):
        page_title = page.title()
        if not page_title in self.problems.keys():
            self.problems[page_title] = []
        self.problems[page_title].append(message)
        print("\t>>> " + message)
        self.ok = False

    def iwreplace(self, pageText, iw, treba="", tekst=""):
        if tekst == "":
            pageText = pageText[: iw.start] + "[[" + treba + "]]" + pageText[iw.end :]
        elif (treba[0:1].lower() + treba[1:]) == (
            tekst[0:1].lower() + tekst[1:]
        ):  # for cases like {{Не перекладено|Марковська модель|марковська модель||Markov model}}
            pageText = pageText[: iw.start] + "[[" + tekst + "]]" + pageText[iw.end :]
        else:
            pageText = (
                pageText[: iw.start]
                + "[["
                + treba
                + "|"
                + tekst
                + "]]"
                + pageText[iw.end :]
            )

        return pageText

    def getFields(self, pageText, iw):
        lfields = TmplOps.getLuaFields(
            iw, lfieldnames=["треба", "текст", "мова", "є", "nocat"], getFieldPos=False
        )

        treba = lfields[0]
        tekst = lfields[1]
        mova = lfields[2]
        ee = lfields[3]

        if treba == None or treba == "":
            raise IwExc("Сторінка містить шаблон {{tl|Не перекладено}} без параметрів")

        if tekst == None:
            tekst = ""
        if mova == None or mova == "":
            mova = "en"
        if ee == None or ee == "":
            ee = treba

        return treba, tekst, mova, ee

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
            % (self.start.strftime("%d.%m.%Y, %H:%M:%S"), datetime.now().strftime("%d.%m.%Y, %H:%M:%S"), len(self.problems), probl)
        )
        return probl


def conv2wikilink(text):
    if text.startswith("Файл:") or text.startswith("Категорія:"):
        text = ":" + text
    return f"[[{text}]]"

class WikiCache:
    """Cache requests to wiki to avoid repeated requests"""

    def __init__(self):
        self.sites = dict(
            d=pywikibot.Site("wikidata", "wikidata")
        )
        self.cache = dict()
        self.page_cache = dict()

    def get_site(self, lang):
        """Get site by language"""
        if lang not in self.sites:
            self.sites[lang] = pywikibot.Site(lang, "wikipedia")
        return self.sites[lang]

    def get_page(self, lang, title):
        key = (lang, title)
        if key not in self.page_cache:
            self.page_cache[key] = pywikibot.Page(self.get_site(lang), title)
            self.page_cache[key].exists()
        return self.page_cache[key]

    def get_iw_data(self, lang, page_title):
        """Get interwiki data"""
        if (lang, page_title) not in self.cache:
            try:
                data = self._fetch_iw_data(lang, page_title)
            except Exception as e:
                data = e
            self.cache[(lang, page_title)] = data

        res = self.cache[(lang, page_title)]
        if isinstance(res, Exception):
            raise res
        return res

    def _fetch_iw_data(self, lang, page_title):
        """Do actual request to wiki to fetch interwiki data"""
        site = self.get_site(lang)

        WikidataID = None
        redirect = False
        redirectTitle = None
        tranlsatedInto = None

        if lang == "d":
            try:
                repo = site.data_repository()
                item = pywikibot.ItemPage(repo, page_title)
                item.get()
                WikidataID = item.id
                sitelinks = item.sitelinks
                if "ukwiki" in sitelinks.keys():
                    tranlsatedInto = sitelinks["ukwiki"]
            except Exception as e:  # TODO: replace by better exception
                print('!!!' * 100, e)
                raise IwExc("Сторінка [[:%s:%s]] не має елемента вікіданих (%s)" % (lang, page_title, e))
        else:
            page = self.get_page(lang, page_title)

            try:
                if page.exists():
                    if page.isRedirectPage():
                        redirect = True
                        page = page.getRedirectTarget()
                        redirectTitle = page.title()
                else:
                    raise IwExc("Не знайдено сторінки [[:%s:%s]]" % (lang, page_title))
            except Exception as e:
                raise IwExc("Якісь проблеми з назвою [[:%s:%s]] (%s)" % (lang, page_title, e))

            try:
                item = pywikibot.ItemPage.fromPage(page)
                item.get()
                WikidataID = item.id
                sitelinks = item.sitelinks
                if "ukwiki" in sitelinks.keys():
                    tranlsatedInto = sitelinks["ukwiki"]
            except Exception as e:
                page = f"[[:{lang}:{redirectTitle}]] (← [[:{lang}:{page_title}]])" if redirect else f"[[:{lang}:{page_title}]]"
                raise IwExc(f"Сторінка {page} не має елемента вікіданих")

        return WikidataID, redirect, redirectTitle, tranlsatedInto


if __name__ == "__main__":
    # Run with report:
    # python3.6 iw.py -maxpages:200 -cat:"Вікіпедія:Статті з неактуальним шаблоном Не перекладено" -always
    # python3.6 iw.py -maxpages:200 -ns:10 -ref:"Шаблон:Не перекладено" -always
    # python3.6 iw.py -page:"Користувач:Pavlo Chemist/Чернетка"

    robot = IwBot()
    robot.run()
