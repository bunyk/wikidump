#!/usr/bin/python
"""
(C) Wikipedia user Pavlo Chemist, 2015-2019
Distributed under the terms of the MIT license.

This is general module with functions and classes
              to be re-used by other Bots

            
    Distributed under the terms of the MIT license

New global options:
-catrdepth:n      defines depth of n recursion for -catr option

Pages to work on:
&params;
"""
import pywikibot
from pywikibot import Bot, pagegenerators
import sys, re

docuReplacements = {"&params;": pagegenerators.parameterHelp}


class GenBot(Bot):
    """
    Generic Bot
    """

    Ntotal = 0
    Nchangedpages = 0
    Nnotchanged = 0
    all_args = []

    def __init__(self, showHelp="generalmodule", addargs={}, locargs=[]):
        """Constructor."""
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
            # pywikibot.showHelp(showHelp)
            super(GenBot, self).__init__(**options)
        else:
            preloadingGen = pagegenerators.PreloadingGenerator(gen)
            super(GenBot, self).__init__(generator=preloadingGen, **options)

    def run(self):
        raise NotImplementedError(
            "Method %s.run() not implemented." % self.__class__.__name__
        )

    @classmethod
    def findInterwiki(cls, page):
        iwikis = {}
        for iwiki in re.finditer(
            "\[\[(?P<lang>[a-z-]+)\:(?P<title>[^]]+)\]\]",
            page.text,
            flags=re.UNICODE | re.MULTILINE | re.DOTALL | re.IGNORECASE,
        ):
            lang = iwiki.group("lang")
            if lang in wikicodes:
                iwikis[lang] = iwiki.group("title")
        return iwikis

    @classmethod
    def setSitelink(item, sitename, title, summary):
        global args

        # https://www.mediawiki.org/wiki/Manual:Pywikibot/Wikidata

        if sitename in item.sitelinks.keys():
            if item.sitelinks[sitename] == title:
                pywikibot.output(
                    'Wikidata item ID (%s) already has a link "%s" to %s'
                    % (item.id, title, sitename)
                )
            else:
                pywikibot.output(
                    'You try to set link "%s" to %s for Wikidata item ID (%s) that already has a link "%s"'
                    % (title, sitename, item.id, item.sitelinks[sitename])
                )
            return

        if self.user_confirm(
            "Do you want to set link %s:%s to the Wikidata?" % (sitename, title)
        ):
            if item:
                item.setSitelink(
                    sitelink={"site": sitename, "title": title}, summary=summary
                )


class testBot(GenBot):
    def __init__(self):
        """Constructor."""
        # Allowed command line arguments (in addition to global ones)
        # and their associated options with default values
        args = {"-verbose": {"verbose": True}, "-testarg": {"testarg": ""}}

        super(testBot, self).__init__(addargs=args)

    def run(self):
        if self.getOption("testarg"):
            print("TESTARG = ", self.getOption("testarg"))
        for page in self.generator:
            print(page.title())
            # self.userPut(page, page.text, '', summary='Test edit')


wikicodes = [
    "en",
    "sv",
    "nl",
    "de",
    "fr",
    "war",
    "ru",
    "ceb",
    "it",
    "es",
    "vi",
    "pl",
    "ja",
    "pt",
    "zh",
    "uk",
    "ca",
    "fa",
    "no",
    "sh",
    "fi",
    "ar",
    "id",
    "ro",
    "cs",
    "sr",
    "ko",
    "h",
    "ms",
    "tr",
    "min",
    "eo",
    "kk",
    "e",
    "sk",
    "da",
    "bg",
    "he",
    "lt",
    "hy",
    "hr",
    "sl",
    "et",
    "uz",
    "gl",
    "nn",
    "vo",
    "la",
    "simple",
    "el",
    "hi",
    "az",
    "ka",
    "th",
    "ce",
    "oc",
    "be",
    "mk",
    "mg",
    "new",
    "ur",
    "ta",
    "tt",
    "pms",
    "cy",
    "tl",
    "bs",
    "lv",
    "te",
    "be-x-old",
    "br",
    "ht",
    "sq",
    "jv",
    "lb",
    "mr",
    "is",
    "ml",
    "zh-yue",
    "bn",
    "af",
    "ga",
    "ba",
    "pnb",
    "cv",
    "tg",
    "fy",
    "lmo",
    "sco",
    "my",
    "yo",
    "an",
    "ky",
    "sw",
    "ne",
    "io",
    "g",
    "scn",
    "bpy",
    "nds",
    "k",
    "ast",
    "q",
    "als",
    "s",
    "pa",
    "kn",
    "ckb",
    "mn",
    "ia",
    "nap",
    "bug",
    "bat-smg",
    "arz",
    "wa",
    "zh-min-nan",
    "am",
    "gd",
    "map-bms",
    "yi",
    "mzn",
    "si",
    "fo",
    "bar",
    "nah",
    "vec",
    "sah",
    "os",
    "sa",
    "mrj",
    "li",
    "roa-tara",
    "hsb",
    "or",
    "pam",
    "mhr",
    "se",
    "mi",
    "ilo",
    "bcl",
    "hif",
    "gan",
    "ps",
    "rue",
    "glk",
    "nds-nl",
    "bo",
    "vls",
    "diq",
    "bh",
    "fiu-vro",
    "xmf",
    "tk",
    "gv",
    "sc",
    "co",
    "csb",
    "km",
    "hak",
    "vep",
    "kv",
    "zea",
    "crh",
    "frr",
    "zh-classical",
    "eml",
    "ay",
    "wuu",
    "udm",
    "stq",
    "nrm",
    "kw",
    "rm",
    "so",
    "szl",
    "koi",
    "as",
    "lad",
    "fur",
    "mt",
    "gn",
    "dv",
    "ie",
    "dsb",
    "pcd",
    "sd",
    "lij",
    "cbk-zam",
    "cdo",
    "ksh",
    "ext",
    "mwl",
    "gag",
    "ang",
    "ug",
    "ace",
    "pi",
    "pag",
    "lez",
    "nv",
    "frp",
    "sn",
    "kab",
    "myv",
    "ln",
    "pfl",
    "xal",
    "krc",
    "haw",
    "rw",
    "kaa",
    "pdc",
    "to",
    "kl",
    "arc",
    "nov",
    "kbd",
    "av",
    "bxr",
    "lo",
    "bjn",
    "ha",
    "tet",
    "tpi",
    "pap",
    "na",
    "lbe",
    "jbo",
    "ty",
    "mdf",
    "tyv",
    "roa-rup",
    "wo",
    "ig",
    "srn",
    "nso",
    "kg",
    "ab",
    "ltg",
    "z",
    "om",
    "chy",
    "za",
    "c",
    "rmy",
    "tw",
    "mai",
    "tn",
    "chr",
    "pih",
    "xh",
    "bi",
    "got",
    "sm",
    "ss",
    "mo",
    "rn",
    "ki",
    "pnt",
    "bm",
    "i",
    "ee",
    "lg",
    "ak",
    "ts",
    "fj",
    "ik",
    "st",
    "sg",
    "ks",
    "ff",
    "dz",
    "ny",
    "ch",
    "ti",
    "ve",
    "tum",
    "cr",
    "ng",
    "cho",
    "kj",
    "mh",
    "ho",
    "ii",
    "aa",
    "mus",
    "hz",
    "kr",
    "be-tarask",
    "cz",
    "d",
]  # Aliases and Wikidata


class TmplError(Exception):
    def __init__(self, message):
        self.message = message

    def __repr__(self):
        return 'Template "%s" is probably broken' % self.message


class TmplCls:
    def __init__(self):
        self.start = 0
        self.end = 0
        self.text = u""


class FieldCls:
    def __init__(self):
        self.start = 0
        self.end = 0
        self.text = u""


class TmplOps(object):
    """ This class handles templates"""

    def __init__(self, text, tmpl):
        self.text = text
        self.tmpl = tmpl

    @classmethod
    def findTmpls(cls, text, tmpl):
        # Find all <nowiki> ... </nowiki> tags
        nowikis = []
        for nowiki in re.finditer(
            "\<nowiki\>.*?\<\/nowiki\>",
            text,
            flags=re.UNICODE | re.MULTILINE | re.DOTALL | re.IGNORECASE,
        ):
            nowikis.append({"start": nowiki.start(), "end": nowiki.end()})

        # Find starting positions of all '{{ <Tmpl>...' and '{{ <tmpl>...'
        lTmpls = []
        retmpl = (
            "\{\{\s*["
            + tmpl[0:1].upper()
            + tmpl[0:1].lower()
            + "]"
            + tmpl[1:]
            + "\s*[}|]"
        )
        tOpens = re.compile(retmpl)
        for tOpen in list(tOpens.finditer(text)):
            # Ignore everything within <nowiki> ... </nowiki> tags
            skip = False
            for nowiki in nowikis:
                if nowiki["start"] < tOpen.start() < nowiki["end"]:
                    skip = True
                    break
            if skip:
                continue
            tmplinst = TmplCls()
            tmplinst.start = tOpen.start()
            lTmpls.append(tmplinst)

        # Finally find all templates and their fields
        for itmpl in range(len(lTmpls)):  # loop over '{{cite' positions
            tmplStart = lTmpls[itmpl].start
            tmplEnd = tmplStart + 2 + len(tmpl) - 1
            ignore = False
            ignore2 = False
            fields = []
            Nofound = 0
            Ncfound = 0
            Nofound2 = 0
            Ncfound2 = 0
            for symb in text[(tmplStart + 2 + len(tmpl)) :]:
                tmplEnd += 1
                if symb == "{":
                    Nofound += 1
                    ignore = True
                elif symb == "}":
                    Ncfound += 1
                    if Ncfound > Nofound:
                        if len(fields) > 0:
                            fields[-1].end = tmplEnd
                            fields[-1].text = text[fields[-1].start : fields[-1].end]
                        break
                    elif Ncfound == Nofound:
                        ignore = False
                elif symb == "[":
                    Nofound2 += 1
                    ignore2 = True
                elif symb == "]":
                    Ncfound2 += 1
                    if Ncfound2 == Nofound2:
                        ignore2 = False
                elif symb == "|" and not ignore and not ignore2:
                    field = FieldCls()
                    field.start = tmplEnd
                    if len(fields) > 0:
                        fields[-1].end = tmplEnd
                        fields[-1].text = text[fields[-1].start : fields[-1].end]
                    fields.append(field)

            # Check for proper template closure:
            if text[tmplEnd + 1 : tmplEnd + 2] != u"}":
                raise TmplError(text[tmplStart:tmplEnd])

            tmplEnd += 2
            lTmpls[itmpl].end = tmplEnd
            lTmpls[itmpl].text = text[tmplStart:tmplEnd]
            lTmpls[itmpl].fields = fields

            """
            print '"%s"' % lTmpls[itmpl].text
            for field in lTmpls[itmpl].fields:
                print field.start, field.end
                print text[field.start:field.end]
                print field.text
            """
        return lTmpls

    @classmethod
    def getField(cls, tmpl, fieldN=None, fieldName=None, getFieldN=False):

        if fieldN:
            if len(tmpl.fields) < fieldN:
                return None
            return tmpl.fields[fieldN - 1].text[1:].strip()

        ifieldN = 0
        if fieldName:
            for field in tmpl.fields:
                ifieldN += 1
                fieldValue = re.search(
                    r"\|\s*%s\s*\=\s*(?P<value>.*)" % fieldName,
                    field.text,
                    flags=re.UNICODE | re.MULTILINE | re.DOTALL | re.IGNORECASE,
                )
                if fieldValue:
                    if getFieldN:
                        return fieldValue.group("value").strip(), ifieldN
                    else:
                        return fieldValue.group("value").strip()

        if getFieldN:
            return None, None
        else:
            return None

    @classmethod
    def getLuaFields(cls, tmpl, lfieldnames=None, getFieldPos=False):
        lfields = [None, None, None, None, None]
        lfieldpos = [None, None, None, None, None]
        lnamedfields = [None for iname in range(len(lfieldnames))]
        lnamedfieldpos = [None for iname in range(len(lfieldnames))]
        lnumfields = [None for iname in range(len(lfieldnames))]
        lnumfieldpos = [None for iname in range(len(lfieldnames))]
        lunnamfields = []
        lunnamfieldpos = []

        # Get named fields:
        for iname in range(len(lfieldnames)):
            lnamedfields[iname], lnamedfieldpos[iname] = cls.getField(
                tmpl, fieldName=lfieldnames[iname], getFieldN=True
            )
        # print lnamedfields, lnamedfieldpos

        # Get numbered fields:
        for iname in range(len(lfieldnames)):
            lnumfields[iname], lnumfieldpos[iname] = cls.getField(
                tmpl, fieldName="%d" % (iname + 1), getFieldN=True
            )
        # print lnumfields, lnumfieldpos

        # Get unnamed fields:
        ipos = 0
        while True:
            ipos += 1
            fieldtemp = cls.getField(tmpl, fieldN=ipos)
            if fieldtemp == None:
                break
            if "=" in fieldtemp:
                continue
            else:
                lunnamfields.append(fieldtemp)
                lunnamfieldpos.append(ipos)
        # print lunnamfields, lunnamfieldpos

        # Get final fields according to priorities
        for iname in range(len(lfieldnames)):
            # named fields always overwrite other fields
            if not (lnamedfields[iname] == None or lnamedfields[iname] == ""):
                lfields[iname] = lnamedfields[iname]
                lfieldpos[iname] = lnamedfieldpos[iname]
            # otherwise the second appearance overwrites the first one
            if lfields[iname] == None or lfields[iname] == "":
                if not (lnumfields[iname] == None or lnumfields[iname] == ""):
                    lfields[iname] = lnumfields[iname]
                    lfieldpos[iname] = lnumfieldpos[iname]
                if iname < len(lunnamfields):
                    if not (lunnamfields[iname] == None or lunnamfields[iname] == ""):
                        if not (lnumfields[iname] == None or lnumfields[iname] == ""):
                            if lunnamfieldpos[iname] < lnumfieldpos[iname]:
                                continue
                        lfields[iname] = lunnamfields[iname]
                        lfieldpos[iname] = lunnamfieldpos[iname]
        # print lfields, lfieldpos

        if getFieldPos:
            return lfields, lfieldpos
        else:
            return lfields


def conv2wikilink(text):
    wikilinktext = ""
    if text[0:5] == "Файл:":
        wikilinktext = "[[:%s]]" % text
    elif text[0:10] == "Категорія:":
        wikilinktext = "[[:%s]]" % text
    else:
        wikilinktext = "[[%s]]" % text
    return wikilinktext


def dump_obj(obj, name):
    import pickle

    with open(name + ".pkl", "wb") as f:
        pickle.dump(obj, f, pickle.HIGHEST_PROTOCOL)


def load_obj(name):
    import pickle

    with open(name + ".pkl", "rb") as f:
        return pickle.load(f)


""" EVERYTHING BELOW IS DEPRICATED - DO NOT USE IT IN NEW SCRIPTS!!!"""
Ntotal = 0
Nchangedpages = 0
Nnotchanged = 0


class ArgsClass(object):
    def __init__(self):
        self.acceptAll = False
        self.simulate = False


args = ArgsClass()


def pageSave(page, originalText, text, summary):
    global Nchangedpages, args

    pywikibot.output(u"\n\n>>> \03{lightpurple}%s\03{default} <<<" % page.title())
    pywikibot.showDiff(originalText, text)

    if originalText.strip() == text.strip():
        pywikibot.output(u"No changes necessary in this page")
        return

    choice = "n"
    if args.acceptAll:
        choice = "y"
    else:
        choice = pywikibot.input_choice(
            u"Do you want to accept these changes?",
            [("Yes", "y"), ("No", "n")],
            default="N",
        )

    if args.simulate:
        pywikibot.output(u"Page will not be changed")
        Nchangedpages += 1
    elif choice == "y":
        try:
            page.put(text, comment=summary)
            Nchangedpages += 1
        except pywikibot.EditConflict:
            pywikibot.output(u"Skipping %s because of edit conflict" % page.title())
        except pywikibot.SpamfilterError as e:
            pywikibot.output(
                u"Cannot change %s because of blacklist entry %s"
                % (page.title(), e.url)
            )
        except pywikibot.LockedPage:
            pywikibot.output(u"Skipping %s (locked page)" % page.title())
        except pywikibot.PageNotSaved as error:
            pywikibot.output(u"Error putting page: %s" % error.args)


def setSitelink(item, sitename, title, summary):
    global args

    # https://www.mediawiki.org/wiki/Manual:Pywikibot/Wikidata

    if sitename in item.sitelinks.keys():
        if item.sitelinks[sitename] == title:
            pywikibot.output(
                'Wikidata item ID (%s) already has a link "%s" to %s'
                % (item.id, title, sitename)
            )
        else:
            pywikibot.output(
                'You try to set link "%s" to %s for Wikidata item ID (%s) that already has a link "%s"'
                % (title, sitename, item.id, item.sitelinks[sitename])
            )
        return

    choice = "n"
    if args.acceptAll:
        choice = "y"
    else:
        choice = pywikibot.input_choice(
            u"Do you want to set link %s:%s to the Wikidata?" % (sitename, title),
            [("Yes", "y"), ("No", "n")],
            default="N",
        )

    if args.simulate:
        pywikibot.output(u"No sitelink will be set")
    elif choice == "y":
        if item:
            item.setSitelink(
                sitelink={"site": sitename, "title": title}, summary=summary
            )


def findInterwiki(page):
    global wikicodes
    iwikis = {}
    for iwiki in re.finditer(
        u"\[\[(?P<lang>[a-z-]+)\:(?P<title>[^]]+)\]\]",
        page.text,
        flags=re.UNICODE | re.MULTILINE | re.DOTALL | re.IGNORECASE,
    ):
        lang = iwiki.group(u"lang")
        if lang in wikicodes:
            iwikis[lang] = iwiki.group(u"title")
    return iwikis


if __name__ == "__main__":
    # Test
    # pagename = u"Користувач:Pavlo Chemist/Чернетка"
    # testBot().run()
    # bot.run()
    """
    site = pywikibot.Site()
    catname = 'Біологія'
    cat = pywikibot.Category(site, catname)
    for subcat in cat.subcategories(recurse=10):
        print subcat.title()
    """
    strtmp = u"""
#::::: Доречі, якщо ви не хочете порушувати сортувальний шаблон, то можна дисципліни перерахувати у дужках після назви вида спорту. Можна їх зробити жирним, курсивом, маленьким або ще якось, щоб воно разом нормально виглядало. Наприклад, ''<nowiki>[[Плавання на Олімпійських іграх|Плавання]]<br />({{не перекладено|Плавання на літніх Олімпійських іграх 2000 – 200 метрів комплексом (жінки)|200 м комплексом||Swimming at the 2000 Summer Olympics – Women's 200 metre individual medley}}),<br />({{не перекладено|Плавання на літніх Олімпійських іграх 2000 – 400 метрів комплексом|400 м комплексом||Swimming at the 2000 Summer Olympics – Women's 400 metre individual medley}}),<br />({{не перекладено|Плавання на літніх Олімпійських іграх 2004 – 200 метрів комплексом (жінки)|200 м комплексом)||Swimming at the 2004 Summer Olympics – Women's 200 metre individual medley}}),<br />({{не перекладено|Плавання на літніх Олімпійських іграх 2004 – 400 метрів комплексом (жінки)|400 м комплексом||Swimming at the 2004 Summer Olympics – Women's 400 metre individual medley}})</nowiki>''. А виглядатиме все це діло наступним чином:<br />
#::::::[[Плавання на Олімпійських іграх|Плавання]]<br />({{не перекладено|Плавання на літніх Олімпійських іграх 2000 – 200 метрів комплексом (жінки)|200 м комплексом||Swimming at the 2000 Summer Olympics – Women's 200 metre individual medley}}),<br />({{не перекладено|Плавання на літніх Олімпійських іграх 2000 – 400 метрів комплексом|400 м комплексом||Swimming at the 2000 Summer Olympics – Women's 400 metre individual medley}}),<br />({{не перекладено|Плавання на літніх Олімпійських іграх 2004 – 200 метрів комплексом (жінки)|200 м комплексом||Swimming at the 2004 Summer Olympics – Women's 200 metre individual medley}}),<br />({{не перекладено|Плавання на літніх Олімпійських іграх 2004 – 400 метрів комплексом (жінки)|400 м комплексом||Swimming at the 2004 Summer Olympics – Women's 400 metre individual medley}})<br />Нічого страшного, що будуть червоні посилання. Я згодом зроблю ці сторінки.--[[Користувач:Waylesange|Waylesange]] ([[Обговорення користувача:Waylesange|обговорення]]) 11:30, 7 вересня 2012 (UTC)
    """
    tmp = TmplOps.findTmpls(strtmp, u"не перекладено")
    tmp = tmp[0]
    print(tmp.text)
    for field in tmp.fields:
        print("-" * 10)
        print(field.text)
