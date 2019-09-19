"""Count substring frequencies in wikipedia dump"""

from collections import Counter
from itertools import islice
import sys
 
from pywikibot.xmlreader import XmlDump

LIMIT_PAGES = None # None for unlimited sample
PATTERN_SIZE = 100
HASHES_ARRAY_SIZE = 10000000
TOP_N = 50
DUPLICATED_TOP = TOP_N * 100


def iter_texts(filename):
    """ Yield page texts from dump given by file name. """
    pages = 0
    for page in islice(XmlDump(filename).parse(), 0, LIMIT_PAGES):
        if (page.ns != '0') or page.isredirect:
            continue
        yield page.text
        pages += 1
        if pages % 123 == 0:
            print('\rPages: %d. Processing: %s' % (pages, (page.title + ' ' * 70)[:70]), end='')
    print()

 
def main():
    if len(sys.argv) < 2:
        print('Please give file name of dump')
        return
    filename = sys.argv[1]
 
    print('allocating hash table')
    hash_counts = [0] * HASHES_ARRAY_SIZE

    print('Processing dump')
    for text in iter_texts(filename):
        for i in range(len(text) - PATTERN_SIZE):
            pattern = text[i:i + PATTERN_SIZE]
            h = hash(pattern) % HASHES_ARRAY_SIZE
            hash_counts[h] += 1

    print('sorting hashes')
    kvcounts = sorted(enumerate(hash_counts), key=lambda p: p[1])
    print('Top hash count:', kvcounts[-1][1])
    top_2n_hashes = set(key for key, _ in kvcounts[-DUPLICATED_TOP:])

    print('reprocessing dump')
    c = Counter()
    for text in iter_texts(filename):
        for i in range(len(text) - PATTERN_SIZE):
            pattern = text[i:i + PATTERN_SIZE]
            h = hash(pattern) % HASHES_ARRAY_SIZE
            if h in top_2n_hashes:
                c[pattern] += 1

    print('{| class="wikitable sortable"')
    print('|-\n! Текст\n! Кількість повторень')
    printed = set()
    for el, count in c.most_common(DUPLICATED_TOP):
        duplicate = False
        for pp in printed:
            if levenstein(pp, el) < (PATTERN_SIZE / 3): # difference less than 33% of previous
                duplicate = True
                break
        if duplicate:
            continue
        printed.add(el)
        print('|-')
        print(f'|<pre><nowiki>{el}</nowiki></pre>\n|', count)
        if len(printed) >= TOP_N:
            break
    print('|}')

def levenstein(s1,s2):
    n = range(0,len(s1)+1)
    for y in range(1,len(s2)+1):
        l,n = n,[y]
        for x in range(1,len(s1)+1):
            n.append(min(l[x]+1,n[-1]+1,l[x-1]+((s2[y-1]!=s1[x-1]) and 1 or 0)))
    return n[-1]

if __name__ == '__main__':
    main()
