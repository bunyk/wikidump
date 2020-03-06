import mwparserfromhell

from iw import get_params, iw_templates

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


def test_iw_templates():
    text = '''
    {{edit}} {{lang-en|adsf}}
    <div>
    '{{iw|треба=this||мова=en|є=that}}'
    </div>
    <gallery mode="packed" heights="120" caption="">
    Файл:Камера з надвисоким вакуумом (Інститут Фізики НАН України).jpg|{{нп|Надвисокий вакуум|||Ultra-high vacuum}}
    </gallery>
    '''
    assert len(list(iw_templates(text))) == 2

