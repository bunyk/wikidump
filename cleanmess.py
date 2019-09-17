

import re

from pywikibot import Page, Site, pagegenerators
import mwparserfromhell
from itertools import islice

from remove_spam import update_page

SEARCH_QUERY='insource:/cx-template-editor-source-container/'

def main():
    for page in pagegenerators.SearchPageGenerator(SEARCH_QUERY, namespaces=[0]):
        edit_page(page)

def edit_page(page):
    print(page.title())
    code = mwparserfromhell.parse(page.text)
    for tag in code.filter(
        recursive=True,
        forcetype=mwparserfromhell.nodes.tag.Tag
    ):
        if not str(tag).startswith('<div class="cx-template-editor-source-container"'):
            continue
        code.remove(tag)

    update_page(page, str(code), 'Вікіфікація', yes=False)

if __name__ == "__main__":
    main()
