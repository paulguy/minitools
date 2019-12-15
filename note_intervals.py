#!/usr/bin/python3

import random
from enum import Enum
import argparse

BIGLETTERS = {
    'A': ("   _ ",
          "  /_\\",
          " //_\\\\",
          "|  _  |",
          "| | | |",
          "|_| |_|"),
    'B': (" ____",
          "|  _ \\",
          "| |_) |",
          "|  _ (",
          "| |_) |",
          "|____/"),
    'C': ("  ___",
          " / _ \\",
          "| | |_|",
          "| |  _",
          "| |_| |",
          " \\___/"),
    'D': (" ____",
          "|  _ \\",
          "| | | |",
          "| | | |",
          "| |_| |",
          "|____/"),
    'E': (" _____",
          "|  ___|",
          "| |__",
          "|  __|",
          "| |___",
          "|_____|"),
    'F': (" _____",
          "|  ___|",
          "| |__",
          "|  __|",
          "| |",
          "|_|"),
    'G': ("  ____",
          " / ___|",
          "| | __",
          "| | \\ |",
          "| |_| |",
          " \\___/"),
    '♭': (" _",
          "| |",
          "| |__",
          "| '_ \\",
          "| |_/ |",
          "|___-'"),
    '♯': ("  _ _",
          "_| | |_",
          "|_   _|",
          "_| | |_",
          "|_   _|",
          " |_|_|"),
    '<': ("   _",
          "  | |",
          " _| |_",
          "\\ \\ / /",
          " \\   /",
          "  \\_/"),
    '>': ("   _",
          "  / \\",
          " /   \\",
          "/_/ \\_\\",
          "  | |",
          "  |_|")
}
BIGLETTERWIDTH = 8
BIGLETTERHEIGHT = 6

def print_big(text : str):
    for i in range(BIGLETTERHEIGHT):
        for char in text:
            print("{:<{width}s}".format(BIGLETTERS[char][i], width=BIGLETTERWIDTH), end='')
        print()

class Direction(Enum):
    UP = 0
    DOWN = 1

    def __str__(self):
        if self == Direction.UP:
            return "going up to"
        return "going down to"

    def arrow(self):
        if self == Direction.UP:
            return '>'
        return '<'


class Note:
    def __init__(self, name : str, num : int):
        self.__name = name
        self.__num = num

    @property
    def num(self):
        return self.__num

    def __str__(self):
        return self.__name

NOTES = (
    Note("A♭", 0),
    Note("A", 1),
    Note("A♯", 2),
    Note("B♭", 2),
    Note("B", 3),
    Note("C", 4),
    Note("C♯", 5),
    Note("D♭", 5),
    Note("D", 6),
    Note("D♯", 7),
    Note("E♭", 7),
    Note("E", 8),
    Note("F", 9),
    Note("F♯", 10),
    Note("G♭", 10),
    Note("G", 11),
    Note("G♯", 0)
)
MAXNOTE = 12

"""
None   - return any
a Note - return any but note
"""
def get_random_note(note = None, max_dist = None, direction = None) -> Note:
    if note == None:
        return NOTES[random.randrange(len(NOTES))]
    if max_dist == None or direction == None:
        raise TypeError
    idx = NOTES.index(note)
    selection = []
    for i in enumerate(NOTES):
        if i[1] == note:
            continue

        distance = None
        if direction == Direction.UP:
            distance = get_distance(note, i[1], Direction.UP)
        elif direction == Direction.DOWN:
            distance = get_distance(note, i[1], Direction.DOWN)

        if distance <= max_dist:
            selection.append(i[1])

    return random.choice(selection)

def get_distance(note1 : Note, note2 : Note, direction : Direction) -> int:
    if note1.num < note2.num:
        if direction == Direction.UP:
            return note2.num - note1.num
        else:
            return ((MAXNOTE + 1) - note2.num) + note1.num
    elif note1.num > note2.num:
        if direction == Direction.UP:
            return ((MAXNOTE + 1) - note1.num) + note2.num
        else:
            return note1.num - note2.num
    else:
        return 0

class EndQuiz(Exception):
    pass

def quiz(max_dist : int):
    note1 = get_random_note()
    direction = Direction(random.randrange(2))
    note2 = get_random_note(note1, max_dist, direction)
    realdist = get_distance(note1, note2, direction)
    dist = None

    while dist == None:
        print_big("{:s}{:s}{:s}".format(str(note1), direction.arrow(), str(note2)))
        ans = input("{:s} {:s} {:s}: ".format(str(note1),
                                              str(direction), 
                                              str(note2)))
        try:
            dist = int(ans)
        except:
            if ans.lower() == 'q':
                raise EndQuiz
            pass

    if dist != realdist:
        print("No, {:s} {:s} {:s} is {:d} intervals away.".format(str(note1),
                                                                  str(direction),
                                                                  str(note2),
                                                                  realdist))
    else:
        print("Correct, {:s} {:s} {:s} is {:d} intervals away.".format(str(note1),
                                                                       str(direction),
                                                                       str(note2),
                                                                       realdist))

def main(max_dist : int):
    if max_dist < 1 or max_dist > MAXNOTE:
        print("Distance must be between 1 and 11.")
        return
    random.seed()
    print("Q/q to quit")
    try:
        while True:
            quiz(max_dist);
    except EndQuiz:
        pass

def test_distances():
    print("UP ", end='')
    for i in NOTES:
        print('{:<3s}'.format(str(i)), end='')
    print()
    for i in NOTES:
        print('{:<3s}'.format(str(i)), end='')
        for j in NOTES:
            print('{:<3d}'.format(get_distance(i, j, Direction.UP)), end='')
        print()
    print()
    print("DN ", end='')
    for i in NOTES:
        print('{:<3s}'.format(str(i)), end='')
    print()
    for i in NOTES:
        print('{:<3s}'.format(str(i)), end='')
        for j in NOTES:
            print('{:<3d}'.format(get_distance(i, j, Direction.DOWN)), end='')
        print()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Flash cards style note intervals quiz")
    parser.add_argument("-l", "--list", help="List all intervals (cheat sheet) and exit", action='store_true')
    parser.add_argument("-d", "--distance", help="Set maximum distance for an interval", type=int, default=MAXNOTE)
    args = parser.parse_args()
    if args.list:
        test_distances()
    else:
        main(args.distance)
