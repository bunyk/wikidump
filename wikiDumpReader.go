package main

import (
	"compress/bzip2"
	"encoding/xml"
	"os"
	"strings"
	"github.com/eliben/gosax"
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

type Reader struct {
	xmlReader *xml.Decoder
}

func NewReader(filename string) (*Reader, error) {
	f, err := os.Open(filename)
	if err != nil {
		return nil, err
	}
	return &Reader{
		xmlReader: xml.NewDecoder(bzip2.NewReader(f)),
	}, nil
}

// Returns io.EOF as error in case of end of file
func (r Reader) NextPage() (*Page, error) {
	var page Page
	var err error
	var token xml.Token
	for {
		token, err = r.xmlReader.Token()
		if err != nil {
			return nil, err
		}
		switch token := token.(type) {
		case xml.StartElement:
			if token.Name.Local == "page" {
				err = r.xmlReader.DecodeElement(&page, &token)
				return &page, err
			}
		}
	}
}
