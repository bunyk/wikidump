import csv

import mwparserfromhell
import pywikibot
from pywikibot import pagegenerators

def main():
    domains = list(read_domains_list('spamsites.csv'))
    print("Total:", len(list(pages_linking_to(domains))))
    return
    for page in pages_linking_to(domains):
        print(page.title())
        new_text = page.text
        new_text = ref_cleaner(new_text, domains)
        new_text = external_links_cleaner(new_text, domains)
        show_domains_lines(new_text, domains)
        update_page(page, new_text, 'Забрав посилання на помийні сайти. http://texty.org.ua/d/2018/mnews/', yes=False)

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
            wikicode.remove(tag)
    return str(wikicode)

def external_links_cleaner(text, domains):
    res = []
    for line in text.splitlines():
        if text_has_domains(line, domains):
            if line.startswith('* {{cite'):
                continue
            if line.startswith('* [http'):
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
