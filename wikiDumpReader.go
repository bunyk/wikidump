package main

import (
	"compress/bzip2"
	"encoding/xml"
	"io"
	"log"
	"os"
	"strings"
)

type Page struct {
	Title     string    `xml:"title"`
	Namespace int       `xml:"ns"`
	Id        int       `xml:"id"`
	Text      string    `xml:"revision>text"`
	Redirect  *Redirect `xml:"redirect"`
}

type Redirect struct {
	To string `xml:"title,attr"`
}

func (p Page) String() string {
	redirect := ""
	if p.Redirect != nil {
		redirect = "-> " + p.Redirect.To
	}
	return p.Title + redirect + ": " + (p.Text + strings.Repeat(" ", 50))[:50]
}

func Read(filename string) <-chan Page {
	out := make(chan Page, 100)
	go func() {
		f, err := os.Open(filename)
		stopOnError(err)
		decompressedFile := bzip2.NewReader(f)
		xmlReader := xml.NewDecoder(decompressedFile)
		for {
			t, err := xmlReader.Token()
			if err == io.EOF {
				close(out)
				break
			}
			stopOnError(err)
			switch t := t.(type) {
			case xml.StartElement:
				if t.Name.Local == "page" {
					var page Page
					stopOnError(xmlReader.DecodeElement(&page, &t))
					stopOnError(err)
					out <- page
				}
			}
		}
	}()
	return out
}

func stopOnError(err error) {
	if err != nil {
		log.Fatal(err)
	}
}

type PageProcessor interface {
	Init()
	Process(p Page)
	Summary()
}

func RunProcessor(processor PageProcessor, limit int) {
	if len(os.Args) < 2 {
		log.Fatal("Please specify a file to read")
	}
	processor.Init()
	processed := 0
	for page := range Read(os.Args[1]) {
		if limit >= 0 && processed >= limit {
			break
		}
		processed++
		processor.Process(page)
	}
	processor.Summary()
}
