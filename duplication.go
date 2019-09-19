package main

import (
	"fmt"
	"hash/fnv"
	"log"
	"net/http"
	_ "net/http/pprof"
	"os"
	"sort"
)

const PATTERN_SIZE = 100
const HASHES_ARRAY_SIZE = 10000000
const TOP_N = 50
const DUPLICATED_TOP = TOP_N * 100

func hash(str []rune) int {
	h := fnv.New32a()
	h.Write([]byte(string(str)))
	return int(h.Sum32()) % HASHES_ARRAY_SIZE
}

const padding = "                                                  "

func main() {
	go func() {
		log.Println(http.ListenAndServe("localhost:6060", nil))
	}()
	var hash_counts [HASHES_ARRAY_SIZE]int
	if len(os.Args) < 2 {
		log.Fatal("Please specify a file to read")
	}
	filename := os.Args[1]
	count := 0
	fmt.Println("Processing dump")
	for page := range Read(filename) {
		if page.Redirect != nil {
			continue // skip redirects
		}
		if page.Namespace != 0 {
			continue // skip non articles
		}
		count++
		if count%123 == 0 {
			fmt.Fprintf(
				os.Stderr,
				"\rPages: %d. Processing: %s",
				count,
				(page.Title + padding)[0:50],
			)
		}
		text := []rune(page.Text)
		for i := 0; i < len(text)-PATTERN_SIZE; i++ {
			pattern := text[i : i+PATTERN_SIZE]
			h := hash(pattern)
			hash_counts[h]++
		}
	}
	sort.Ints(hash_counts[:])
	for i := HASHES_ARRAY_SIZE - DUPLICATED_TOP; i < HASHES_ARRAY_SIZE; i++ {
		fmt.Println(i, hash_counts[i])
	}
}
