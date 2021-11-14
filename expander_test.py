from datetime import datetime

text = """
== Зноски ==
<references>
<ref name="spotify">https://developer.spotify.com/documentation/web-api/reference/tracks/get-audio-features/</ref>
<ref name="qz">https://qz.com/1331549/these-are-the-best-songs-to-dance-to-according-to-computer-science/</ref>
</references>
"""

expected = """
== Зноски ==
<references>
<ref name="spotify">{{cite web
 |url          = https://developer.spotify.com/documentation/web-api/reference/tracks/get-audio-features/
 |назва        = test title <!-- заголовок згенерований ботом -->
 |автор        = test author
 |дата         =
 |веб-сайт     = test site
 |видавець     =
 |дата-доступу = 14 листопада 2021
}}</ref>
<ref name="qz">{{cite web
 |url          = https://qz.com/1331549/these-are-the-best-songs-to-dance-to-according-to-computer-science/
 |назва        = test title <!-- заголовок згенерований ботом -->
 |автор        = test author
 |дата         =
 |веб-сайт     = test site
 |видавець     =
 |дата-доступу = 14 листопада 2021
}}</ref>
</references>
"""

def mock_metadata(url):
    from expander import Fields
    return Fields(
        title = 'test title',
        site = 'test site',
        author = 'test author',
    )

def test_templetify_links():
    import expander
    expander.metadata = mock_metadata
    expander.now = datetime(2021, 11, 14)
    from expander import templetify_links
    expanded = templetify_links(text)
    assert expanded == expected
