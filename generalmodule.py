import re

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
