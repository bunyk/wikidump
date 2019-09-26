"""Turn xml.bz2 into plain text"""

import sys
from pywikibot.xmlreader import XmlDump

def main():
    if len(sys.argv) < 2:
        print('Please give file name of dump')
        return
    for page in XmlDump(sys.argv[1]).parse():
        if (page.ns != '0') or page.isredirect:
            continue
        print(page.title)
        print(page.text.count('\n'))
        print(page.text)
 
if __name__ == '__main__':
    main()
