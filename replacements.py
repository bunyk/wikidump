''' Derussification '''
import sqlite3
import time

import pywikibot

def main():
    ''' Do derussification '''
    print("Waiting till the time is right")
    for i in range(3600 * 6, 0, -1):
        print('\r%02d:%02d:%02d' % (i // 3600, i % 3600 // 60, i % 60), end='')
        time.sleep(1)

    db = sqlite3.connect('nps.db')
    cursor = db.cursor()

    articles = cursor.execute('SELECT page, count(*) as count from templates where language="ru" and existing_size < alt_size * 1.3 group by page order by count desc').fetchall()

    todo = len(articles)

    for i, (page, count) in enumerate(articles):
        print('%s/%s' % (i, todo), page, count)
        replacements = cursor.execute('SELECT template, requested, text, alt_language, alt_existing from templates where language="ru" and existing_size < alt_size * 1.3 and page=?', (page, )).fetchall()
        p = pywikibot.Page(pywikibot.Site(), page)
        new_text = p.text
        if new_text == '':
            continue
        for template, requested, text, alt_language, alt_existing in replacements:
            if alt_language == 'en':
                alt_language = ''
            if text == requested:
                text = ''
            replacement = '{{нп|%s|%s|%s|%s}}' % (requested, text, alt_language, alt_existing)
            print(template, replacement)
            new_text = new_text.replace(template, replacement)
        if p.text != new_text:
            p.text = new_text
        try:
            p.save('Вікіфікація')
        except Exception as e:
            print(e)

if __name__ == "__main__":
    main()
