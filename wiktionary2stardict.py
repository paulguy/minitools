#!/usr/bin/env python3

import sys
import json
import re
import pathlib
import struct
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional
import pprint

class WordType(Enum):
    INTERFIX = auto()
    PROVERB = auto()
    PREP = auto()
    NAME = auto()
    PREP_PHRASE = auto()
    PARTICLE = auto()
    ADJ = auto()
    SYMBOL = auto()
    PHRASE = auto()
    CONJ = auto()
    COMBINING_FORM = auto()
    ADV_PHRASE = auto()
    NOUN = auto()
    PREFIX = auto()
    HARD_REDIRECT = auto()
    INTJ = auto()
    INFIX = auto()
    PUNCT = auto()
    CHARACTER = auto()
    POSTP = auto()
    NUM = auto()
    ARTICLE = auto()
    SUFFIX = auto()
    ADV = auto()
    DET = auto()
    PRON = auto()
    VERB = auto()

STR_TO_WORDTYPE : dict[str, WordType] = {
    'interfix': WordType.INTERFIX,
    'proverb': WordType.PROVERB,
    'prep': WordType.PREP,
    'name': WordType.NAME,
    'prep_phrase': WordType.PREP_PHRASE,
    'particle': WordType.PARTICLE,
    'adj': WordType.ADJ,
    'symbol': WordType.SYMBOL,
    'phrase': WordType.PHRASE,
    'conj': WordType.CONJ,
    'combining_form': WordType.COMBINING_FORM,
    'adv_phrase': WordType.ADV_PHRASE,
    'noun': WordType.NOUN,
    'prefix': WordType.PREFIX,
    'hard-redirect': WordType.HARD_REDIRECT,
    'intj': WordType.INTJ,
    'infix': WordType.INFIX,
    'punct': WordType.PUNCT,
    'character': WordType.CHARACTER,
    'postp': WordType.POSTP,
    'num': WordType.NUM,
    'article': WordType.ARTICLE,
    'suffix': WordType.SUFFIX,
    'adv': WordType.ADV,
    'det': WordType.DET,
    'pron': WordType.PRON,
    'verb': WordType.VERB
}

WORDTYPE_TO_NAME : dict[WordType, str] = {
    WordType.INTERFIX: "Interfix",
    WordType.PROVERB: "Proverb",
    WordType.PREP: "Preposition",
    WordType.NAME: "Proper Name",
    WordType.PREP_PHRASE: "Prepositional Phrase",
    WordType.PARTICLE: "Particle",
    WordType.ADJ: "Adjective",
    WordType.SYMBOL: "Symbol",
    WordType.PHRASE: "Phrase",
    WordType.CONJ: "Conjunction",
    WordType.COMBINING_FORM: "Combining Form",
    WordType.ADV_PHRASE: "Adverbial Phrase",
    WordType.NOUN: "Noun",
    WordType.PREFIX: "Prefix",
    WordType.HARD_REDIRECT: "Hard Redirect",
    WordType.INTJ: "Interjection",
    WordType.INFIX: "Infix",
    WordType.PUNCT: "Punctuation",
    WordType.CHARACTER: "Character",
    WordType.POSTP: "Postposition",
    WordType.NUM: "Number",
    WordType.ARTICLE: "Article",
    WordType.SUFFIX: "Suffix",
    WordType.ADV: "Adverb",
    WordType.DET: "Determiner",
    WordType.PRON: "Pronoun",
    WordType.VERB: "Verb"
}

ALLOWED_WORDTYPES : set[WordType] = {
    WordType.PREP,
    WordType.NAME,
    WordType.PARTICLE,
    WordType.ADJ,
    WordType.CONJ,
    WordType.NOUN,
    WordType.INTJ,
    WordType.POSTP,
    WordType.NUM,
    WordType.ADV,
    WordType.DET,
    WordType.PRON,
    WordType.VERB
}

DISALLOWED_FORM_TAGS : set[str] = {
    'table-tags',
    'inflection-template',
    'class'
}

DECLENSION_TABLE_COLUMNS : set[str] = {
    "singular",
    "plural",
    "masculine",
    "neuter",
    "feminine"
}

DECLENSION_TABLE_EXTRAS : set[str] = {
    "animate",
    "inanimate"
}

@dataclass
class Example:
    text : str
    english : str

    def __str__(self):
        return f"{self.text} -> {self.english}"

class Definition:
    definition : str
    examples : Optional[list[Example]]
    DESCRIPTIVE_WORDS : set[str] = {
        "singular",
        "plural",
        "masculine",
        "neuter",
        "feminine",
        "perfective",
        "imperfective"
    }
    WORD_RE : re.Pattern = re.compile('\\sof\\s+([^\\s]+)')

    def __init__(self, definition : str):
        self.definition = definition
        self.examples = None

    def redirect_of(self) -> Optional[str]:
        # some dubious heuristics
        # if the definition text contains at least 2 of some descriptive words
        # since as far as I've seen, at least gender and number are given for
        # noun cases and participles and at least perfectiveness and number for
        # verbs
        # This is mostly for debugging as it captures some false-positives and
        # only misses a handful of malformed pages
        defn = self.definition.lower()
        count = 0
        for item in Definition.DESCRIPTIVE_WORDS:
            if item in defn:
                count += 1
        if count < 2:
            return None
        match = Definition.WORD_RE.search(defn)
        if match is None:
            return None
        return match.group(1)

    def __str__(self):
        if self.examples is None:
            return self.definition
        ret = f"{self.definition}\n"
        if self.examples is not None:
            ret += '\n'.join(str(x) for x in self.examples)
        return ret

    def htmlize(self):
        ret = f"<li><p>{self.definition}</p>"
        if self.examples is not None:
            ret += "<ul>"
            ret += ''.join(f"<li>{x}</li>" for x in self.examples)
            ret += "</ul>"
        ret += "</li>"
        return ret

@dataclass
class Word:
    wordtype : WordType
    head_templates : list[str]
    definitions : list[Definition]

    def __str__(self):
        ret = f"{WORDTYPE_TO_NAME[self.wordtype]}\n"
        ret += '\n'.join(str(x) for x in self.head_templates)
        ret += '\n'.join(str(x) for x in self.definitions)
        return ret

    def htmlize(self):
        ret = f"<p><b>{WORDTYPE_TO_NAME[self.wordtype]}</b></p>"
        ret += ''.join(f"<p>{x}</p>" for x in self.head_templates)
        ret += "<ol>"
        ret += ''.join(x.htmlize() for x in self.definitions)
        ret += "</ol>"
        return ret


def try_delete_from_dict(d : dict, k : str):
    try:
        del d[k]
    except KeyError:
        pass

def pp_record(record):
    try_delete_from_dict(record, 'categories')
    try_delete_from_dict(record, 'descendants')
    try_delete_from_dict(record, 'etymology_templates')
    try_delete_from_dict(record, 'sounds')
    try_delete_from_dict(record, 'derived')
    try_delete_from_dict(record, 'holonyms')
    try_delete_from_dict(record, 'hypernyms')
    try_delete_from_dict(record, 'hyponyms')
    try_delete_from_dict(record, 'related')
    pprint.pprint(record)

def add_mapping(mappings : dict[str, set[str]],
                original : str,
                alternate : str):
    # remove stress marks
    original = original.replace(chr(0x301), '')
    if ' ' in original:
        return
    if original == alternate:
        return
    if original not in mappings:
        mappings[original] = set()
    if alternate in mappings:
        mappings[original].update(mappings[alternate])
        del mappings[alternate]
    mappings[original].update((alternate,))

def add_record(words : dict[str, list[Definition]],
               mappings : dict[str, set[str]],
               record : dict):
    wordtype = STR_TO_WORDTYPE[record['pos']]
    # remove stress marks
    # they're pretty inconsistently used on wiktionary and they create a lot of copies
    wordname = record['word'].replace(chr(0x301), '')
    if ' ' not in wordname:
        # koreader can't get definitions of multiple-word phrases
        if wordtype in ALLOWED_WORDTYPES:
            senses = record['senses']
            # if tagged as a form of another word, just add it as a mapping
            redirect = False
            for sense in senses:
                if 'form_of' in sense:
                    redirect = True
                    for form in sense['form_of']:
                        form_of = form['word']
                        add_mapping(mappings, form_of, wordname)
                if 'alt_of' in sense:
                    redirect = True
                    for alt in sense['alt_of']:
                        alt_of = alt['word']
                        add_mapping(mappings, alt_of, wordname)
                elif 'tags' in sense and 'participle' in sense['tags']:
                    redirect = True
                    # this is probably unreliable
                    if 'links' in sense:
                        participle_of = sense['links'][0][0]
                        add_mapping(mappings, participle_of, wordname)
            if redirect:
                return

            definitions : list[Definition] = []
            for sense in senses:
                definition = None
                if 'raw_glosses' in sense:
                    definition = Definition(', '.join(sense['raw_glosses']))
                elif 'glosses' in sense:
                    definition = Definition(', '.join(sense['glosses']))
                else:
                    # no definitions
                    return
                #redirect_of = definition.redirect_of()
                #if redirect_of is not None:
                #    pprint.pprint(record)
                #    return
                if 'examples' in sense:
                    definition.examples = []
                    for example in sense['examples']:
                        if 'text' in example and 'english' in example:
                            definition.examples.append(Example(example['text'], example['english']))
                definitions.append(definition)
            head_templates : list[str] = []
            if 'head_templates' not in record:
                head_templates.append([wordname])
            else:
                for ht in record['head_templates']:
                    head_templates.append(ht['expansion'])
            word = Word(wordtype, head_templates, definitions)
            if wordname not in words:
                words[wordname] = []
            words[wordname].append(word)

def parse_file(path : pathlib.Path, num=-1) -> (dict[str, list[Definition]],
                                                dict[str, list[str]]):
    words : dict[str, list[Definition]] = {}
    mappings : dict[str, list[str]] = {}

    with path.open('r') as infile:
        for line in infile:
            record = json.loads(line)
            if STR_TO_WORDTYPE[record['pos']] in ALLOWED_WORDTYPES:
                add_record(words, mappings, record)
                #pp_record(record)
                if num >= 0:
                    num -= 1
                    if num == 0:
                        break

    return words, mappings

def clean_mappings(words : dict[str, list[Definition]],
                   mappings : dict[str, list[str]]):
    mapkeys = list(mappings.keys())
    wordset = set(words.keys())
    orig_len = len(mapkeys)

    # remove mappings that don't map to any existing words
    for mapping in mapkeys:
        if mapping not in words:
            del mappings[mapping]

    mapkeys = list(mappings.keys())
    for num, mapping in enumerate(mapkeys):
        if num % 100 == 0:
            print(f"{num}/{orig_len}", end='\r')
        # remove mappings that would alias defined words
        mappings[mapping].difference_update(mappings[mapping].intersection(wordset))

        for mapping2 in mapkeys[num+1:]:
            if mappings[mapping] == mappings[mapping2]:
                # remove totally ambiguous duplicate mappings
                mappings[mapping] = set()
                mappings[mapping2] = set()
            else:
                # remove duplicate mappings
                mappings[mapping].difference_update(mappings[mapping].intersection(mappings[mapping2]))
    print(f"{orig_len}/{orig_len}")

    # delete all the empty ones
    for mapping in mapkeys:
        if len(mappings[mapping]) == 0:
            del mappings[mapping]
    print(f"Reduced from {orig_len} to {len(mappings)}")

def write_dict(words : dict[str, list[Definition]]) -> (list[tuple[str, int]],
                                                        dict[str, int]):
    dict_offsets : list[tuple[str, int, int]] = []
    dict_indexes : dict[str, int] = {}
    wordlist = list(words.keys())

    with open("stardict.dict", 'wb') as outfile:
        for num, word in enumerate(wordlist):
            dict_indexes[word] = num
            offset = outfile.tell()
            for definition in words[word]:
                outfile.write(definition.htmlize().encode('utf-8'))
            dict_offsets.append((word, offset, outfile.tell() - offset))
        print(f"{len(wordlist)}/{len(wordlist)}")

    return dict_offsets, dict_indexes

IDX_ENTRY = struct.Struct(">BII")
def write_idx(dict_offsets : list[tuple[str, int]]) -> int:
    size = 0
    with open("stardict.idx", 'wb') as outfile:
        for entry in dict_offsets:
            outfile.write(entry[0].encode('utf-8'))
            outfile.write(IDX_ENTRY.pack(0, entry[1], entry[2]))
        size = outfile.tell()

    return size

SYN_ENTRY = struct.Struct(">BI")
def write_syn(mappings : dict[str, list[str]],
              dict_indexes : dict[str, int]) -> int:
    count = 0
    with open("stardict.syn", 'wb') as outfile:
        for mapping in mappings.keys():
            count += len(mappings[mapping])

            for syn in mappings[mapping]:
                outfile.write(syn.encode('utf-8'))
                outfile.write(SYN_ENTRY.pack(0, dict_indexes[mapping]))

    return count

IFO_MAGIC = "StarDict's dict ifo file\n"
def write_ifo(name : str,
              wordcount : int,
              syn_count : int,
              idx_file_size : int):
    with open("stardict.ifo", 'w', encoding='utf-8') as outfile:
        outfile.write(IFO_MAGIC)
        outfile.write("version=3.0.0\n")
        outfile.write(f"bookname={name}\n")
        outfile.write(f"wordcount={wordcount}\n")
        outfile.write(f"synwordcount={syn_count}\n")
        outfile.write(f"idxfilesize={idx_file_size}\n")
        outfile.write("sametypesequence=h\n")

outpath = pathlib.Path(sys.argv[1])

print("Parsing file and collecting definitions and alternates")
words, mappings = parse_file(outpath)
print(f"Found {len(words)} unique words with definitions (not alternates)")

print("Removing duplicate and ambiguous alternates (slow!)")
clean_mappings(words, mappings)

print("Writing dict")
dict_offsets, dict_indexes = write_dict(words)

print("Writing index")
idx_file_size = write_idx(dict_offsets)

print("Writing synonyms")
syn_count = write_syn(mappings, dict_indexes)

print("Writing ifo")
write_ifo(outpath.stem, len(dict_offsets), syn_count, idx_file_size)

print("done")
