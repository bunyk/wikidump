import csv

import mwparserfromhell
import pywikibot
from pywikibot import pagegenerators
from diff_match_patch import diff_match_patch

def main():
    domains = list(read_domains_list('spamsites.csv'))
    for page in pages_linking_to(domains):
        print(page.title())
        new_text = page.text
        new_text = ref_cleaner(new_text, domains)
        new_text = external_links_cleaner(new_text, domains)
        show_domains_lines(new_text, domains)
        update_page(page, new_text, 'Забрав посилання на сміттєві ресурси. http://texty.org.ua/d/2018/mnews/', yes=False)

def show_domains_lines(text, domains):
    for line in text.splitlines():
        if text_has_domains(line, domains):
            print(line)

def ref_cleaner(text, domains):
    wikicode = mwparserfromhell.parse(text)
    for tag in wikicode.filter_tags():
        if tag.tag != 'ref':
            continue
        if text_has_domains(str(tag.contents), domains):
            wikicode.replace(tag, '{{fact}}')

    res = str(wikicode)
    res = res.replace('{{fact}}<ref', '<ref') # TODO: replace to regexp and add \s* between template and ref
    res = res.replace('ref>{{fact}}', 'ref>')
    return res

def external_links_cleaner(text, domains):
    res = []
    for line in text.splitlines():
        if text_has_domains(line, domains):
            if line.startswith('* {{cite'):
                continue
            if line.startswith('* [http'):
                continue
            if line.startswith('* http'):
                continue
        res.append(line)
    return '\n'.join(res)

def text_has_domains(text, domains):
    return any(domain in text for domain in domains)

def pages_linking_to(domains):
    for domain in domains:
        for page in pagegenerators.SearchPageGenerator(
            'insource:/%s/' % domain.replace('.', r'\.'),
            namespaces=[0],
        ):
            yield page

def read_domains_list(filename):
    with open(filename, newline='') as csvfile:
        for row in  csv.DictReader(csvfile):
            for domain in row['url_domain'].split(','):
                yield domain.strip()

def update_page(page, new_text, description, yes=False):
        if new_text == page.text:
            print('Нічого не міняли')
            return

        dmp = diff_match_patch()
        diff = dmp.diff_main(page.text, new_text)
        dmp.diff_cleanupSemantic(diff)
        short_diff = []
        for action, text in diff:
            if action == 0 and len(text) > 210:
                text = text[:100] + ' ... ' + text[-100:]
            short_diff.append((action, text))

        html = dmp.diff_prettyHtml(short_diff)
        with open('diff.html', 'w') as f:
            f.write(f'''<!DOCTYPE html><html>
                <head>
                    <meta charset=utf-8>
                    <title>Simple HTML5</title>
                </head>

                <body>
                {html}
                </body>
                </html>
            ''')
        print(diff)
        # pywikibot.showDiff(page.text, new_text)

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
