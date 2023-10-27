import sys
import re
from functools import partial

import pywikibot
from pywikibot.xmlreader import XmlDump
import mwparserfromhell

def main():
    arg = sys.argv[1]
    if arg.endswith('.bz2'):
        for p in iter_mixed(arg):
            print(p)
    elif arg.endswith('.txt'):
        with open(arg) as f:
            for p in f:
                fix_page(p.strip())
                print()
    else:
        fix_page(arg)

LATIN_HOMOGRAPHS =     'AaCcTKOoIiXxyEeMPpHB'
CYRILLIC_HOMOPGRAPHS = 'АаСсТКОоІіХхуЕеМРрНВ'
CYR_EXCLUSIVE = 'БбгГґҐдДєЄжЖзЗиИїЇйЙпПфФцЦчЧшШЩщюЮяЯ'
LAT_EXCLUSIVE = 'bdDfFgGhjJlLqNQrRsStVvwWzZ'

CYR = 'а-яєії'

mixed_re = f'[a-z{CYR}’]*(?:[a-z][{CYR}]|[{CYR}][a-z])[a-z{CYR}’]*'


PRE_FIXES = [
    (r' iн\.', ' ін.'),
    (r' iм\.', ' ім.'),
    (r'ghfворуч', 'праворуч'),
    (r'([^&])nbsp;', r'\1&nbsp;'),
    (r'&nbsp([^;])', r'&nbsp;\1'),
    (r'cт\.', r'ст.'),
]

EXCEPTION_AREAS = [
    r'\{\{(F|In).*?\}\}', # weird templates
    r'[КФТСЛ]р?[a-h]?x?[a-h][1-8]', # chess
    r'\[\[(?:Файл|File):.*?\]\]',
    r'(?:Файл|File):.*?\|',
    r'http[^ \|\]\}]+',
    r'^.*\.(jpg|jpeg|png|svg|tiff?)',
    r'%[A-Z0-9]{2}', # URLencoding
]

TO_KEEP = '''
AVтограф
2SLБ
3SLBФ
3SLБ
DЦ
Dруга Ріка
FANтастика
Flёur
FМВС
InВДВ
InМЕХ
KaZaнтип
KaZaнтип
KoЯN
KoЯn
Lюk
Lюk-дует
Lюк
MEGAКАВА
Megaкава
NOνA
NЭНСИ
Pianoбой
RECвізити
ReФорматЦія
RЕФLEKSIЯ
Starперці
Superнянь
Tvій
Ukraїner
Uлія
Vavёrka
Vася
Vмакс
Wideнь
Zалупа
Zаникай
Zомбі
Zоряна
dsРНК
ssРНК
ΜTorrent
ΦX174
ΦX174
ΦX174
ЄльціUA
АрміяInform
Арміяinform
БраZерс
Вниz
ВолиньPost
ГАМКA
ГАМКB
ГАМКC
ГОГОЛЬFEST
ГогольFest
Гогольfest
ДМ-SLБ
Дзядuк
Духless
ЖАRА
КАZАНТИП
КримSOS
ЛжеNostradamus
Лорd
ЛітераDYPA
МакSим
Модель ΛCDM
МікрOFFONна
НаCLICKай
ПоLOVEинки
СкруDG
СловоUA
Снjпъ
СуперWASP
ТаблоID
УкрFace
УкраїнSKA
ФлайzZzа
ШELTER+
ШАNA
ШОУМАSТГОУОН
ШоумаSтгоуон
Яndex
еXтра
мікроQR
нароDJення
'''.splitlines()



site = pywikibot.Site('uk', 'wikipedia')

def iter_mixed(dump_filename):
    i = 0
    for page in XmlDump(dump_filename).parse():
        i += 1
        if i % 123 == 0:
            print('\033[K\r', i, page.title, file=sys.stderr, end='')

        mixed = find_mixes(page.text)
        if mixed:
            new_text = fix_page_text(page.text)
            if new_text != page.text :
                # print(len(mixed), page.title + ':', ', '.join(colored(mix) for mix in mixed[:5]))
                yield page.title

def find_mixes(text):
    return re.findall(mixed_re, text, re.I)

def fix_word(word):
    if word in TO_KEEP: 
        return word
    script = detect_script(word)
    new_word = script(word)
    if has_mix(new_word):
        print('Do not know how to handle:', colored(word))
        return word
    return new_word

def looks_like_roman_numeral(word):
    for c in word:
        if c not in ('IІVXХLCСDMМ'):
            return False
    return True

def detect_script(word):
    if any(c in word for c in CYR_EXCLUSIVE):
        return cyrilize

    if any(c in word for c in LAT_EXCLUSIVE):
        return latinize
    if looks_like_roman_numeral(word):
        return latinize

    latin = count_latin(word)
    cyrillic = count_cyrillic(word)
    if latin > cyrillic:
        return latinize
    elif cyrillic > latin:
        return cyrilize

    return lambda x: x

from iw import update_page
def fix_page(pagename):
    print('\n\t =', pagename, '=')
    page = pywikibot.Page(site, pagename)
    if '/Архів' in page.title():
        print('Архів, пропускаємо')
        return
    if len(page.text) > 300000:
        print('Сторінка задовга')
        return
    mixes = re.findall(mixed_re, page.text, re.I)
    if mixes:
        print(' - ' + '\n - '.join(map(colored, mixes)))
    else:
        print('no mixes')
    new_text = fix_page_text(page.text)
    try:
        update_page(page, new_text, 'Виправлена суміш розкладок')
    except pywikibot.exceptions.LockedPageError as e:
        print(e)

def fix_page_text(text):
    new_text = text
    for fix_from, fix_to in PRE_FIXES:
        new_text = re.sub(fix_from, fix_to, new_text)
    new_text = process_text(new_text, mixed_re, EXCEPTION_AREAS, fix_word)
    if new_text != text: 
        # Do additional replacements
        new_text = re.sub(r"\[\[([^|\d]+)\|\1([^\W\d]*)]]", r"[[\1]]\2", new_text)

    return new_text

def process_text(text, reMix, exception_areas, func):
    for match in re.finditer(reMix, text, flags=re.I | re.M):
        inside_exception = False
        for exception in exception_areas:
            for exception_match in re.finditer(exception, text, flags = re.I | re.M):
                if (match.start() >= exception_match.start() and match.start() < exception_match.end()) or (match.end() > exception_match.start() and match.end() <= exception_match.end()):
                    inside_exception = True
                    break
            if inside_exception:
                break
        if not inside_exception:
            text = text[:match.start()] + func(match.group()) + text[match.end():]
    return text

def cyrilize(word):
    return word.translate(
        str.maketrans(LATIN_HOMOGRAPHS, CYRILLIC_HOMOPGRAPHS)
    )

def latinize(word):
    return word.translate(
        str.maketrans(CYRILLIC_HOMOPGRAPHS, LATIN_HOMOGRAPHS)
    )


def colored(text):
    text = re.sub('^([a-z])', r'\033[94m\1', text, 0, re.I)
    text = re.sub(f'^([{CYR}])', r'\033[0m\1', text, 0, re.I)
    text = re.sub(f'([a-z])([{CYR}])', r'\1\033[0m\2', text, 0, re.I)
    text = re.sub(f'([{CYR}])([a-z])', r'\1\033[94m\2', text, 0, re.I)
    return text + '\033[0m'

def count_re(pattern, text):
    return len(re.findall(pattern, text, re.I))

count_latin = partial(count_re, '[a-z]')
count_cyrillic = partial(count_re, f'[{CYR}]')

def has_mix(word):
    l = count_latin(word)
    return 0 < l < len(word)

if __name__ == '__main__':
    main()

test_text_with_url = '- * {{cite web |url=http://khoda.gov.ua/na-hersonshhinі-prohoditimut-navchalnі-zbori-124-okremoї-brigadi-teritorіalnoї-oboroni |title=На Херсонщині проходитимуть навчальні збори 124 окремої бригади територіальної оборони |author= |date=2018-07-25 |website=http://khoda.gov.ua/ |publisher=[[Херсонська обласна державна адміністрація]] |accessdate=26 липня 2018 |archive-date=28 липня 2018 |archive-url=https://web.archive.org/web/20180728221940/http://khoda.gov.ua/na-hersonshhinі-prohoditimut-navchalnі-zbori-124-okremoї-brigadi-teritorіalnoї-oboroni }}'

def test_fix_page_text():
    fixed = fix_page_text(test_text_with_url)
    assert fixed == test_text_with_url # should not change

def test_124():
    page = """[http://www.khoda.gov.ua/vіjskovі-taktichnі-navchannja-124-oї-okremoї-brigadi-teritorіalnoї-oboroni-na-hersonshhinі-rozpochato! Військові тактичні навчання 124-ї окремої бригади територіальної оборони на Херсонщині розпочато!] {{Webarchive|url=https://web.archive.org/web/20190924125309/http://khoda.gov.ua/vіjskovі-taktichnі-navchannja-124-oї-okremoї-brigadi-teritorіalnoї-oboroni-na-hersonshhinі-rozpochato! |date=24 вересня 2019 }} на http://www.khoda.gov.ua/ {{Webarchive|url=https://web.archive.org/web/20190823083120/http://khoda.gov.ua/ |date=23 серпня 2019 }}</ref>.

* {{cite web |url=http://khoda.gov.ua/na-hersonshhinі-prohoditimut-navchalnі-zbori-124-okremoї-brigadi-teritorіalnoї-oboroni |title=На Херсонщині проходитимуть навчальні збори 124 окремої бригади територіальної оборони |author= |date=2018-07-25 |website=http://khoda.gov.ua/ |publisher=[[Херсонська обласна державна адміністрація]] |accessdate=26 липня 2018 |archive-date=28 липня 2018 |archive-url=https://web.archive.org/web/20180728221940/http://khoda.gov.ua/na-hersonshhinі-prohoditimut-navchalnі-zbori-124-okremoї-brigadi-teritorіalnoї-oboroni }}
"""
    fixed = fix_page_text(page)
    assert fixed == page # should not change

def test_image():
    page = '''
| name = Oryctini
| image = Жук носорiг. Маяцький лic.jpg
| image_width = 270px
'''
    fixed = fix_page_text(page)
    assert fixed == page # should not change

def test_nbsp():
    page = 'З 1946 рокуnbsp;— виконроб, &nbspщесуміш'
    fixed = fix_page_text(page)
    assert fixed == 'З 1946 року&nbsp;— виконроб, &nbsp;щесуміш'

def test_gallery():
    page = '''<small><gallery caption="" widths="" heights="" mode=packed perrow="" class= style=>
Новгород. Детинец и торговая сторона с птичьего полета.(отк) конXIXвека e0OMqt9nPDM e1.jpg|border|Новгородський детинець на листівці, після 1895 року
</gallery></small>
'''
    fixed = fix_page_text(page)
    assert fixed == page # should not change

def test_urlencoding():
    page = '&nbsp;[[Спеціальна%3AДжерела%20книг/9789197737609|9789197737609'
    fixed = fix_page_text(page)
    assert fixed == page # should not change

def test_concats():
    page = """ ВолиньРost|accessdate=2022-02-08|language=en|archive-date=8 лютого 2022| ArtВітальня"""
    fixed = fix_page_text(page)
    assert fixed == page # should not change

def test_funny():
    page = 'енергiя, необхiдна для здiйснення вивертання конформацiї вiдносно центра iнверсiї.'
    fixed = fix_page_text(page)
    expected = 'енергія, необхідна для здійснення вивертання конформації відносно центра інверсії.'
    assert fixed == expected

