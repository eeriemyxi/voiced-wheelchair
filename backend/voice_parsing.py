from dataclasses import dataclass
from enum import Enum


class MovementType(Enum):
    FORWARD = "forward"
    BACKWARD = "backward"
    LEFT = "left"
    RIGHT = "right"

    @classmethod
    def from_str(cls, move: str):
        if move in ("back", "backwards", "reverse", "down"):
            return cls.BACKWARD
        elif move in ("up", "forwards"):
            return cls.FORWARD
        return cls(move)


@dataclass
class Movement:
    move: MovementType
    duration: int


MOVEMENTS = ("forward", "forwards", "up", "down", "reverse", "down", "backward", "backwards", "left", "right")


def peek(after: int, lst: list):
    if after < (len(lst) - 1):
        return lst[after + 1]
    return None


def word_to_num(word: str):
    if word.isdigit():
        return int(word)
    maps = dict(
        one=1, two=2, three=3, four=4, five=5, six=6, seven=7, eight=8, nine=9, zero=0
    )
    return maps[word]


def parse_speech(speech: str):
    instructions = []
    tokens = speech.casefold().split()
    i = 0
    while i < len(tokens):
        if tokens[i] in MOVEMENTS:
            move = MovementType.from_str(tokens[i])
            if peek(i, tokens) == "for":
                i += 1
                num = word_to_num(peek(i, tokens))
                instructions.append(Movement(move, num))
            elif peek(i, tokens) == "then":
                instructions.append(Movement(move, 1))
                i += 1
                continue
            elif peek(i, tokens) is None:
                instructions.append(Movement(move, 1))
                break
        i += 1
    return instructions


print(parse_speech("forward for two seconds then right then left"))
