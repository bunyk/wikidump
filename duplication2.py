"""Count substring frequencies in wikipedia dump"""

from collections import Counter
import gc
import sys
 
from pywikibot.xmlreader import XmlDump

LIMIT_PAGES = 10000 # None for unlimited sample
PATTERN_SIZE = 1000
HASHES_ARRAY_SIZE = 10000000
TOP_N = 100
DUPLICATED_TOP = TOP_N * 100


def iter_texts(filename):
    """ Yield page texts from dump given by file name. """
    pages = 0
    for page in XmlDump(filename).parse():
        if (page.ns != '0') or page.isredirect:
            continue
        yield page.text
        pages += 1
        if pages % 123 == 0:
            print('\rPages: %d. Processing: %s' % (pages, (page.title + ' ' * 70)[:70]), end='')
            if LIMIT_PAGES and (pages >= LIMIT_PAGES):
                return
    print()

def iter_patterns_hashes(filename):
    for text in iter_texts(filename):
        if len(text) < PATTERN_SIZE:
            continue
        for i in range(len(text) - PATTERN_SIZE):
            pattern = text[i:i + PATTERN_SIZE]
            h = hash(pattern) % HASHES_ARRAY_SIZE
            yield pattern, h


def get_top_hashes(filename):
    print('allocating hash table')
    hash_counts = [0] * HASHES_ARRAY_SIZE

    print('Processing dump')
    for _, h in iter_patterns_hashes(filename):
        hash_counts[h] += 1

    print('sorting hashes')
    kvcounts = sorted(enumerate(hash_counts), key=lambda p: p[1])
    print('Top hash count:', kvcounts[-1][1])
    print('Bottom hash count:', kvcounts[-DUPLICATED_TOP][1])
    return set(key for key, _ in kvcounts[-DUPLICATED_TOP:])

 
def main():
    if len(sys.argv) < 2:
        print('Please give file name of dump')
        return
    filename = sys.argv[1]
 
    for text in iter_texts(filename):
        pass
    return
    top_2n_hashes = get_top_hashes(filename)

    print('freeing some memory')
    gc.collect()

    print('reprocessing dump')
    c = Counter()
    for pattern, h in iter_patterns_hashes(filename):
        if h in top_2n_hashes:
            c[pattern] += 1

    print('{| class="wikitable sortable"')
    print('|-\n! №\n! Текст\n! Кількість повторень')
    printed = set()
    n = 1
    for el, count in c.most_common(DUPLICATED_TOP):
        if count == 1:
            break
        duplicate = False
        for pp in printed:
            if similar(pp, el):
                duplicate = True
                break
        if duplicate:
            continue
        printed.add(el)
        print('|-')
        print(f'|{len(printed)}\n|<pre><nowiki>{el}</nowiki></pre>\n|', count)
        if len(printed) >= TOP_N:
            break
    print('|}')

def similar(s1, s2):
    return (s1[:PATTERN_SIZE//2] in s2) or (s1[PATTERN_SIZE//2:] in s2)

if __name__ == '__main__':
    main()
