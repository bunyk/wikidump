-- Connect to sqlite using sqlite3 filename.db
-- Then run:
-- sqlite> .read create.sql
CREATE TABLE templates (
    spelling TEXT, -- how template was written
    requested TEXT, -- page that was requested
    text TEXT, -- link text to display
    language TEXT, -- language where article exists
    existing TEXT, -- name of existing article
    template TEXT, -- name of template used (could be alias iw, нп5 etc..)
    page TEXT,  -- name of page with template

    alt_language TEXT, -- language of alternative (lets try en)
    alt_existing TEXT, -- name of alternative
    existing_size INT, -- size of existing article
    alt_size INT -- size of alternative
);

CREATE TABLE http_cache (
    url TEXT, 
    response TEXT,
);
