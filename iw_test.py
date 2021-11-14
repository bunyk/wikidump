import mwparserfromhell

from iw import get_params, deduplicate_comments
from constants import BOT_NAME

def parse_tmpl(text):
    code = mwparserfromhell.parse(text)
    return code.filter_templates()[0]

def test_get_params():
    tmpl = parse_tmpl('{{iw|треба=Магдалена Фрех|мова=fr|є=Magdalena Fręch}}')
    uk_title, text, lang, external_title = get_params(tmpl)
    assert uk_title == 'Магдалена Фрех'
    assert text == 'Магдалена Фрех'
    assert lang == 'fr'
    assert external_title == 'Magdalena Fręch'

    tmpl = parse_tmpl('{{нп|Imagen Awards}}')
    uk_title, text, lang, external_title = get_params(tmpl)

    assert uk_title == 'Imagen Awards'
    assert text == 'Imagen Awards'
    assert lang == 'en'
    assert external_title == 'Imagen Awards'

    tmpl = parse_tmpl('{{Нп|Галф-Кантрі|||Gulf Country}}')
    uk_title, text, lang, external_title = get_params(tmpl)

    assert uk_title == 'Галф-Кантрі'
    assert text == 'Галф-Кантрі'
    assert lang == 'en'
    assert external_title == 'Gulf Country'

    tmpl = parse_tmpl('{{iw|треба=treba|текст=text|мова=lang|є=exists}}')
    uk_title, text, lang, external_title = get_params(tmpl)

    assert uk_title == 'treba'
    assert text == 'text'
    assert lang == 'lang'
    assert external_title == 'exists'

    tmpl = parse_tmpl('{{не перекладено | є =B |мова=en| треба = Б}}')
    uk_title, text, lang, external_title = get_params(tmpl)

    assert uk_title == 'Б'
    assert text == 'Б'
    assert lang == 'en'
    assert external_title == 'B'


def test_deduplicate_comments():
    assert deduplicate_comments(f'<!-- Проблема вікіфікації: ggg ({BOT_NAME})--><!-- Проблема вікіфікації: ggg ({BOT_NAME})-->') == ( f'<!-- Проблема вікіфікації: ggg ({BOT_NAME})-->'
    )
