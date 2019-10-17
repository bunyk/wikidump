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

docuReplacements = {
    '&params;':     pagegenerators.parameterHelp,
}

class GenBot(Bot):
    """
    Generic Bot
    """
    Ntotal        = 0
    Nchangedpages = 0
    Nnotchanged   = 0
    all_args      = []

    def __init__(self, showHelp='generalmodule', addargs = {}, locargs = []):
        """Constructor."""
        # Allow additional options
        addargs['-catrdepth'] = {'catrdepth': 'infinite'}
        for key in addargs.keys():
            arg = addargs[key]
            k, v = list(arg.items())[0]
            self.availableOptions.update({
                k: v
            })
        
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
        options['catrdepth'] = 'infinite'
        catrargs = []
        for arg in self.all_args:
            if arg.startswith('-catrdepth'):
                options['catrdepth'] = arg.split(':')[1]
            elif arg.startswith('-catr'):
                catrargs.append(arg)
                continue
            elif genFactory.handleArg(arg):
                continue
            elif arg == '-always':
                options['always'] = True
            elif not arg.split(':')[0] in addargs.keys():
                pywikibot.output('Option "%s" is not supported' % arg)
                pywikibot.showHelp(showHelp)
                sys.exit()
            else:
                splarg = arg.split(':')
                argcmd = splarg[0]
                optname = addargs[argcmd].keys()[0]
                if len(splarg) == 1:
                    options[optname] = True
                elif len(splarg) == 2:
                    argvalue = splarg[1]
                    options[optname] = argvalue
                elif len(splarg) > 2:
                    splreg = re.search(r'(?P<argcmd>.*?)\:(?P<argvalue>.*)', arg, flags=re.UNICODE | re.MULTILINE | re.DOTALL | re.IGNORECASE)
                    if splreg:
                        options[optname] = splreg.group(u'argvalue')

        old = False # On non-updated Windows machine, where -cat and -catr work
        if old:
            recurse = True
            if not options['catrdepth'] == 'infinite':
                recurse = int(options['catrdepth'])
            for arg in catrargs:
                gen = genFactory.getCategoryGen(arg, recurse=recurse,
                                          gen_func=pagegenerators.CategorizedPageGenerator)
                if gen:
                    genFactory.gens.append(gen)
        else:
            for arg in catrargs:
                recurse = False
                catname = u''
                if arg.startswith('-catr:'):
                    recurse = True
                    if not options['catrdepth'] == 'infinite':
                        recurse = int(options['catrdepth'])
                    catname = arg[len(u'-catr:'):]
                elif arg.startswith('-cat:'):
                    catname = arg[len(u'-cat:'):]
                gen = genFactory.getCategoryGen(catname, recurse=recurse,
                                          gen_func=pagegenerators.CategorizedPageGenerator)
                if gen:
                    genFactory.gens.append(gen)
        
        gen = genFactory.getCombinedGenerator()
        if not gen:
            #pywikibot.showHelp(showHelp)
            super(GenBot, self).__init__(**options)
        else:
            preloadingGen = pagegenerators.PreloadingGenerator(gen)
            super(GenBot, self).__init__(generator=preloadingGen, **options)

    def run(self):
        raise NotImplementedError('Method %s.run() not implemented.'
                                  % self.__class__.__name__)

    @classmethod
    def findInterwiki(cls, page):
        iwikis = {}
        for iwiki in re.finditer(u'\[\[(?P<lang>[a-z-]+)\:(?P<title>[^]]+)\]\]', page.text, flags=re.UNICODE | re.MULTILINE | re.DOTALL | re.IGNORECASE):
            lang = iwiki.group(u'lang')
            if lang in wikicodes:
                iwikis[lang] = iwiki.group(u'title')
        return iwikis

    @classmethod
    def setSitelink(item, sitename, title, summary):
        global args

        # https://www.mediawiki.org/wiki/Manual:Pywikibot/Wikidata

        if sitename in item.sitelinks.keys():
            if item.sitelinks[sitename] == title:
                pywikibot.output(u'Wikidata item ID (%s) already has a link "%s" to %s' %
                                 (item.id, title, sitename))
            else:
                pywikibot.output(u'You try to set link "%s" to %s for Wikidata item ID (%s) that already has a link "%s"' %
                                 (title, sitename, item.id, item.sitelinks[sitename]))
            return

        if self.user_confirm(u'Do you want to set link %s:%s to the Wikidata?' % (sitename, title)):
            if item:
                item.setSitelink(sitelink={'site': sitename, 'title': title}, summary=summary)

class testBot(GenBot):
    def __init__(self):
        """Constructor."""
        # Allowed command line arguments (in addition to global ones)
        # and their associated options with default values
        args = {'-verbose': {'verbose': True},
                '-testarg': {'testarg': ''}
                }
        
        super(testBot, self).__init__(addargs=args)
        
    def run(self):
        if self.getOption('testarg'):
            print('TESTARG = ', self.getOption('testarg'))
        for page in self.generator:
            print(page.title())
            #self.userPut(page, page.text, u'', summary='Test edit')


wikicodes = [u'en', u'sv', u'nl', u'de', u'fr', u'war', u'ru', u'ceb', u'it',
             u'es', u'vi', u'pl', u'ja', u'pt', u'zh', u'uk', u'ca', u'fa',
             u'no', u'sh', u'fi', u'ar', u'id', u'ro', u'cs', u'sr', u'ko',
             u'hu', u'ms', u'tr', u'min', u'eo', u'kk', u'eu', u'sk', u'da',
             u'bg', u'he', u'lt', u'hy', u'hr', u'sl', u'et', u'uz', u'gl',
             u'nn', u'vo', u'la', u'simple', u'el', u'hi', u'az', u'ka', u'th',
             u'ce', u'oc', u'be', u'mk', u'mg', u'new', u'ur', u'ta', u'tt',
             u'pms', u'cy', u'tl', u'bs', u'lv', u'te', u'be-x-old', u'br',
             u'ht', u'sq', u'jv', u'lb', u'mr', u'is', u'ml', u'zh-yue', u'bn',
             u'af', u'ga', u'ba', u'pnb', u'cv', u'tg', u'fy', u'lmo', u'sco',
             u'my', u'yo', u'an', u'ky', u'sw', u'ne', u'io', u'gu', u'scn',
             u'bpy', u'nds', u'ku', u'ast', u'qu', u'als', u'su', u'pa', u'kn',
             u'ckb', u'mn', u'ia', u'nap', u'bug', u'bat-smg', u'arz', u'wa',
             u'zh-min-nan', u'am', u'gd', u'map-bms', u'yi', u'mzn', u'si',
             u'fo', u'bar', u'nah', u'vec', u'sah', u'os', u'sa', u'mrj',
             u'li', u'roa-tara', u'hsb', u'or', u'pam', u'mhr', u'se', u'mi',
             u'ilo', u'bcl', u'hif', u'gan', u'ps', u'rue', u'glk', u'nds-nl',
             u'bo', u'vls', u'diq', u'bh', u'fiu-vro', u'xmf', u'tk', u'gv',
             u'sc', u'co', u'csb', u'km', u'hak', u'vep', u'kv', u'zea',
             u'crh', u'frr', u'zh-classical', u'eml', u'ay', u'wuu', u'udm',
             u'stq', u'nrm', u'kw', u'rm', u'so', u'szl', u'koi', u'as',
             u'lad', u'fur', u'mt', u'gn', u'dv', u'ie', u'dsb', u'pcd',
             u'sd', u'lij', u'cbk-zam', u'cdo', u'ksh', u'ext', u'mwl',
             u'gag', u'ang', u'ug', u'ace', u'pi', u'pag', u'lez', u'nv',
             u'frp', u'sn', u'kab', u'myv', u'ln', u'pfl', u'xal', u'krc',
             u'haw', u'rw', u'kaa', u'pdc', u'to', u'kl', u'arc', u'nov',
             u'kbd', u'av', u'bxr', u'lo', u'bjn', u'ha', u'tet', u'tpi',
             u'pap', u'na', u'lbe', u'jbo', u'ty', u'mdf', u'tyv', u'roa-rup',
             u'wo', u'ig', u'srn', u'nso', u'kg', u'ab', u'ltg', u'zu', u'om',
             u'chy', u'za', u'cu', u'rmy', u'tw', u'mai', u'tn', u'chr', u'pih',
             u'xh', u'bi', u'got', u'sm', u'ss', u'mo', u'rn', u'ki', u'pnt',
             u'bm', u'iu', u'ee', u'lg', u'ak', u'ts', u'fj', u'ik', u'st',
             u'sg', u'ks', u'ff', u'dz', u'ny', u'ch', u'ti', u've', u'tum',
             u'cr', u'ng', u'cho', u'kj', u'mh', u'ho', u'ii', u'aa', u'mus',
             u'hz', u'kr',
             u'be-tarask', u'cz', u'd'] # Aliases and Wikidata

class TmplError(Exception):
    def __init__(self, message):
        self.message = message
    def __repr__(self):
        return u'Template "%s" is probably broken' % self.message

class TmplCls():
    def __init__(self):
        self.start = 0
        self.end   = 0
        self.text  = u""

class FieldCls():
    def __init__(self):
        self.start = 0
        self.end   = 0
        self.text  = u""

class TmplOps(object):
    ''' This class handles templates'''
    def __init__(self, text, tmpl):
        self.text = text
        self.tmpl = tmpl

    @classmethod
    def findTmpls(cls, text, tmpl):
        # Find all <nowiki> ... </nowiki> tags
        nowikis = []
        for nowiki in re.finditer(u'\<nowiki\>.*?\<\/nowiki\>', text, flags=re.UNICODE | re.MULTILINE | re.DOTALL | re.IGNORECASE):
            nowikis.append({'start': nowiki.start(), 'end': nowiki.end()})
        
        # Find starting positions of all '{{ <Tmpl>...' and '{{ <tmpl>...'
        lTmpls = []
        retmpl = u'\{\{\s*[' + tmpl[0:1].upper() + tmpl[0:1].lower() + u']' + tmpl[1:] + u'\s*[}|]'
        tOpens = re.compile(retmpl)
        for tOpen in list(tOpens.finditer(text)):
            # Ignore everything within <nowiki> ... </nowiki> tags
            skip = False
            for nowiki in nowikis:
                if nowiki['start'] < tOpen.start() < nowiki['end']:
                    skip = True
                    break
            if skip:
                continue
            tmplinst = TmplCls()
            tmplinst.start = tOpen.start()
            lTmpls.append(tmplinst)

        # Finally find all templates and their fields
        for itmpl in range(len(lTmpls)): # loop over '{{cite' positions
            tmplStart = lTmpls[itmpl].start
            tmplEnd  = tmplStart + 2 + len(tmpl) - 1            
            ignore  = False
            ignore2 = False
            fields  = []
            Nofound = 0
            Ncfound = 0
            Nofound2 = 0
            Ncfound2 = 0
            for symb in text[(tmplStart + 2 + len(tmpl)):]:
                tmplEnd += 1
                if symb == u'{':
                    Nofound += 1
                    ignore = True
                elif symb == u'}':
                    Ncfound += 1
                    if Ncfound > Nofound:
                        if len(fields) > 0:
                            fields[-1].end = tmplEnd
                            fields[-1].text = text[fields[-1].start:fields[-1].end]
                        break
                    elif Ncfound == Nofound:
                        ignore = False
                elif symb == u'[':
                    Nofound2 += 1
                    ignore2 = True
                elif symb == u']':
                    Ncfound2 += 1
                    if Ncfound2 == Nofound2:
                        ignore2 = False
                elif symb == u'|' and not ignore and not ignore2:
                    field = FieldCls()
                    field.start = tmplEnd
                    if len(fields) > 0:
                        fields[-1].end = tmplEnd
                        fields[-1].text = text[fields[-1].start:fields[-1].end]
                    fields.append(field)
                    
            # Check for proper template closure:
            if text[tmplEnd + 1:tmplEnd + 2] != u"}":
                raise TmplError(text[tmplStart:tmplEnd])
        
            tmplEnd += 2
            lTmpls[itmpl].end = tmplEnd
            lTmpls[itmpl].text = text[tmplStart:tmplEnd]
            lTmpls[itmpl].fields = fields

            '''
            print u'"%s"' % lTmpls[itmpl].text
            for field in lTmpls[itmpl].fields:
                print field.start, field.end
                print text[field.start:field.end]
                print field.text
            '''
        return lTmpls

    @classmethod
    def getField(cls, tmpl, fieldN = None, fieldName = None, getFieldN = False):

        if fieldN:
            if len(tmpl.fields) < fieldN:
                return None
            return tmpl.fields[fieldN - 1].text[1:].strip()

        ifieldN = 0
        if fieldName:
            for field in tmpl.fields:
                ifieldN += 1
                fieldValue = re.search(r'\|\s*%s\s*\=\s*(?P<value>.*)' % fieldName, field.text, flags=re.UNICODE | re.MULTILINE | re.DOTALL | re.IGNORECASE)
                if fieldValue:
                    if getFieldN:
                        return fieldValue.group(u'value').strip(), ifieldN
                    else:
                        return fieldValue.group(u'value').strip()

        if getFieldN:
            return None, None
        else:
            return None

    @classmethod
    def getLuaFields(cls, tmpl, lfieldnames = None, getFieldPos = False):
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
            lnamedfields[iname], lnamedfieldpos[iname] = cls.getField(tmpl, fieldName=lfieldnames[iname], getFieldN = True)
        #print lnamedfields, lnamedfieldpos
        
        # Get numbered fields:
        for iname in range(len(lfieldnames)):
            lnumfields[iname], lnumfieldpos[iname] = cls.getField(tmpl, fieldName=u'%d' % (iname + 1), getFieldN = True)
        #print lnumfields, lnumfieldpos
            
        # Get unnamed fields:
        ipos = 0
        while True:
            ipos += 1
            fieldtemp = cls.getField(tmpl, fieldN = ipos)
            if fieldtemp == None:
                break
            if u'=' in fieldtemp:
                continue
            else:
                lunnamfields.append(fieldtemp)
                lunnamfieldpos.append(ipos)
        #print lunnamfields, lunnamfieldpos
        
        # Get final fields according to priorities
        for iname in range(len(lfieldnames)):
            # named fields always overwrite other fields
            if not (lnamedfields[iname] == None or lnamedfields[iname] == u''):
                lfields[iname] = lnamedfields[iname]
                lfieldpos[iname] = lnamedfieldpos[iname]
            # otherwise the second appearance overwrites the first one
            if lfields[iname] == None or lfields[iname] == u'':
                if not (lnumfields[iname] == None or lnumfields[iname] == u''):
                    lfields[iname] = lnumfields[iname]
                    lfieldpos[iname] = lnumfieldpos[iname]
                if iname < len(lunnamfields):
                    if not (lunnamfields[iname] == None or lunnamfields[iname] == u''):
                        if not (lnumfields[iname] == None or lnumfields[iname] == u''):
                            if lunnamfieldpos[iname] < lnumfieldpos[iname]:
                                continue
                        lfields[iname] = lunnamfields[iname]
                        lfieldpos[iname] = lunnamfieldpos[iname]
        #print lfields, lfieldpos

        if getFieldPos:
            return lfields, lfieldpos
        else:
            return lfields

def conv2wikilink(text):
    wikilinktext = u''
    if text[0:5] == u'Файл:':
        wikilinktext = u'[[:%s]]' % text
    elif text[0:10] == u'Категорія:':
        wikilinktext = u'[[:%s]]' % text
    else:
        wikilinktext = u'[[%s]]' % text
    return wikilinktext

def dump_obj(obj, name):
    import cPickle
    with open(name + '.pkl', 'wb') as f:
        cPickle.dump(obj, f, cPickle.HIGHEST_PROTOCOL)

def load_obj(name):
    import cPickle
    with open(name + '.pkl', 'rb') as f:
        return cPickle.load(f)

''' EVERYTHING BELOW IS DEPRICATED - DO NOT USE IT IN NEW SCRIPTS!!!'''
Ntotal        = 0
Nchangedpages = 0
Nnotchanged   = 0

class ArgsClass(object):
    def __init__(self):
        self.acceptAll = False
        self.simulate  = False

args = ArgsClass()

def pageSave(page, originalText, text, summary):
    global Nchangedpages, args
    
    pywikibot.output(u"\n\n>>> \03{lightpurple}%s\03{default} <<<" % page.title())
    pywikibot.showDiff(originalText, text)

    if originalText.strip() == text.strip():
        pywikibot.output(u'No changes necessary in this page')
        return

    choice = 'n'
    if args.acceptAll:
        choice = 'y'
    else:
        choice = pywikibot.input_choice(
                        u'Do you want to accept these changes?',
                        [('Yes', 'y'), ('No', 'n')],
                        default='N')

    if args.simulate:
        pywikibot.output(u"Page will not be changed")
        Nchangedpages += 1
    elif choice == 'y':
        try:
            page.put(text, comment=summary)
            Nchangedpages += 1
        except pywikibot.EditConflict:
            pywikibot.output(u'Skipping %s because of edit conflict' % page.title())
        except pywikibot.SpamfilterError as e:
            pywikibot.output(u'Cannot change %s because of blacklist entry %s' % (page.title(), e.url))
        except pywikibot.LockedPage:
            pywikibot.output(u'Skipping %s (locked page)' % page.title())
        except pywikibot.PageNotSaved as error:
            pywikibot.output(u'Error putting page: %s' % error.args)

def setSitelink(item, sitename, title, summary):
    global args

    # https://www.mediawiki.org/wiki/Manual:Pywikibot/Wikidata

    if sitename in item.sitelinks.keys():
        if item.sitelinks[sitename] == title:
            pywikibot.output(u'Wikidata item ID (%s) already has a link "%s" to %s' %
                             (item.id, title, sitename))
        else:
            pywikibot.output(u'You try to set link "%s" to %s for Wikidata item ID (%s) that already has a link "%s"' %
                             (title, sitename, item.id, item.sitelinks[sitename]))
        return

    choice = 'n'
    if args.acceptAll:
        choice = 'y'
    else:
        choice = pywikibot.input_choice(
                        u'Do you want to set link %s:%s to the Wikidata?' % (sitename, title),
                        [('Yes', 'y'), ('No', 'n')],
                        default='N')

    if args.simulate:
        pywikibot.output(u"No sitelink will be set")
    elif choice == 'y':
        if item:
            item.setSitelink(sitelink={'site': sitename, 'title': title}, summary=summary)

def findInterwiki(page):
    global wikicodes
    iwikis = {}
    for iwiki in re.finditer(u'\[\[(?P<lang>[a-z-]+)\:(?P<title>[^]]+)\]\]', page.text, flags=re.UNICODE | re.MULTILINE | re.DOTALL | re.IGNORECASE):
        lang = iwiki.group(u'lang')
        if lang in wikicodes:
            iwikis[lang] = iwiki.group(u'title')
    return iwikis


if __name__ == "__main__":
    # Test
    #pagename = u"Користувач:Pavlo Chemist/Чернетка"
    #testBot().run()
    #bot.run()
    '''
    site = pywikibot.Site()
    catname = u'Біологія'
    cat = pywikibot.Category(site, catname)
    for subcat in cat.subcategories(recurse=10):
        print subcat.title()
    '''
    strtmp=u'''
#::::: Доречі, якщо ви не хочете порушувати сортувальний шаблон, то можна дисципліни перерахувати у дужках після назви вида спорту. Можна їх зробити жирним, курсивом, маленьким або ще якось, щоб воно разом нормально виглядало. Наприклад, ''<nowiki>[[Плавання на Олімпійських іграх|Плавання]]<br />({{не перекладено|Плавання на літніх Олімпійських іграх 2000 – 200 метрів комплексом (жінки)|200 м комплексом||Swimming at the 2000 Summer Olympics – Women's 200 metre individual medley}}),<br />({{не перекладено|Плавання на літніх Олімпійських іграх 2000 – 400 метрів комплексом|400 м комплексом||Swimming at the 2000 Summer Olympics – Women's 400 metre individual medley}}),<br />({{не перекладено|Плавання на літніх Олімпійських іграх 2004 – 200 метрів комплексом (жінки)|200 м комплексом)||Swimming at the 2004 Summer Olympics – Women's 200 metre individual medley}}),<br />({{не перекладено|Плавання на літніх Олімпійських іграх 2004 – 400 метрів комплексом (жінки)|400 м комплексом||Swimming at the 2004 Summer Olympics – Women's 400 metre individual medley}})</nowiki>''. А виглядатиме все це діло наступним чином:<br />
#::::::[[Плавання на Олімпійських іграх|Плавання]]<br />({{не перекладено|Плавання на літніх Олімпійських іграх 2000 – 200 метрів комплексом (жінки)|200 м комплексом||Swimming at the 2000 Summer Olympics – Women's 200 metre individual medley}}),<br />({{не перекладено|Плавання на літніх Олімпійських іграх 2000 – 400 метрів комплексом|400 м комплексом||Swimming at the 2000 Summer Olympics – Women's 400 metre individual medley}}),<br />({{не перекладено|Плавання на літніх Олімпійських іграх 2004 – 200 метрів комплексом (жінки)|200 м комплексом||Swimming at the 2004 Summer Olympics – Women's 200 metre individual medley}}),<br />({{не перекладено|Плавання на літніх Олімпійських іграх 2004 – 400 метрів комплексом (жінки)|400 м комплексом||Swimming at the 2004 Summer Olympics – Women's 400 metre individual medley}})<br />Нічого страшного, що будуть червоні посилання. Я згодом зроблю ці сторінки.--[[Користувач:Waylesange|Waylesange]] ([[Обговорення користувача:Waylesange|обговорення]]) 11:30, 7 вересня 2012 (UTC)
    '''
    tmp = TmplOps.findTmpls(strtmp, u'не перекладено')
    tmp = tmp[0]
    print(tmp.text)
    for field in tmp.fields:
        print('-'*10)
        print(field.text)
    
