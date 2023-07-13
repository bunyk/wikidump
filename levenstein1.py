import re
import sys
import json
from collections import defaultdict, Counter
from itertools import permutations
from urllib.parse import urlparse
 
import mwparserfromhell
from pywikibot.xmlreader import XmlDump
 
def main():
    with open('pages.lst') as f:
        existing_pages = set(
            p.strip() for p in f
        )
    with open('top_links.json') as f:
        top_links = Counter(json.load(f))

    for i, (link, frequency) in enumerate(top_links.most_common()):
        if frequency < 2:
            break
        if link in existing_pages:
            continue
        print(f'\r{i} {frequency} {link}', end='', file=sys.stderr)
        find_suggestions(link, frequency, existing_pages)
 
def find_suggestions(link, frequency, existing_pages):
    suggestions = []
    for edit in deletes_and_doubles(link):
        if just_number_diff(edit, link):
            continue
        if edit in existing_pages:
            suggestions.append(edit)
    if suggestions:
        print(f'* [[{link}]] ([[Спеціальна:Посилання_сюди/{link}|~{frequency}]])')
        for s in suggestions:
            print(f'** [[{s}]]?')

def strip_num(s):
    return re.sub('\d', '', s)

def just_number_diff(a, b):
    ''' True if difference between two strings is just in numbers '''
    return strip_num(a) == strip_num(b)

# https://norvig.com/spell-correct.html
ALPHABET = "'(),-ABCDHIMPSTabcdeghiklmnoprstuwyzІАБВГҐДЕЗКЛМНОПРСТУФХЧШабвгґдежзийклмнопрстуфхцчшьюяєії"
# alphabet = Counter(''.join(existing_pages))
# print(''.join(sorted(c for c, f in alphabet.most_common(100))))
# And then delete numbers, inserting numbers is really weird way to fix typo
def edits1(text):
    "All edits that are one edit away from `text`."
    splits     = [(text[:i], text[i:])    for i in range(len(text) + 1)]
    deletes    = [L + R[1:]               for L, R in splits if R]
    transposes = [L + R[1] + R[0] + R[2:] for L, R in splits if len(R)>1]
    replaces   = [L + c + R[1:]           for L, R in splits if R for c in ALPHABET]
    inserts    = [L + c + R               for L, R in splits for c in ALPHABET]
    return set(deletes + transposes + replaces + inserts)

def deletes_and_doubles(text):
    splits     = [(text[:i], text[i:])    for i in range(len(text) + 1)]
    doubles    = [L + R[0] + R            for L, R in splits if R and R[0] != 'I']
    return set(doubles)

def edits2(text):
    return set(
        t2 
        for o in reorders(text)
        for t in likely_typos(o)
        for t2 in likely_typos(t)
    )

TYPO_ALPHABET = "'еєґгіипфув ь,-—()" 
REPLACES = defaultdict(set)
# for group in ['іиыеєї', 'еа', 'ґхгч', 'пфт', 'ув', '-— ', 'зс', 'йь']:
for group in ['іи', 'ґг', 'ув', '-— ', 'еє']:
    for char in group:
        REPLACES[char].update(group.replace(char, ''))
        REPLACES[char.upper()].update(group.replace(char, '').upper())
print(REPLACES)
print()

def likely_typos(text):
    splits     = [(text[:i], text[i:])    for i in range(len(text) + 1)]
    return set(
        [text] +
        # [L + R[1:]                for L, R in splits if R and R[0] in TYPO_ALPHABET] + # deletes
        [L + c + R[1:]            for L, R in splits if R for c in REPLACES[R[0]]] + # replaces
        [L + R[0].upper() + R[1:] for L, R in splits if R] +
        [L + R[0].lower() + R[1:] for L, R in splits if R]
        # [L + c + R                for L, R in splits for c in TYPO_ALPHABET] # inserts
    )



def reorders(text):
    yield text
    parts = text.split(' ')
    if len(parts) > 3:
        return
    for p in permutations(text.split(' ')):
        yield ' '.join(p)

# print('\n'.join(edits2('Тарас Григорович Шевченко')))
assert 'Крістіан Голомеєв' in edits2('Крістіан Голомєєв')
assert 'Тіссе Едуард Казимірович' in edits2('Тіссе Едуард Казимирович')


def get_filename():
    if len(sys.argv) < 2:
        print('Please provide file name of dump')
        sys.exit(1)
    return sys.argv[1]
 
if __name__ == '__main__':
    main()
