package main

import (
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
		return top[i].Freq < top[j].Freq
	})
	for i, rf := range top {
		fmt.Println("%d) &#%d;: %d", len(cc.charcount)-i, rf.R, rf.Freq)
	}
	fmt.Println("Total characters: %d", sum)
	fmt.Println("Different characters: %d", len(cc.charcount))
}

type RuneFreq struct {
	R    rune
	Freq uint
}
