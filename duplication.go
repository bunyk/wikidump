package main

import (
	"bufio"
	"fmt"
	"log"
	"math/big"
	"os"
	"strconv"
	// "sort"
)

const LIMIT_PAGES = 100000 // 0 for unlimited sample
const PATTERN_SIZE = 10000
const HASHES_ARRAY_SIZE = 10000000
const HASHES_COUNT = 5
const TOP_N = 100
const DUPLICATED_TOP = TOP_N * 100

const padding = "                                                  "

func main() {
	if len(os.Args) < 2 {
		log.Fatal("Please specify a file to read")
	}
	topHashCounts(os.Args[1])

	// WRONG!!!!!!!!!!!!!
	// sort.Ints(hash_counts[:])
}

func isPrime(n int) bool {
	b := big.NewInt(int64(n))
	return b.ProbablyPrime(20)
}

func topHashCounts(filename string) {
	var i, j int
	var hash_counts [HASHES_ARRAY_SIZE][HASHES_COUNT]byte

	var hash_sizes [HASHES_COUNT]int
	hash_sizes[0] = HASHES_ARRAY_SIZE
	for i = 0; i < HASHES_COUNT; i++ {
		if i > 0 {
			hash_sizes[i] = hash_sizes[i-1]
		}
		for !isPrime(hash_sizes[i]) {
			hash_sizes[i]--
		}
	}
	var base_on_the_left [HASHES_COUNT]int
	var hashes [HASHES_COUNT]int
	for i = 0; i < HASHES_COUNT; i++ {
		base_on_the_left[i] = 1
	}
	for i = 0; i < PATTERN_SIZE-1; i++ {
		for j = 0; j < HASHES_COUNT; j++ {
			base_on_the_left[j] = (base_on_the_left[j] << 16) % hash_sizes[j]
		}
	}
	forEachPage(filename, func(page []rune) {
		if len(page) < PATTERN_SIZE {
			return
		}
		for j = 0; j < HASHES_COUNT; j++ {
			hashes[j] = 0
		}
		for i = 0; i < PATTERN_SIZE; i++ {
			for j = 0; j < HASHES_COUNT; j++ {
				hashes[j] = ((hashes[j] << 16) + int(page[i])) % hash_sizes[j]
			}
		}
		for j = 0; j < HASHES_COUNT; j++ {
			if hashes[j] < 0 {
				hashes[j] += hash_sizes[j]
			}
			if hash_counts[hashes[j]][j] < 255 {
				hash_counts[hashes[j]][j]++
			}
		}
		for ; i < len(page); i++ {
			for j = 0; j < HASHES_COUNT; j++ {
				hashes[j] = ((hashes[j]-int(page[i-PATTERN_SIZE])*base_on_the_left[j])<<16 + int(page[i])) % hash_sizes[j]
				if hashes[j] < 0 {
					hashes[j] += hash_sizes[j]
				}
				if hash_counts[hashes[j]][j] < 255 {
					hash_counts[hashes[j]][j]++
				}
			}
		}
	})
	duplicated := 0
	for _, count := range hash_counts {
		var min_count byte = 255
		for j = 0; j < HASHES_COUNT; j++ {
			if count[j] < min_count {
				min_count = count[j]
			}
		}
		if min_count >= 2 {
			fmt.Println(count)
			duplicated++
		}
	}
	fmt.Println("Duplicated:", duplicated, (100.0 * duplicated / HASHES_ARRAY_SIZE), "%")
}

func forEachPage(filename string, cb func([]rune)) {
	var page []rune
	var err error
	var count int

	file, err := os.Open(filename)
	if err != nil {
		log.Fatal(err)
	}
	defer file.Close()

	fmt.Println("Processing dump")
	scanner := bufio.NewScanner(file)
	for {
		if !scanner.Scan() {
			break
		}
		title := scanner.Text()
		if !scanner.Scan() {
			break
		}
		lines, err := strconv.Atoi(scanner.Text())
		lines++ // TODO: increment this in dump2txt
		dieOnErr(err)

		page = page[:0]
		for i := 0; i < lines; i++ {
			if !scanner.Scan() {
				dieOnErr(fmt.Errorf("Less lines than promised"))
			}
			page = append(page, []rune(scanner.Text())...)
		}
		cb(page)
		count++

		if count%1379 == 0 {
			fmt.Fprintf(
				os.Stderr,
				"\rProcessed pages: %d. Processing %d characters of: %s",
				count,
				len(page),
				(title + padding)[0:50],
			)
			if LIMIT_PAGES > 0 && count > LIMIT_PAGES {
				break
			}
		}
	}
	dieOnErr(scanner.Err())
}

func dieOnErr(err error) {
	if err != nil {
		log.Fatal(err)
	}
}
