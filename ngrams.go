package main

import (
	"fmt"
	"log"
)

type Ngrams struct {
	Size   int
	ngrams map[string]uint
	count  uint
}

func (ng *Ngrams) Init() {
	ng.ngrams = make(map[string]uint)
	ng.count = 0
}

func (ng *Ngrams) Process(page Page) {
	if page.Namespace != 0 {
		return // skip all namespaces except main
	}
	if page.Redirect != nil {
		return // skip redirects
	}

	ng.count++
	if ng.count%123 == 0 {
		fmt.Fprintf(os.Stderr, "\rPages: %d\t\tRunes: %d", cc.count, len(cc.charcount))
	}
	defer func() {
		if r := recover(); r != nil {
			ng.Summary()
			log.Fatal(r)
		}
	}()
	fmt.Println("\n\t", page.Title)
	text := []rune(page.Text)
	for i := 0; i <= len(text)-ng.Size; i++ {
		fmt.Println(string(text[i : i+ng.Size]))
	}
}

func (ng *Ngrams) Summary() {
}
