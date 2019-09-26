import csv
import re
import random

import mwparserfromhell
import pywikibot
from pywikibot import pagegenerators
from diff_match_patch import diff_match_patch

def main():
    domains = list(read_domains_list('spamsites.txt'))
    random.shuffle(domains)
    for page in pages_linking_to(domains):
        print()
        print('=' * 50)
        print(page.title())
        print('-' * 50)
        new_text = page.text
        new_text = ref_cleaner(new_text, domains)
        new_text = external_links_cleaner(new_text, domains)
        show_domains_lines(new_text, domains)
        update_page(page, new_text, 'Забрав посилання на сміттєві ресурси.', yes=False)

def show_domains_lines(text, domains):
    for line in text.splitlines():
        if text_has_domains(line, domains, pattern='%s'):
            print(line)

def ref_cleaner(text, domains):
    wikicode = mwparserfromhell.parse(text)
    for tag in wikicode.filter_tags():
        if tag.tag != 'ref':
            continue
        if text_has_domains(str(tag.contents), domains):
            wikicode.replace(tag, '{{fact}}')

    res = str(wikicode)
    for i in range(10):
        res = re.sub(r'{{fact}}\s*<ref', '<ref', res)
        res = re.sub(r'ref>\s*{{fact}}', 'ref>', res)
        res = re.sub(r'{{fact}}\s*{{Неавторитетне джерело}}', '{{fact}}', res)
        res = re.sub(r'{{Неавторитетне джерело}}\s*{{fact}}', '{{fact}}', res)
        res = re.sub(r'{{fact}}\s*{{fact}}', '{{fact}}', res)
        res = re.sub(r'(<ref\s+name=.+?\s*/>\s*){{fact}}', r'\1', res)
    return res

def external_links_cleaner(text, domains):
    res = []
    for line in text.splitlines():
        if text_has_domains(line, domains):
            if re.match('^\*\s*\[?http', line):
                continue
            if re.match('^\*\s*\{\{cite', line):
                continue
        res.append(line)
    return '\n'.join(res)

def text_has_domains(text, domains, pattern='/%s/'):
    return any((pattern % domain) in text for domain in domains)

def pages_linking_to(domains):
    for domain in domains:
        for page in pagegenerators.SearchPageGenerator(
            r'insource:/%s/' % domain.replace('.', r'\.'),
            namespaces=[0],
        ):
            yield page

def read_domains_list(filename):
    with open(filename) as f:
        for row in f:
            yield row.strip()

def update_page(page, new_text, description, yes=False):
        if new_text == page.text:
            print('Нічого не міняли')
            return

        #  dmp = diff_match_patch()
        #  diff = dmp.diff_main(page.text, new_text)
        #  dmp.diff_cleanupSemantic(diff)
        #  short_diff = []
        #  for action, text in diff:
        #      if action == 0 and len(text) > 210:
        #          text = text[:100] + ' ... ' + text[-100:]
        #      short_diff.append((action, text))
        #  patches = dmp.patch_make(page.text, new_text)
        #  diff = dmp.patch_toText(patches)
        #  print(diff)

        # html = dmp.diff_prettyHtml(short_diff)
        # with open('diff.html', 'w') as f:
        #     f.write(f'''<!DOCTYPE html><html>
        #         <head>
        #             <meta charset=utf-8>
        #             <title>Simple HTML5</title>
        #         </head>

        #         <body>
        #         {html}
        #         </body>
        #         </html>
        #     ''')
        # print(diff)

        pywikibot.showDiff(page.text, new_text)

        print(description)

        if yes or confirmed('Робимо заміну?'):
            page.text = new_text
            page.save(description)

def confirmed(question):
    return pywikibot.input_choice(
        question,
        [('Yes', 'y'), ('No', 'n')],
        default='N'
    ) == 'y'

if __name__ == '__main__':
    main()
