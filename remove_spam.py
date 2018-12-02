import csv

import pywikibot
from pywikibot import pagegenerators

def main():
    site = pywikibot.Site()
    count = 0
    for domain in read_domains_list('spamsites.csv'):
        print(f'\n== {domain} ==')
        for page in pagegenerators.SearchPageGenerator(
            'insource:/%s/' % domain.replace('.', r'\.'),
            namespaces=[0],
        ):
            count += 1
            print(page.title())
    print("Total:", count)

def read_domains_list(filename):
    with open(filename, newline='') as csvfile:
        for row in  csv.DictReader(csvfile):
            for domain in row['url_domain'].split(','):
                yield domain.strip()


if __name__ == '__main__':
    main()
