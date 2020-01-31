from iw import get_params
import mwparserfromhell

def tmpl(text):
    code = mwparserfromhell.parse(text)
    return code.filter_templates()[0]

def test_get_params():
    uk_title, text, lang, external_title = get_params(tmpl(
        '{{iw|треба=this||мова=en|є=that}}'
    ))
    assert uk_title == 'this'
    assert text == 'this'
    assert lang == 'en'
    assert external_title == 'that'
