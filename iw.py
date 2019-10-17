#!/usr/bin/python
"""
(C) Wikipedia user Pavlo Chemist, 2015-2019
Distributed under the terms of the MIT license.

This bot will substitute iwtmpl {{Не перекладено}} and its aliases
with wiki-link, if the page-to-be-translated is already translated.

Arguments:
   -reportbytopic : generate and save reports by topics
   -loadreport    : load report dictionary from pickle file
   -dumpreport    : dump report dictionary in pickle file

                      or (but not together with above keywords)
   
   -replace    : replace pages [default]
   -report     : print only report, do not replace anything
   -maxpages:n : process at most n pages
   -notsafe    : allow Bot fail while processing a page
   -ignwarn    : ignore warning, but ask user to accept changes
   -help       : print this help and exit

&paramsgen;

Pages to work on:
&params;
"""

import pywikibot
from pywikibot import pagegenerators
import generalmodule
from generalmodule import GenBot, wikicodes, TmplOps, conv2wikilink, dump_obj, load_obj

import sys, re, time, json
from time import gmtime, strftime

docuReplacements = {
    "&paramsgen;": generalmodule.__doc__.replace("\nPages to work on:\n&params;", r""),
    "&params;": pagegenerators.parameterHelp,
}


class IwExc(Exception):
    pass


class IwBot(GenBot):
    ok = True
    IwItems = {}
    problems = {}
    report = ""
    Nitems = 0
    reportProblems = ""
    NproblemPages = 0
    # Structure of problems:
    """
    problems = {'PageTitle': ['Error message 1',
                              '...next error message...'],
                        ...next problem page...}
    """

    def __init__(self, locargs=[]):
        """Constructor."""
        # Allowed command line arguments (in addition to global ones)
        # and their associated options with default values
        args = {
            "-replace": {"replace": True},
            "-report": {"report": False},
            "-maxpages": {"maxpages": "all"},
            "-notsafe": {"notsafe": False},
            "-ignwarn": {"ignwarn": False},
            "-loadreport": {"loadreport": False},
            "-dumpreport": {"dumpreport": False},
            "-help": {"help": False},
        }

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

        if self.getOption("report"):
            self.options["replace"] = False

        if self.getOption("report") and self.getOption("loadreport"):
            self.IwItems = load_obj("IwItems")
            self.problems = load_obj("problems")
        else:
            try:
                for page in self.generator:
                    if not self.getOption("maxpages") == "all":
                        if self.Ntotal == int(self.getOption("maxpages")):
                            break
                    if self.getOption("notsafe"):
                        self.treat(page)
                    else:
                        try:
                            self.treat(page)
                        except KeyboardInterrupt:
                            raise KeyboardInterrupt
                        except Exception as e:
                            self.addProblem(
                                page,
                                "Unexpected error (%s) occured while processing page \03{blue}[[%s]]\03{default}!"
                                % (e, page.title()),
                            )
            except KeyboardInterrupt:
                raise KeyboardInterrupt
            except AttributeError:  # This will actually never work
                pywikibot.showHelp("iw")
                return

        if self.getOption("report"):
            pywikibot.output("%d pages were processed" % self.Ntotal)
            self.analyzeIwItems()
            self.analyzeProblems()

            if self.getOption("dumpreport"):
                dump_obj(self.IwItems, "IwItems")
                dump_obj(self.problems, "problems")

        elif self.getOption("replace"):
            pywikibot.output("%d pages were processed" % self.Ntotal)
            pywikibot.output("%d pages were changed" % self._save_counter)
            pywikibot.output(
                "%d pages were not changed" % (self.Ntotal - self._save_counter)
            )

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

        if self.getOption("ignwarn"):
            self.ok = True

        if self.ok and self.getOption("replace"):
            summary = u"[[User:PavloChemBot/Iw|автоматична заміна]] {{[[Шаблон:Не перекладено|Не перекладено]]}} вікі-посиланнями на перекладені статті"
            self.userPut(page, page.text, text, summary=summary)
        elif self.getOption("replace"):
            pywikibot.output(
                "Page [[%s]] was not changed because of the above problems"
                % page.title()
            )
            pywikibot.output("=" * 80)
        elif not self.ok:
            pywikibot.output("Page [[%s]] has the above problems" % page.title())
            pywikibot.output("=" * 80)

    def iwanalyze(self, page, pageText, iw):
        # Extract all fields
        try:
            treba, tekst, mova, ee = self.getFields(pageText, iw)
        except IwExc:
            self.addProblem(
                page,
                "Page contains bare \03{blue}{{tl|Не перекладено}}\03{default} without parameters!",
            )
            return

        # Find, whether the page was translated
        if not mova in wikicodes:
            self.addProblem(
                page, 'Language code \03{blue}"%s"\03{default} is not supported!' % mova
            )
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
            except KeyboardInterrupt:
                raise KeyboardInterrupt
            except:
                self.addProblem(
                    page,
                    "Data item \03{blue}[[:%s:%s]]\03{default} does not exist!"
                    % (mova, ee),
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
                        page,
                        "\n\n>>> Page \03{blue}[[:%s:%s]]\03{default} does not exist! <<<"
                        % (mova, ee),
                    )
                    if self.getOption("ignwarn"):
                        if self.user_confirm(
                            'Do you want to replace "%s" with wikilink?' % iw.text
                        ):
                            return treba, tekst
                    return
            except KeyboardInterrupt:
                raise KeyboardInterrupt
            except:
                self.addProblem(
                    page,
                    "\n\n>>> Something is wrong with a title \03{blue}[[:%s:%s]]\03{default}! <<<"
                    % (mova, ee),
                )
                return

            try:
                item = pywikibot.ItemPage.fromPage(eePage)
                item.get()
                WikidataID = item.id
                sitelinks = item.sitelinks
                if "ukwiki" in sitelinks.keys():
                    tranlsatedInto = sitelinks["ukwiki"]
            except KeyboardInterrupt:
                raise KeyboardInterrupt
            except:
                if redirect:
                    self.addProblem(
                        page,
                        "\n\n>>> Page \03{blue}[[:%s:%s]] (← [[:%s:%s]])\03{default} does not have Wikidata element! <<<"
                        % (mova, redirectTitle, mova, ee),
                    )
                else:
                    self.addProblem(
                        page,
                        "\n\n>>> Page \03{blue}[[:%s:%s]]\03{default} does not have Wikidata element! <<<"
                        % (mova, ee),
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
            except KeyboardInterrupt:
                raise KeyboardInterrupt
            except:
                self.addProblem(
                    page,
                    "\n\n>>> Something is wrong with a title \03{blue}%s\03{default}! <<<"
                    % (conv2wikilink(treba)),
                )
                return
        else:
            self.addProblem(
                page,
                "\n\n>>> Template \03{blue}%s\03{default} does not have any page title! <<<"
                % iw.text,
            )
            return

        if HEREexist:
            try:
                HEREitem = pywikibot.ItemPage.fromPage(trebaPage)
                HEREitem.get()
                HEREWikidataID = HEREitem.id
            except KeyboardInterrupt:
                raise KeyboardInterrupt
            except:
                self.addProblem(
                    page,
                    "\n\n>>> Page \03{blue}%s\03{default} does not have Wikidata element! <<<"
                    % conv2wikilink(treba),
                )
                return

        # Add it to the global list
        if not WikidataID in self.IwItems.keys():
            self.IwItems[WikidataID] = []
        self.IwItems[WikidataID].append(
            {
                "pageToTranslate": {
                    "lang": mova,
                    "title": ee,
                    "redirect": redirect,
                    "redirectTitle": redirectTitle,
                    "translatedInto": tranlsatedInto,
                },
                "requiredPage": {
                    "title": treba,
                    "text": tekst,
                    "exist": HEREexist,
                    "redirect": HEREredirect,
                    "redirectTitle": HEREredirectTitle,
                    "WikidataID": HEREWikidataID,
                },
                "inPage": page.title(),
            }
        )

        # Make text substitutions for pages that translated, but first check them
        if HEREexist:
            # if not self.getOption('replace'):
            #    return

            if WikidataID == HEREWikidataID:
                if not HEREredirect:
                    self.ok = self.ok & True
                    return treba, tekst
                else:
                    self.addProblem(
                        page,
                        "\n\n>>> Page \03{blue}%s\03{default} redirects to \03{blue}%s\03{default}! <<<"
                        % (conv2wikilink(treba), conv2wikilink(HEREredirectTitle)),
                    )
                    if self.getOption("ignwarn"):
                        if tekst == u"":
                            if self.user_confirm(
                                'Do you want to replace "%s" with [[%s]]?'
                                % (iw.text, HEREredirectTitle)
                            ):
                                return HEREredirectTitle, tekst
                            if self.user_confirm(
                                'Do you want to replace "%s" with [[%s]]?'
                                % (
                                    iw.text,
                                    HEREredirectTitle[0:1].lower()
                                    + HEREredirectTitle[1:],
                                )
                            ):
                                return (
                                    HEREredirectTitle[0:1].lower()
                                    + HEREredirectTitle[1:],
                                    tekst,
                                )
                            if self.user_confirm(
                                'Do you want to replace "%s" with [[%s]]?'
                                % (iw.text, treba)
                            ):
                                return treba, tekst
                        elif (treba[0:1].lower() + treba[1:]) == (
                            tekst[0:1].lower() + tekst[1:]
                        ):
                            if self.user_confirm(
                                'Do you want to replace "%s" with [[%s]]?'
                                % (iw.text, HEREredirectTitle)
                            ):
                                return HEREredirectTitle, HEREredirectTitle
                            if self.user_confirm(
                                'Do you want to replace "%s" with [[%s]]?'
                                % (
                                    iw.text,
                                    HEREredirectTitle[0:1].lower()
                                    + HEREredirectTitle[1:],
                                )
                            ):
                                return (
                                    HEREredirectTitle[0:1].lower()
                                    + HEREredirectTitle[1:],
                                    HEREredirectTitle[0:1].lower()
                                    + HEREredirectTitle[1:],
                                )
                            if self.user_confirm(
                                'Do you want to replace "%s" with [[%s]]?'
                                % (iw.text, tekst)
                            ):
                                return tekst, tekst
                        else:
                            if self.user_confirm(
                                'Do you want to replace "%s" with [[%s|%s]]?'
                                % (iw.text, HEREredirectTitle, tekst)
                            ):
                                return HEREredirectTitle, tekst
                            if self.user_confirm(
                                'Do you want to replace "%s" with [[%s|%s]]?'
                                % (iw.text, treba, tekst)
                            ):
                                return treba, tekst
            else:
                self.addProblem(
                    page,
                    "\n\n>>> Pages \03{blue}[[:%s:%s]]\03{default} and \03{blue}%s\03{default} link to different Wikidata items! <<<"
                    % (mova, ee, conv2wikilink(treba)),
                )
                return
        elif tranlsatedInto:
            if redirect:
                self.addProblem(
                    page,
                    "\n\n>>> Page \03{blue}[[:%s:%s]] (→ [[:%s:%s]])\03{default} is translated into \03{blue}%s\03{default}, while requested \03{blue}%s\03{default}! <<<"
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
                    "\n\n>>> Page \03{blue}[[:%s:%s]]\03{default} is translated into \03{blue}%s\03{default}, while requested \03{blue}%s\03{default}! <<<"
                    % (mova, ee, conv2wikilink(tranlsatedInto), conv2wikilink(treba)),
                )

            if not (self.getOption("replace") and self.getOption("ignwarn")):
                return

            if tekst == "":
                tekst = treba
            if self.user_confirm(
                'Do you want to replace "%s" with [[%s|%s]]?'
                % (iw.text, tranlsatedInto, tekst)
            ):
                return tranlsatedInto, tekst
            if self.user_confirm(
                'Do you want to replace "%s" with [[%s]]?' % (iw.text, tranlsatedInto)
            ):
                return tranlsatedInto, tranlsatedInto
            if self.user_confirm(
                'Do you want to replace "%s" with [[%s]]?'
                % (iw.text, tranlsatedInto[0:1].lower() + tranlsatedInto[1:])
            ):
                return (
                    tranlsatedInto[0:1].lower() + tranlsatedInto[1:],
                    tranlsatedInto[0:1].lower() + tranlsatedInto[1:],
                )
            else:
                return

    def addProblem(self, page, message):
        page_title = page.title()
        if not page_title in self.problems.keys():
            self.problems[page_title] = []
        plainmessage = re.sub(r"\03\{[^}]*\}", r"", message, re.UNICODE)
        plainmessage = re.sub(r"\n\n>>> ", r"", plainmessage, re.UNICODE)
        plainmessage = re.sub(r" <<<", r"", plainmessage, re.UNICODE)
        plainmessage = re.sub(r"!", r"", plainmessage, re.UNICODE)
        self.problems[page_title].append(plainmessage)
        pywikibot.output(message)
        self.ok = False

    def iwreplace(self, pageText, iw, treba="", tekst=""):
        if tekst == "":
            pageText = pageText[: iw.start] + u"[[" + treba + u"]]" + pageText[iw.end :]
        elif (treba[0:1].lower() + treba[1:]) == (
            tekst[0:1].lower() + tekst[1:]
        ):  # for cases like {{Не перекладено|Марковська модель|марковська модель||Markov model}}
            pageText = pageText[: iw.start] + u"[[" + tekst + u"]]" + pageText[iw.end :]
        else:
            pageText = (
                pageText[: iw.start]
                + u"[["
                + treba
                + u"|"
                + tekst
                + u"]]"
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

    def analyzeIwItems(self):
        report = '{| class="standard sortable"\n'
        report += "! Вікідані || Треба перекласти || Сторінки до перекладу || Запит на переклад зі сторінок || Кількість посилань з основного простору || Кількість статей в інших розділах Вікімедіа\n"
        Nitem = 0
        for item in sorted(self.IwItems.keys()):
            Nitem += 1
            Nrequests = (
                0
            )  # Number of requests made with template {{iw}} in all namespaces
            Nrefs = (
                0
            )  # Number of referencies to the requested treba pages in namespace 0
            lPrefs = []  # List of referencies
            lTreba = []
            sTreba = ""
            lMovaE = []
            sMovaE = ""
            lPages = []
            sPages = ""
            Nsitelinks = 0
            translatedInto = None

            for request in self.IwItems[item]:
                Nrequests += 1
                treba = request["requiredPage"]["title"]
                treba = treba[0:1].lower() + treba[1:]
                if not treba in lTreba:
                    # Nrefs += sum(1 for _ in pywikibot.Page(self.botsite, treba).getReferences(namespaces=0,follow_redirects=False))
                    for Pref in pywikibot.Page(self.botsite, treba).getReferences(
                        namespaces=0, follow_redirects=False
                    ):  # Requires more memory
                        if not Pref in lPrefs:
                            lPrefs.append(Pref)
                            Nrefs += 1
                    lTreba.append(treba)
                    if Nrequests > 1:
                        sTreba += "<br>"
                    sTreba += conv2wikilink(request["requiredPage"]["title"])
                    translatedInto = request["pageToTranslate"]["translatedInto"]
                    if translatedInto:
                        if item == request["requiredPage"]["WikidataID"]:
                            sTreba += " (перекладено)"

                ee = request["pageToTranslate"]["title"]
                movaEcurrent = (
                    request["pageToTranslate"]["lang"] + ":" + ee[0:1].lower() + ee[1:]
                )
                if not (movaEcurrent) in lMovaE:
                    lMovaE.append(movaEcurrent)
                    if Nrequests > 1:
                        sMovaE += "<br>"
                    sMovaE += "[[:%s:%s]]" % (
                        request["pageToTranslate"]["lang"],
                        request["pageToTranslate"]["title"],
                    )
                    if request["pageToTranslate"]["redirect"]:
                        sMovaE += " (→ [[:%s:%s]])" % (
                            request["pageToTranslate"]["lang"],
                            request["pageToTranslate"]["redirectTitle"],
                        )

                    try:
                        itemtmp = pywikibot.ItemPage.fromPage(
                            pywikibot.Page(
                                pywikibot.Site(
                                    request["pageToTranslate"]["lang"], "wikipedia"
                                ),
                                request["pageToTranslate"]["title"],
                            )
                        )
                        itemtmp.get()
                        Nsitelinks = len(itemtmp.sitelinks.keys())
                    except:
                        Nsitelinks = 1

                if not request["inPage"] in lPages:
                    nTransculsions = None
                    lPages.append(request["inPage"])
                    if Nrequests > 1:
                        sPages += "<br>"
                    if request["inPage"][0:7] == "Шаблон:":
                        nTransculsions = sum(
                            1
                            for _ in pywikibot.Page(
                                self.botsite, request["inPage"]
                            ).getReferences(
                                onlyTemplateInclusion=True, follow_redirects=False
                            )
                        )

                    sPages += conv2wikilink(request["inPage"])

                    if request["inPage"] in self.problems.keys():
                        sPages += "*"

                    if nTransculsions:
                        Nrequests += nTransculsions
                        sPages += " (включень: %d)" % nTransculsions

            if translatedInto and not (" (перекладено)" in sTreba):
                sTreba += "<br>(вже є %s)" % conv2wikilink(translatedInto)

            # report += '|-\n| [[d:%s]] || %s || %s || %s || %d\n' % (item, sTreba, sMovaE, sPages, Nrequests)
            report += "|-\n| [[d:%s]] || %s || %s || %s || %d || %d\n" % (
                item,
                sTreba,
                sMovaE,
                sPages,
                Nrefs,
                Nsitelinks,
            )
            lPrefs = []  # List of referencies

        from time import gmtime, strftime

        report = (
            """== Список неперекладених сторінок ==

Список статей, для яких використано [[Шаблон:Не перекладено]], станом на %s. Всього таких статей %d.

Позначення: 
* Треба перекласти:
** «(перекладено)» — вказує, що сторінка перекладена в потрібну статтю і шаблон Не перекладено можна прибрати
** «(вже є <nowiki>[[назва статті]]</nowiki>)» — вказує, що сторінка вже можливо перекладена в потрібну статтю і шаблон Не перекладено можна прибрати
* Сторінки до перекладу:
** «(→ <nowiki>[[назва статті]]</nowiki>)» — показує, куди сторінку в іншомовному розділі перенаправляє
* Запит на переклад зі сторінок:
** «*» — сторінки відмічені мають [[#Сторінки, які можливо потребують уваги|потенційні проблеми]], тому перевірте їх
** «(включень: n)» — кількість включень шаблонів (додається до числа в колонці «Необхідна у наступній кількості випадків»)

"""
            % (strftime("%d.%m.%Y, %H:%M:%S", gmtime()), Nitem)
            + report
        )
        report += "|}"

        pywikibot.output(report)

        self.report = report
        self.Nitems = Nitem

    def analyzeProblems(self):
        probl = '{| class="standard sortable"\n'
        probl += "! Стаття з проблемами || Error message || N\n"
        NproblemPages = 0
        for problem in sorted(self.problems.keys()):
            NproblemPages += 1
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
            % (strftime("%d.%m.%Y, %H:%M:%S", gmtime()), NproblemPages, probl)
        )

        pywikibot.output(probl)

        self.reportProblems = probl
        self.NproblemPages = NproblemPages


class ReportByTopicBot(GenBot):
    lpages = []
    lpagesExclude = []

    def __init__(self):
        """Constructor."""
        # Allowed command line arguments (in addition to global ones)
        # and their associated options with default values
        args = {
            "-reportbytopic": {"reportbytopic": False},
            "-loadreport": {"loadreport": False},
            "-dumpreport": {"dumpreport": False},
            "-replace": {"replace": True},
            "-report": {"report": False},
            "-dumpreport": {"dumpreport": False},
            "-maxpages": {"maxpages": "all"},
            "-notsafe": {"notsafe": False},
            "-ignwarn": {"ignwarn": False},
            "-help": {"help": False},
        }

        self.botsite = None
        super(ReportByTopicBot, self).__init__(showHelp="iw", addargs=args)

        self.generalPages = {
            "Report": {
                "title": "Користувач:PavloChemBot/Неперекладені сторінки",
                #'title': 'PavloChemBot/Неперекладені сторінки',
                "minNoRequests": 100,
            },
            "Problems": 'Користувач:PavloChemBot/Сторінки з невірно використаним шаблоном "Не перекладено"',
        }
        #'PavloChemBot/Сторінки з невірно використаним шаблоном "Не перекладено"'}

        self.topics = {}
        site = pywikibot.Site("uk", "wikipedia")

        page = pywikibot.Page(
            site, "Вікіпедія:Проект:Біологія/Неперекладені статті/Категорії"
        )
        self.topics["Біологія"] = json.loads(page.text)
        self.topics["Біологія"][
            "page"
        ] = "Вікіпедія:Проект:Біологія/Неперекладені статті"

        page = pywikibot.Page(
            site, "Користувач:PavloChemBot/Неперекладені сторінки/Хімія/Категорії"
        )
        self.topics["Хімія"] = json.loads(page.text)
        self.topics["Хімія"][
            "page"
        ] = "Користувач:PavloChemBot/Неперекладені сторінки/Хімія"

        page = pywikibot.Page(
            site, "Користувач:PavloChemBot/Неперекладені сторінки/Математика/Категорії"
        )
        self.topics["Математика"] = json.loads(page.text)
        self.topics["Математика"][
            "page"
        ] = "Користувач:PavloChemBot/Неперекладені сторінки/Математика"

    def run(self):
        if not self.getOption("reportbytopic"):
            if self.getOption("report"):
                self.iwrobot = IwBot()
                self.iwrobot.run()
                self.updatePages()
            else:
                IwBot().run()
            return

        # self.iwrobot = IwBot(locargs = ['-ref:Шаблон:Не перекладено', '-catr:Навігаційні шаблони:Математика', '-maxpages:10', '-intersect', '-report'])
        if self.getOption("dumpreport"):
            self.iwrobot = IwBot(
                locargs=["-ref:Шаблон:Не перекладено", "-report", "-dumpreport"]
            )
            self.iwrobot.run()
            self.updatePages()
        elif self.getOption("loadreport"):
            self.iwrobot = IwBot(
                locargs=["-ref:Шаблон:Не перекладено", "-report", "-loadreport"]
            )
            # self.iwrobot.run()
            self.iwrobot.IwItems = load_obj("IwItems")
            self.iwrobot.problems = load_obj("problems")
        else:
            self.iwrobot = IwBot(locargs=["-ref:Шаблон:Не перекладено", "-report"])
            self.iwrobot.run()
            self.updatePages()

        # self.topicReport('Біологія')
        for topic in sorted(self.topics.keys()):
            self.topicReport(topic)

    def updatePages(self):
        # self.iwrobot.analyzeIwItems()
        report = self.iwrobot.report

        tmpspl = report.split("\n")
        lines = []
        for line in tmpspl:
            if "Всього таких статей" in line:
                line += (
                    " Показані лише найбільш поширені в інших розділах Вікімедіа (статей не менше %d)."
                    % self.generalPages["Report"]["minNoRequests"]
                )
            if (
                "[[#Сторінки, які можливо потребують уваги|потенційні проблеми]]"
                in line
            ):
                line = line.replace(
                    "#Сторінки, які можливо потребують уваги",
                    self.generalPages["Problems"],
                )
            if "| [[d:" in line[: len("| [[d:")]:
                if int(line.split()[-1]) < self.generalPages["Report"]["minNoRequests"]:
                    del lines[-1]
                    continue
            lines.append(line)

        report = "== Не перекладені сторінки за темами ==\n"
        for topic in sorted(self.topics.keys()):
            report += "* [[%s|%s]]\n" % (self.topics[topic]["page"], topic)
        report += "\n"

        for line in lines:
            report += line + "\n"

        # self.iwrobot.analyzeProblems()
        reportProblems = self.iwrobot.reportProblems

        # Put reports:
        summary = "[[User:PavloChemBot/Iw|автоматичне оновлення]] таблиць"
        page = pywikibot.Page(self.botsite, self.generalPages["Report"]["title"])
        self.userPut(page, page.text, report, summary=summary)
        page = pywikibot.Page(self.botsite, self.generalPages["Problems"])
        self.userPut(page, page.text, reportProblems, summary=summary)

    def topicReport(self, topic):
        start = time.time()

        # Prepare list of topic pages
        cats = self.topics[topic]["cats"]
        catexc = self.topics[topic]["catexc"]
        pagetitle = self.topics[topic]["page"]

        # Get all pages transcluding {{iw}} template
        locargscat = ["-ref:Шаблон:Не перекладено"]
        findBot = GenBot(showHelp="iw", locargs=locargscat)
        alliwpages = [page.title() for page in findBot.generator]
        pywikibot.output(
            "Finished getting all pages transcluding iw template after %.1f seconds"
            % (time.time() - start)
        )

        # Get all categories in the topic
        lcats = []
        catText = ""
        for cat in cats:
            catText += "* [[:Категорія:%s]] (%d)\n" % (cat["title"], cat["depth"])
            lcats += [cat["title"]]
            if cat["depth"] > 0:
                pywikicat = pywikibot.Category(self.botsite, cat["title"])
                lcats += [
                    subcat.title()
                    for subcat in pywikicat.subcategories(recurse=cat["depth"])
                ]
        pywikibot.output(
            "Finished collecting categories to include into the topic topic after %.1f seconds"
            % (time.time() - start)
        )

        # Get all categories that should be excluded from the topic
        lcatsExclude = []
        catexcText = ""
        for cat in catexc:
            catexcText += "* [[:Категорія:%s]] (%d)\n" % (cat["title"], cat["depth"])
            lcatsExclude += [cat["title"]]
            if cat["depth"] > 0:
                pywikicat = pywikibot.Category(self.botsite, cat["title"])
                lcatsExclude += [
                    subcat.title()
                    for subcat in pywikicat.subcategories(recurse=cat["depth"])
                ]
        pywikibot.output(
            "Finished collecting categories to exclude from the topic after %.1f seconds"
            % (time.time() - start)
        )

        # Get all required categories
        lcatsreduced = [cat for cat in lcats if not cat in lcatsExclude]
        pywikibot.output(
            "Finished collecting all required categories after %.1f seconds"
            % (time.time() - start)
        )

        # Get all pages in the topic
        locargscat = []
        for catname in lcatsreduced:
            locargscat.append("-cat:%s" % catname)
        findBot = GenBot(showHelp="iw", locargs=locargscat)
        self.lpages = []
        for page in findBot.generator:
            if page.title() in alliwpages:
                self.lpages.append(page.title())
        pywikibot.output(
            "Finished collecting pages in the topic after %.1f seconds"
            % (time.time() - start)
        )

        """
        self.lpages = []
        self.lpagesExclude = []
        catexcText = ''
        for cate in catexc:
            catexcText += '* [[:Категорія:%s]] (%d)\n' % (cate['title'], cate['depth'])
            self.findPages(cate['title'], cate['depth'])
        self.lpagesExclude = self.lpages[:]
        pywikibot.output('Finished collecting pages to exclude from topic after %.1f seconds' % (time.time() - start))

        self.lpages = []
        catText = ''
        for cat in cats:
            catText += '* [[:Категорія:%s]] (%d)\n' % (cat['title'], cat['depth'])
            self.findPages(cat['title'], cat['depth'])
        self.lpagesExclude = []
        pywikibot.output('Finished collecting pages to include into topic topic after %.1f seconds' % (time.time() - start))
        """

        header = """На цій сторінці зібрані неперекладені статті з теми «%s».

Сторінка автоматично оновлюється ботом на основі пошуку в наступних категоріях (глибина рекурсивного пошуку в дужках):
%s
за виключенням таких категорій (глибина рекурсивного пошуку в дужках):
{{стовпці|3}}
%s</div>""" % (
            topic,
            catText,
            catexcText,
        )

        pywikibot.output(header)

        # Prepare list of not translated pages
        oldIwItems = self.iwrobot.IwItems
        newIwItems = {}
        for item in oldIwItems.keys():
            for request in oldIwItems[item]:
                page = request["inPage"]
                if page in self.lpages:
                    if not item in newIwItems:
                        newIwItems[item] = []
                    newIwItems[item].append(request)
        NitemsPerPage = 2000
        Npages = len(newIwItems) / NitemsPerPage
        if Npages > 1:
            report = (
                "Оскільки кількість статей більше ніж удвічі перевищує %d, ця сторінка розбита на %d підсторінок:\n\n"
                % (NitemsPerPage, Npages)
            )
            itemKeys = sorted(newIwItems.keys())
            itemKeysChunks = []
            for Npage in range(Npages - 1):
                report += "[[%s/%d|%d]] • " % (pagetitle, (Npage + 1), (Npage + 1))
                itemKeysChunks.append(
                    itemKeys[
                        Npage * NitemsPerPage : Npage * NitemsPerPage + NitemsPerPage
                    ]
                )
            report += "[[%s/%d|%d]]\n" % (pagetitle, Npages, Npages)
            itemKeysChunks.append(itemKeys[(Npages - 1) * NitemsPerPage :])
            for Npage in range(Npages):
                self.iwrobot.IwItems = {}
                for itemKey in itemKeysChunks[Npage]:
                    self.iwrobot.IwItems[itemKey] = newIwItems[itemKey]
                self.iwrobot.analyzeIwItems()
                reportPage = self.iwrobot.report
                page = pywikibot.Page(self.botsite, pagetitle + "/%d" % (Npage + 1))
                summary = "[[User:PavloChemBot/Iw|автоматичне оновлення]] таблиць"
                self.userPut(page, page.text, reportPage, summary=summary)
            self.iwrobot.IwItems = oldIwItems
        else:
            self.iwrobot.IwItems = newIwItems
            self.iwrobot.analyzeIwItems()
            report = self.iwrobot.report
            self.iwrobot.IwItems = oldIwItems
        pywikibot.output(
            "Finished preparing list of not translated pages after %.1f seconds"
            % (time.time() - start)
        )

        # Prepare list of problems
        oldProblems = self.iwrobot.problems
        newProblems = {}
        for page in oldProblems.keys():
            if page in self.lpages:
                if not page in newProblems:
                    newProblems[page] = []
                newProblems[page] = oldProblems[page]
        self.iwrobot.problems = newProblems
        self.iwrobot.analyzeProblems()
        reportProblems = self.iwrobot.reportProblems
        self.iwrobot.problems = oldProblems
        self.lpages = []
        lcatsreduced = []
        lcats = []
        lcatsExclude = []
        pywikibot.output(
            "Finished preparing list of problems after %.1f seconds"
            % (time.time() - start)
        )

        # Put reports:
        page = pywikibot.Page(self.botsite, pagetitle)
        text = header + "\n" + report + "\n\n" + reportProblems
        summary = "[[User:PavloChemBot/Iw|автоматичне оновлення]] таблиць"
        self.userPut(page, page.text, text, summary=summary)
        pywikibot.output(
            "Finished putting report after %.1f seconds" % (time.time() - start)
        )

    def findPages(self, catname, catrdepth):
        if catrdepth == "infinite":
            locargscat = [
                "-ref:Шаблон:Не перекладено",
                "-catr:%s" % catname,
                "-intersect",
            ]
        else:
            locargscat = [
                "-ref:Шаблон:Не перекладено",
                "-catr:%s" % catname,
                "-intersect",
                "-catrdepth:%d" % catrdepth,
            ]
        findBot = GenBot(showHelp="iw", locargs=locargscat)
        for page in findBot.generator:
            if page.title() in self.lpagesExclude or page.title() in self.lpages:
                continue
            self.lpages.append(page.title())

        """
        sys.exit()
        catexc = ['Категорія:Місця']
        allcats = []
        for catname in cats:
            cat = pywikibot.Category(self.botsite, catname)
            allcats.append(cat)
            for subcat in cat.subcategories(recurse=True):
                if subcat.title() in catexc:
                    continue
                allcats.append(subcat)
        print allcats
        
        #robot = IwBot(locargs = ['-ref:Шаблон:Не перекладено', '-catr:Математика', '-intersect', '-report'])
        robot = IwBot(locargs = ['-ref:Шаблон:Не перекладено', '-maxpages:2', '-report'])
        robot.run()
        for item in robot.IwItems:
            for request in robot.IwItems[item]:
                page = pywikibot.Page(self.botsite, request['inPage'])
                for cat in page.categories():
                    print cat.title()
                    #print cat.subcategories()
        """


if __name__ == "__main__":
    # IwBot(locargs = ['-page:Користувач:Pavlo Chemist/Чернетка', '-report']).run()
    # IwBot(locargs = ['-page:Користувач:Pavlo Chemist/Чернетка']).run()
    # IwBot(locargs = ['-cat:Вікіпедія:Статті з неактуальним шаблоном Не перекладено']).run()
    # IwBot().run()
    # python pwb.py iw -cat:"Вікіпедія:Статті з неактуальним шаблоном Не перекладено"
    # python pwb.py iw -ref:"Шаблон:Не перекладено" -report
    # python pwb.py iw -page:"Користувач:Pavlo Chemist/Чернетка"

    robot = ReportByTopicBot()
    robot.run()
