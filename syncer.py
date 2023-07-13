import time
from datetime import datetime
import argparse
from itertools import islice
import glob
import os

import pywikibot
from pywikibot import pagegenerators
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler

SITE = pywikibot.Site("uk", "wikipedia")
PAGES_DIR = 'pages'

COMMENT = ''

def sync(args):
    print(args)
    cleanup()
    for page in islice(search(args.search, args.namespaces), args.limit):
        save(page)
    watch_changes()

def search(query, namespaces):
    with open(PAGES_DIR + '/exclude.lst') as f:
        excludes = set(l.strip() for l in f)

    for page in pagegenerators.SearchPageGenerator(query, site=SITE, namespaces=namespaces):
        title = page.title()
        if title in excludes:
            continue
        yield page

def cleanup():
    for f in glob.glob(PAGES_DIR + '/*.wiki'):
        os.remove(f)

def watch_changes():
    my_event_handler = PatternMatchingEventHandler(["*.wiki"], None, None, True)
    my_event_handler.on_modified = on_modified

    my_observer = Observer()
    my_observer.schedule(my_event_handler, './' + PAGES_DIR, recursive=False)

    my_observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        my_observer.stop()
        my_observer.join()


updates = {}
def on_modified(event):
    # work around https://github.com/gorakhargosh/watchdog/issues/93
    last_updated = updates.get(event.src_path)
    if last_updated and (datetime.now() - last_updated).seconds < 2:
        return

    updates[event.src_path] = datetime.now()
    print(f"{event.src_path} has been modified")


    with open(event.src_path) as f:
        text = f.read()

    update_page(event.src_path[len(PAGES_DIR) +3:-len('.wiki')].replace('_SLASH_', '/'), text, COMMENT)


def update_page(name, new_text, comment):
    print('updating', name)
    page = pywikibot.Page(SITE, name)
    if page.text == new_text:
        print("Nothing changed, not saving")
        return
    page.text = new_text
    page.save(comment)



def save(page):
    filename = PAGES_DIR + '/' + page.title().replace('/', '_SLASH_') + '.wiki'

    with open(filename, 'w') as f:
        f.write(page.text)

    print("saved", filename)

def main():
    parser = argparse.ArgumentParser(description='Syncronize wiki pages with local files')

    parser.add_argument('-s', '--search', required=True, help='search query')
    parser.add_argument('-c', '--comment', default='bot changes', help='change comment')
    parser.add_argument('-l', '--limit', type=int, default=20, help='limit on number of pages to download')
    parser.add_argument('-n', '--namespaces', action='store', nargs="*", default=[0], type=int, help='namespaces to download')

    args = parser.parse_args()

    global COMMENT
    COMMENT = args.comment

    sync(args)

if __name__ == '__main__':
    main()
