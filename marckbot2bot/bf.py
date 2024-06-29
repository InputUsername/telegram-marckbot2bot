from collections import defaultdict

def execute(code, inp = "", steps=10000):
    tape = defaultdict(lambda: 0)
    cur = 0
    loc = 0
    read = 0
    ret = ""

    while steps > 0:
        try:
            c = code[loc]
        except IndexError:
            return ret
        if c == ">":
            cur += 1
        elif c == "<":
            cur -= 1
        elif c == "+":
            if tape[cur] == 255:
                tape[cur] = 0
            else:
                tape[cur] += 1
        elif c == "-":
            if tape[cur] == 0:
                tape[cur] == 255
            else:
                tape[cur] -= 1
        elif c == ".":
            ret += chr(tape[cur])
        elif c == ",":
            try:
                tape[cur] = ord(inp[read])
                read += 1
            except IndexError:
                raise Exception("No data left to read from input")
        elif c == "[" and tape[cur] == 0:
            loop = 1
            loc += 1
            while loop > 0:
                try:
                    c = code[loc]
                except IndexError:
                    raise Exception("Unbalanced parens")
                if c == "[":
                    loop += 1
                elif c == "]":
                    loop -= 1
                loc += 1
        elif c == "]" and tape[cur] != 0:
            loop = 1
            loc -= 1
            while loop > 0:
                try:
                    c = code[loc]
                except IndexError:
                    raise Exception("Unbalanced parens")
                if c == "[":
                    loop -= 1
                elif c == "]":
                    loop += 1
                loc -= 1
        loc += 1
        steps -= 1