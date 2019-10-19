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

from constants import LANGUAGE_CODES

class GenBot(Bot):
    """
    Generic Bot
    """

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
            super(GenBot, self).__init__(**options)
        else:
            preloadingGen = pagegenerators.PreloadingGenerator(gen)
            super(GenBot, self).__init__(generator=preloadingGen, **options)

    def run(self):
        raise NotImplementedError(
            "Method %s.run() not implemented." % self.__class__.__name__
        )


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

if __name__ == "__main__":
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
