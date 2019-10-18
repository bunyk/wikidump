#!/usr/bin/python
"""
(C) Wikipedia user Pavlo Chemist, 2015-2019
Distributed under the terms of the MIT license.

This bot will substitute iwtmpl {{Не перекладено}} and its aliases
with wiki-link, if the page-to-be-translated is already translated.

Arguments:
   -maxpages:n : process at most n pages
   -help       : print this help and exit

&paramsgen;

Pages to work on:
&params;
"""

import sys, re, json
from time import time
from datetime import datetime

import pywikibot
from pywikibot import pagegenerators

import generalmodule
from generalmodule import GenBot, TmplOps
from constants import LANGUAGE_CODES


docuReplacements = {
    "&paramsgen;": generalmodule.__doc__.replace("\nPages to work on:\n&params;", r""),
    "&params;": pagegenerators.parameterHelp,
}


class IwExc(Exception):
    pass


class IwBot(GenBot):
    ok = True
    problems = {}
    """
    Structure of problems:
    problems = {'PageTitle': ['Error message 1',
                              '...next error message...'],
                        ...next problem page...}
    """

    def __init__(self, locargs=[]):
        # Allowed command line arguments (in addition to global ones)
        # and their associated options with default values
        args = {"-maxpages": {"maxpages": "all"}, "-help": {"help": False}}

        self.botsite = None
        super(IwBot, self).__init__(showHelp="iw", addargs=args, locargs=locargs)

        self.titleExceptions = [
            "Користувач:",
            "Вікіпедія:Кнайпа",
            "Обговорення:",
            "Обговорення користувача:",
            "Шаблон:Не перекладено",
            "Вікіпедія:Завдання для роботів",
            "Вікіпедія:Проект:Біологія/Неперекладені статті",
            "Вікіпедія:WikiPhysContest-2016",
        ]

    def run(self):
        if self.getOption("help"):
            pywikibot.showHelp("iw")
            sys.exit()

        start = time()

        try:
            for page in self.generator:
                if not self.getOption("maxpages") == "all":
                    if self.Ntotal == int(self.getOption("maxpages")):
                        break
                try:
                    self.treat(page)
                except Exception as e:
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
        print("Finished in %s seconds" % int(time() - start))

    def treat(self, page):
        self.ok = True

        for exc in self.titleExceptions:
            if exc in page.title():
                return

        self.Ntotal += 1
        pywikibot.output("%d. Processing page [[%s]]" % (self.Ntotal, page.title()))

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
            pywikibot.output(
                "Page [[%s]] was not changed because of the above problems"
                % page.title()
            )
            pywikibot.output("=" * 80)

    def iwanalyze(self, page, pageText, iw):
        # Extract all fields
        try:
            treba, tekst, mova, ee = self.getFields(pageText, iw)
        except IwExc:
            self.addProblem(
                page, "Сторінка містить шаблон {{tl|Не перекладено}} без параметрів"
            )
            return

        # Find, whether the page was translated
        if not mova in LANGUAGE_CODES:
            self.addProblem(page, 'Мовний код "%s" не підтримується' % mova)
            return

        WikidataID = None
        redirect = False
        redirectTitle = None
        tranlsatedInto = None
        if mova == "d":
            try:
                site = pywikibot.Site("wikidata", "wikidata")
                repo = site.data_repository()
                item = pywikibot.ItemPage(repo, ee)
                item.get()
                WikidataID = item.id
                pywikibot.output("itom.id = %s" % WikidataID)
                sitelinks = item.sitelinks
                if "ukwiki" in sitelinks.keys():
                    tranlsatedInto = sitelinks["ukwiki"]
            except Exception as e:  # TODO: replace by better exception
                self.addProblem(
                    page, "Data item [[:%s:%s]] does not exist" % (mova, ee)
                )
                return
        else:
            movawiki = pywikibot.Site(mova, "wikipedia")
            eePage = pywikibot.Page(movawiki, ee)

            try:
                if eePage.exists():
                    if eePage.isRedirectPage():
                        redirect = True
                        eePage = eePage.getRedirectTarget()
                        redirectTitle = eePage.title()
                else:
                    self.addProblem(
                        page, "Не знайдено сторінки [[:%s:%s]]" % (mova, ee)
                    )
                    return
            except Exception as e:
                self.addProblem(
                    page, "Something is wrong with a title [[:%s:%s]]" % (mova, ee)
                )
                return

            try:
                item = pywikibot.ItemPage.fromPage(eePage)
                item.get()
                WikidataID = item.id
                sitelinks = item.sitelinks
                if "ukwiki" in sitelinks.keys():
                    tranlsatedInto = sitelinks["ukwiki"]
            except Exception as e:
                if redirect:
                    self.addProblem(
                        page,
                        "Сторінка [[:%s:%s]] (← [[:%s:%s]]) не має елемента вікіданих"
                        % (mova, redirectTitle, mova, ee),
                    )
                else:
                    self.addProblem(
                        page,
                        "Сторінка [[:%s:%s]] не має елемента вікіданих" % (mova, ee),
                    )
                return

        # Now check, whether page with title needed already exists
        HEREexist = False
        HEREredirect = False
        HEREredirectTitle = None
        HEREWikidataID = None
        if treba != "":
            trebaPage = pywikibot.Page(self.botsite, treba)

            try:
                if trebaPage.exists():
                    HEREexist = True
                    if trebaPage.isRedirectPage():
                        HEREredirect = True
                        trebaPage = trebaPage.getRedirectTarget()
                        HEREredirectTitle = trebaPage.title()
            except Exception as e:
                self.addProblem(
                    page, "Something is wrong with a title %s" % (conv2wikilink(treba))
                )
                return
        else:
            self.addProblem(page, "Template %s does not have any page title" % iw.text)
            return

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
                    self.ok = self.ok & True
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
                    "Pages [[:%s:%s]] and %s link to different Wikidata items"
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
        pywikibot.output("\t>>> " + message)
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
            raise IwExc

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
            "== Сторінки, які можливо потребують уваги ==\n\nСтаном на %s. Всього таких статей %d.\n\n%s"
            % (datetime.now().strftime("%d.%m.%Y, %H:%M:%S"), len(self.problems), probl)
        )
        return probl


def conv2wikilink(text):
    if text.startswith("Файл:") or text.startswith("Категорія:"):
        text = ":" + text
    return f"[[{text}]]"


if __name__ == "__main__":
    # Run with report:
    # python3.6 iw.py -maxpages:200 -cat:"Вікіпедія:Статті з неактуальним шаблоном Не перекладено" -always
    # python3.6 iw.py -maxpages:200 -ns:10 -ref:"Шаблон:Не перекладено" -always
    # python3.6 iw.py -page:"Користувач:Pavlo Chemist/Чернетка"

    robot = IwBot()
    robot.run()
