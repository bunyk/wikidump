"""
Wit - wiki git.
"""
import time
from datetime import datetime
import argparse
from itertools import islice
import glob
import os

import click
import pywikibot
from pywikibot import pagegenerators
from diff_match_patch import diff_match_patch

SITE = pywikibot.Site("uk", "wikipedia")
PAGES_DIR = 'pages'

COMMENT = ''

@click.command()
@click.argument('search_query')
@click.option('-l', '--limit', type=int, default=100, help='limit on number of pages to download')
@click.option('-n', '--namespaces', default=[0], type=int, multiple=True, help='namespaces to download')
def pull(search_query, limit, namespaces):
    for page in islice(search(search_query, namespaces), limit):
        save(page)

@click.command()
@click.argument('comment')
def push(comment):
    push_changes(False, comment)

@click.command()
def diff():
    push_changes(True, '')

@click.command()
def cleanup():
    for f in glob.glob(PAGES_DIR + '/*.wiki'):
        os.remove(f)
    for f in glob.glob(PAGES_DIR + '_orig/*.wiki'):
        os.remove(f)

def push_changes(dry, comment):
    for filepath in glob.iglob(PAGES_DIR + '/*.wiki'):
        page_name = filepath[len(PAGES_DIR) + 1:-len('.wiki')].replace('_SLASH_', '/')
        with open(filepath) as f:
            changes = f.read()
        with open(PAGES_DIR + '_orig' + filepath[len(PAGES_DIR):]) as f:
            original = f.read()
        if changes != original:
            apply_patch(dry, page_name, changes, original, comment)
            if not dry:
                with open(PAGES_DIR + '_orig' + filepath[len(PAGES_DIR):], 'w') as f:
                    f.write(changes)

def search(query, namespaces):
    with open(PAGES_DIR + '/exclude.lst') as f:
        excludes = set(l.strip() for l in f)

    for page in pagegenerators.SearchPageGenerator(query, site=SITE, namespaces=namespaces):
        title = page.title()
        if title in excludes:
            continue
        yield page

def apply_patch(dry, name, new_text, original, comment):
    print('Page:', name)
    dmp = diff_match_patch()
    patches = dmp.patch_make(original, new_text)

    page = pywikibot.Page(SITE, name)
    if page.text == new_text:
        print("Already changed, not saving")
        return

    new_text, _ = dmp.patch_apply(patches, page.text)

    new_text = new_text.strip()

    pywikibot.showDiff(page.text, new_text)

    if dry:
        return
    page.text = new_text
    page.save(comment)

def save(page):
    filename = page.title().replace('/', '_SLASH_') + '.wiki'

    with open(PAGES_DIR + '/' + filename, 'w') as f:
        f.write(page.text)

    with open(PAGES_DIR + '_orig/' + filename, 'w') as f:
        f.write(page.text)

    print("saved", filename)


@click.group()
def main():
    """ Wiki git. Try to interact with wikipedia like with Git repository """
    pass

main.add_command(pull)
main.add_command(push)
main.add_command(diff)
main.add_command(cleanup)

if __name__ == '__main__':
    main()
