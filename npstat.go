package main

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"log"
	"net/http"
	"net/url"
	"os"
	"regexp"
	"strings"
	"time"
	"unicode"

	_ "github.com/mattn/go-sqlite3"
)

type NpStats struct {
	db *sql.DB
}

func (np *NpStats) Init() {
	if len(os.Args) < 3 {
		log.Fatal("Please specify a file to read and database to write")
	}
	var err error
	np.db, err = sql.Open("sqlite3", os.Args[2])
	if err != nil {
		log.Fatalf("Error connecting to db: %s", err.Error())
	}
}

func (np *NpStats) Process(page Page) {
	if page.Namespace != 0 {
		return // skip all namespaces except main
	}
	if page.Redirect != nil {
		return // skip redirects
	}
	defer func() {
		if r := recover(); r != nil {
			np.Summary()
			log.Fatal(r)
		}
	}()
	// fmt.Println("\n\t", page.Title)
	var altLang, altExisting string
	var existingSize, altSize int
	for _, tmpl := range pageTemplates(page.Text) {
		parsed := parseTemplate(tmpl)
		if parsed.Language == "ru" {
			altLang, altExisting = getAlternativeTo(parsed.Language, parsed.Existing)
			if altLang != "" {
				existingSize = getPageSize(parsed.Language, parsed.Existing)
				altSize = getPageSize(altLang, altExisting)
				fmt.Printf("%v, %v, %v, %v, %v, %v, %v, %v, %v, %v, %v\n", parsed.Spelling, parsed.Requested, parsed.Text, parsed.Language, parsed.Existing, tmpl, page.Title, altLang, altExisting, existingSize, altSize)
			}
		}
		_, err := np.db.Exec(`insert into templates
			(spelling, requested, text , language , existing, template, page, alt_language, alt_existing, existing_size, alt_size)
			VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
		`, parsed.Spelling, parsed.Requested, parsed.Text, parsed.Language, parsed.Existing, tmpl, page.Title, altLang, altExisting, existingSize, altSize,
		)
		fear(err)
	}
}

func fear(err error) {
	if err != nil {
		panic(err.Error())
	}
}

func (np *NpStats) Summary() {
	np.db.Close()
}

// To get alternative languages, do:
// curl "https://www.wikidata.org/w/api.php?action=wbgetentities&sites=ruwiki&titles=Бечей&format=json" | python -mjson.tool
func getAlternativeTo(language, article string) (string, string) {
	path := fmt.Sprintf(
		"https://www.wikidata.org/w/api.php?action=wbgetentities&sites=%swiki&titles=%s&format=json",
		language, url.PathEscape(article),
	)
	resp, err := http.Get(path)
	time.Sleep(200 * time.Millisecond)
	fear(err)
	defer resp.Body.Close()
	body, err := ioutil.ReadAll(resp.Body)
	fear(err)
	var data map[string]interface{}
	err = json.Unmarshal(body, &data)
	if err != nil {
		return "", ""
	}
	entities := data["entities"].(map[string]interface{})
	for _, ei := range entities {
		sitelinks, ok := ei.(map[string]interface{})["sitelinks"]
		if !ok {
			return "", ""
		}
		link, ok := sitelinks.(map[string]interface{})["enwiki"]
		if ok {
			llink, ok := link.(map[string]interface{})
			if !ok {
				return "", ""
			}
			t, ok := llink["title"]
			if !ok {
				return "", ""
			}
			title, ok := t.(string)
			if !ok {
				return "", ""
			}
			return "en", title
		}
	}
	return "", ""
}

func getPageSize(language, article string) int {
	path := fmt.Sprintf(
		"https://%s.wikipedia.org/w/api.php?action=query&prop=revisions&rvprop=content&format=jsonfm&formatversion=2&titles=%s",
		language, url.PathEscape(article),
	)
	resp, err := http.Get(path)
	time.Sleep(200 * time.Millisecond)

	fear(err)
	defer resp.Body.Close()
	body, err := ioutil.ReadAll(resp.Body)
	return len(body)
}

func parseTemplate(markup string) IwTemplate {
	markup = strings.TrimFunc(markup, func(r rune) bool {
		return r == '{' || r == '}' || unicode.IsSpace(r)
	})
	parts := strings.Split(markup, "|")
	res := IwTemplate{}
	orderOffset := 0
	for i, part := range parts {
		if strings.Contains(part, "=") {
			kv := strings.SplitN(part, "=", 2)
			orderOffset++
			k := strings.TrimSpace(kv[0])
			v := strings.TrimSpace(kv[1])
			switch k {
			case "1":
				fallthrough
			case "треба":
				res.Requested = v
			case "2":
				fallthrough
			case "текст":
				res.Text = v
			case "3":
				fallthrough
			case "мова":
				res.Language = v
			case "4":
				fallthrough
			case "є":
				res.Existing = v
			default:
				fmt.Println("Unknown params:", markup)
			}
		} else {
			part = strings.TrimSpace(part)
			switch i - orderOffset {
			case 0:
				res.Spelling = part
			case 1:
				res.Requested = part
			case 2:
				res.Text = part
			case 3:
				res.Language = part
			case 4:
				res.Existing = part
			}
		}
	}
	if res.Text == "" {
		res.Text = res.Requested
	}
	if res.Language == "" {
		res.Language = "en"
	}
	if res.Existing == "" {
		res.Existing = res.Requested
	}
	return res
}

type IwTemplate struct {
	Spelling  string
	Requested string
	Text      string
	Language  string
	Existing  string
}

var npPattern = regexp.MustCompile(
	`\{\{([Нн]п5?1?|[Ii]w2?|[N]name|[Нн]еперекладена стаття|[Нн]еперекладено|[Нн]е переведено 5)\|.*?\}\}`,
)

func pageTemplates(text string) []string {
	return npPattern.FindAllString(text, -1)
}
