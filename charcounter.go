package main

import (
	"encoding/json"
	"fmt"
	"os"
	"sort"
)

type CharCounter struct {
	charcount map[rune]uint
	count     uint
}

func (cc *CharCounter) Init() {
	cc.charcount = make(map[rune]uint)
	cc.count = 0
}

func (cc *CharCounter) Process(page Page) {
	cc.count++
	if cc.count%123 == 0 {
		fmt.Fprintf(os.Stderr, "\rPages: %d\t\tRunes: %d", cc.count, len(cc.charcount))
	}
	if page.Redirect != nil {
		return // skip redirects
	}
	for _, r := range []rune(page.Text) {
		cc.charcount[r]++
	}

}

func (cc *CharCounter) Summary() {
	top := make([]RuneFreq, len(cc.charcount))
	i := 0
	var sum uint = 0
	for k, v := range cc.charcount {
		top[i] = RuneFreq{k, v}
		i++
		sum += v
	}
	sort.Slice(top, func(i, j int) bool {
		return top[i].Freq > top[j].Freq
	})
	var top255 = [255]rune{}
	for i, rf := range top {
		if i < 255 {
			top255[i] = rf.R
			fmt.Printf("%d) &#%d;: %d\n", i, rf.R, rf.Freq)
		}
	}
	encoding, _ := json.Marshal(top255)
	fmt.Println(string(encoding))
	file, err := os.Create("freq_chars.json")
	if err != nil {
		fmt.Println(err.Error())
	}
	defer file.Close()
	_, err = file.Write(encoding)

	fmt.Printf("Total characters: %d\n", sum)
	fmt.Printf("Different characters: %d\n", len(cc.charcount))
}

type RuneFreq struct {
	R    rune
	Freq uint
}
