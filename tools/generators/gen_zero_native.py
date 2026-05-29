"""Generate verified `zero_native` tasks.

Every fixture is compiled AND run through the real `zero` toolchain; the
expected stdout is captured from that run (never guessed), so each task ships
with a provably-correct oracle solution. Fixtures that fail to compile or run
are dropped and reported.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common

ZERO_VERSION = common.zero_runner.zero_version()
PAT_MAIN = r"pub\s+fn\s+main"
PAT_WRITE = r"world\.out\.write"


# ---- fixture builders (return Zero source) ----

def b_print(msg: str) -> str:
    return f'pub fn main(world: World) -> Void raises {{\n    check world.out.write("{msg}\\n")\n}}\n'


def b_arith(a: int, b: int, op: str) -> str:
    return common.FMT_U32 + f"""
pub fn main(world: World) -> Void raises {{
    let a: u32 = {a}
    let b: u32 = {b}
    let r: u32 = a {op} b
    var buf: [10]u8 = [0; 10]
    check world.out.write(fmt_u32(buf, r))
    check world.out.write("\\n")
}}
"""


def b_factorial(n: int) -> str:
    return common.FMT_U32 + f"""
fn factorial(n: u32) -> u32 {{
    var i: u32 = 1
    var acc: u32 = 1
    while i <= n {{
        acc = acc * i
        i = i + 1
    }}
    return acc
}}

pub fn main(world: World) -> Void raises {{
    var buf: [10]u8 = [0; 10]
    check world.out.write(fmt_u32(buf, factorial({n})))
    check world.out.write("\\n")
}}
"""


def b_fib_nth(n: int) -> str:
    return common.FMT_U32 + f"""
fn fib(n: u32) -> u32 {{
    var i: u32 = 0
    var a: u32 = 0
    var b: u32 = 1
    while i < n {{
        let nx: u32 = a + b
        a = b
        b = nx
        i = i + 1
    }}
    return a
}}

pub fn main(world: World) -> Void raises {{
    var buf: [10]u8 = [0; 10]
    check world.out.write(fmt_u32(buf, fib({n})))
    check world.out.write("\\n")
}}
"""


def b_fib_seq(n: int) -> str:
    return common.FMT_U32 + f"""
pub fn main(world: World) -> Void raises {{
    var i: u32 = 0
    var a: u32 = 0
    var b: u32 = 1
    while i < {n} {{
        if i > 0 {{
            check world.out.write(" ")
        }}
        var buf: [10]u8 = [0; 10]
        check world.out.write(fmt_u32(buf, a))
        let nx: u32 = a + b
        a = b
        b = nx
        i = i + 1
    }}
    check world.out.write("\\n")
}}
"""


def b_gcd(a: int, b: int) -> str:
    return common.FMT_U32 + f"""
fn gcd(a: u32, b: u32) -> u32 {{
    var x: u32 = a
    var y: u32 = b
    while y > 0 {{
        let t: u32 = x % y
        x = y
        y = t
    }}
    return x
}}

pub fn main(world: World) -> Void raises {{
    var buf: [10]u8 = [0; 10]
    check world.out.write(fmt_u32(buf, gcd({a}, {b})))
    check world.out.write("\\n")
}}
"""


def b_sum_to(n: int) -> str:
    return common.FMT_U32 + f"""
pub fn main(world: World) -> Void raises {{
    var i: u32 = 0
    var total: u32 = 0
    while i <= {n} {{
        total = total + i
        i = i + 1
    }}
    var buf: [10]u8 = [0; 10]
    check world.out.write(fmt_u32(buf, total))
    check world.out.write("\\n")
}}
"""


def b_power(base: int, exp: int) -> str:
    return common.FMT_U32 + f"""
pub fn main(world: World) -> Void raises {{
    var i: u32 = 0
    var acc: u32 = 1
    while i < {exp} {{
        acc = acc * {base}
        i = i + 1
    }}
    var buf: [10]u8 = [0; 10]
    check world.out.write(fmt_u32(buf, acc))
    check world.out.write("\\n")
}}
"""


def b_is_prime(n: int) -> str:
    return f"""
fn is_prime(n: u32) -> Bool {{
    if n < 2 {{
        return false
    }}
    var d: u32 = 2
    while d * d <= n {{
        if n % d == 0 {{
            return false
        }}
        d = d + 1
    }}
    return true
}}

pub fn main(world: World) -> Void raises {{
    if is_prime({n}) {{
        check world.out.write("prime\\n")
    }} else {{
        check world.out.write("not prime\\n")
    }}
}}
"""


def b_count_down(n: int) -> str:
    return common.FMT_U32 + f"""
pub fn main(world: World) -> Void raises {{
    var i: u32 = {n}
    while i > 0 {{
        var buf: [10]u8 = [0; 10]
        check world.out.write(fmt_u32(buf, i))
        check world.out.write("\\n")
        i = i - 1
    }}
}}
"""


def b_mult_row(k: int) -> str:
    return common.FMT_U32 + f"""
pub fn main(world: World) -> Void raises {{
    var i: u32 = 1
    while i <= 10 {{
        if i > 1 {{
            check world.out.write(" ")
        }}
        var buf: [10]u8 = [0; 10]
        check world.out.write(fmt_u32(buf, {k} * i))
        i = i + 1
    }}
    check world.out.write("\\n")
}}
"""


def b_digit_sum(n: int) -> str:
    return common.FMT_U32 + f"""
pub fn main(world: World) -> Void raises {{
    var n: u32 = {n}
    var total: u32 = 0
    while n > 0 {{
        total = total + (n % 10)
        n = n / 10
    }}
    var buf: [10]u8 = [0; 10]
    check world.out.write(fmt_u32(buf, total))
    check world.out.write("\\n")
}}
"""


def b_collatz(n: int) -> str:
    return common.FMT_U32 + f"""
pub fn main(world: World) -> Void raises {{
    var n: u32 = {n}
    var steps: u32 = 0
    while n != 1 {{
        if n % 2 == 0 {{
            n = n / 2
        }} else {{
            n = 3 * n + 1
        }}
        steps = steps + 1
    }}
    var buf: [10]u8 = [0; 10]
    check world.out.write(fmt_u32(buf, steps))
    check world.out.write("\\n")
}}
"""


def b_fizzbuzz(n: int) -> str:
    return common.FMT_U32 + f"""
pub fn main(world: World) -> Void raises {{
    var i: u32 = 1
    while i <= {n} {{
        if i % 15 == 0 {{
            check world.out.write("FizzBuzz")
        }} else if i % 3 == 0 {{
            check world.out.write("Fizz")
        }} else if i % 5 == 0 {{
            check world.out.write("Buzz")
        }} else {{
            var buf: [10]u8 = [0; 10]
            check world.out.write(fmt_u32(buf, i))
        }}
        check world.out.write("\\n")
        i = i + 1
    }}
}}
"""


def b_triangle(n: int) -> str:
    return f"""
pub fn main(world: World) -> Void raises {{
    var row: u32 = 1
    while row <= {n} {{
        var c: u32 = 0
        while c < row {{
            check world.out.write("*")
            c = c + 1
        }}
        check world.out.write("\\n")
        row = row + 1
    }}
}}
"""


def b_even_count(n: int) -> str:
    return common.FMT_U32 + f"""
pub fn main(world: World) -> Void raises {{
    var i: u32 = 1
    var evens: u32 = 0
    while i <= {n} {{
        if i % 2 == 0 {{
            evens = evens + 1
        }}
        i = i + 1
    }}
    var buf: [10]u8 = [0; 10]
    check world.out.write(fmt_u32(buf, evens))
    check world.out.write("\\n")
}}
"""


def b_isqrt(n: int) -> str:
    return common.FMT_U32 + f"""
fn isqrt(n: u32) -> u32 {{
    var r: u32 = 0
    while (r + 1) * (r + 1) <= n {{
        r = r + 1
    }}
    return r
}}

pub fn main(world: World) -> Void raises {{
    var buf: [10]u8 = [0; 10]
    check world.out.write(fmt_u32(buf, isqrt({n})))
    check world.out.write("\\n")
}}
"""


def b_to_binary(n: int) -> str:
    return f"""
pub fn main(world: World) -> Void raises {{
    var n: u32 = {n}
    if n == 0 {{
        check world.out.write("0\\n")
        return
    }}
    var tmp: [32]u8 = [0; 32]
    var cnt: usize = 0
    while n > 0 {{
        tmp[cnt] = 48 + ((n % 2) as u8)
        n = n / 2
        cnt = cnt + 1
    }}
    var out: [32]u8 = [0; 32]
    var w: usize = 0
    while w < cnt {{
        out[w] = tmp[cnt - 1 - w]
        w = w + 1
    }}
    check world.out.write(out[0..cnt])
    check world.out.write("\\n")
}}
"""


def b_popcount(n: int) -> str:
    return common.FMT_U32 + f"""
pub fn main(world: World) -> Void raises {{
    var n: u32 = {n}
    var c: u32 = 0
    while n > 0 {{
        c = c + (n % 2)
        n = n / 2
    }}
    var buf: [10]u8 = [0; 10]
    check world.out.write(fmt_u32(buf, c))
    check world.out.write("\\n")
}}
"""


def b_lcm(a: int, b: int) -> str:
    return common.FMT_U32 + f"""
fn gcd(a: u32, b: u32) -> u32 {{
    var x: u32 = a
    var y: u32 = b
    while y > 0 {{
        let t: u32 = x % y
        x = y
        y = t
    }}
    return x
}}

pub fn main(world: World) -> Void raises {{
    let g: u32 = gcd({a}, {b})
    let l: u32 = {a} / g * {b}
    var buf: [10]u8 = [0; 10]
    check world.out.write(fmt_u32(buf, l))
    check world.out.write("\\n")
}}
"""


def b_triangle_num(n: int) -> str:
    return common.FMT_U32 + f"""
pub fn main(world: World) -> Void raises {{
    let n: u32 = {n}
    let t: u32 = n * (n + 1) / 2
    var buf: [10]u8 = [0; 10]
    check world.out.write(fmt_u32(buf, t))
    check world.out.write("\\n")
}}
"""


def b_celsius_to_f(c: int) -> str:
    return common.FMT_U32 + f"""
pub fn main(world: World) -> Void raises {{
    let c: u32 = {c}
    let f: u32 = c * 9 / 5 + 32
    var buf: [10]u8 = [0; 10]
    check world.out.write(fmt_u32(buf, f))
    check world.out.write("\\n")
}}
"""


def b_hex(n: int) -> str:
    return f"""
fn hex_digit(v: u32) -> u8 {{
    if v < 10 {{
        return 48 + (v as u8)
    }}
    return 97 + ((v - 10) as u8)
}}

pub fn main(world: World) -> Void raises {{
    var n: u32 = {n}
    if n == 0 {{
        check world.out.write("0\\n")
        return
    }}
    var tmp: [16]u8 = [0; 16]
    var cnt: usize = 0
    while n > 0 {{
        tmp[cnt] = hex_digit(n % 16)
        n = n / 16
        cnt = cnt + 1
    }}
    var out: [16]u8 = [0; 16]
    var w: usize = 0
    while w < cnt {{
        out[w] = tmp[cnt - 1 - w]
        w = w + 1
    }}
    check world.out.write(out[0..cnt])
    check world.out.write("\\n")
}}
"""


def b_caesar(text: str, shift: int) -> str:
    return f"""
pub fn main(world: World) -> Void raises {{
    let s: Span<u8> = std.mem.span("{text}")
    let n: usize = std.mem.len(s)
    var out: [256]u8 = [0; 256]
    var i: usize = 0
    while i < n && i < 256 {{
        let c: u8 = s[i]
        if c >= 97 && c <= 122 {{
            out[i] = 97 + ((c - 97 + {shift}) % 26)
        }} else if c >= 65 && c <= 90 {{
            out[i] = 65 + ((c - 65 + {shift}) % 26)
        }} else {{
            out[i] = c
        }}
        i = i + 1
    }}
    check world.out.write(out[0..n])
    check world.out.write("\\n")
}}
"""


def b_reverse_str(text: str) -> str:
    return f"""
pub fn main(world: World) -> Void raises {{
    let s: Span<u8> = std.mem.span("{text}")
    let n: usize = std.mem.len(s)
    var out: [256]u8 = [0; 256]
    var i: usize = 0
    while i < n && i < 256 {{
        out[i] = s[n - 1 - i]
        i = i + 1
    }}
    check world.out.write(out[0..n])
    check world.out.write("\\n")
}}
"""


def b_count_vowels(text: str) -> str:
    return common.FMT_U32 + f"""
pub fn main(world: World) -> Void raises {{
    let s: Span<u8> = std.mem.span("{text}")
    let n: usize = std.mem.len(s)
    var i: usize = 0
    var v: u32 = 0
    while i < n {{
        let c: u8 = s[i]
        if c == 97 || c == 101 || c == 105 || c == 111 || c == 117 {{
            v = v + 1
        }}
        i = i + 1
    }}
    var buf: [10]u8 = [0; 10]
    check world.out.write(fmt_u32(buf, v))
    check world.out.write("\\n")
}}
"""


def b_repeat_char(ch: str, n: int) -> str:
    return f"""
pub fn main(world: World) -> Void raises {{
    var i: u32 = 0
    while i < {n} {{
        check world.out.write("{ch}")
        i = i + 1
    }}
    check world.out.write("\\n")
}}
"""


# ---- task specs: (slug, title, difficulty, tags, prompt, source, extra_patterns) ----

def specs():
    out = []

    def add(slug, title, diff, tags, prompt, src, extra=None):
        out.append((slug, title, diff, tags, prompt, src, extra or []))

    for msg in ["hello, zero", "ready", "compiled and run", "RL ready"]:
        add(f"print-{msg.split(',')[0].replace(' ', '-')}", f"Print a fixed line", 1,
            ["stdout"], f'Write a single-file Zero program whose `main` prints exactly `{msg}` followed by a newline.',
            b_print(msg))

    for a, b, op, name in [(40, 2, "+", "add"), (100, 58, "-", "sub"), (6, 7, "*", "mul"),
                           (100, 7, "/", "div"), (100, 7, "%", "mod"), (12, 12, "+", "add"),
                           (255, 255, "+", "add"), (9, 9, "*", "mul")]:
        add(f"arith-{name}-{a}-{b}", f"Compute {a} {op} {b}", 1, ["arithmetic"],
            f"Write a Zero program that computes `{a} {op} {b}` (u32 arithmetic) and prints the result followed by a newline.",
            b_arith(a, b, op))

    for n in [5, 6, 7, 10]:
        add(f"factorial-{n}", f"Factorial of {n}", 2, ["algorithm", "loop"],
            f"Write a Zero program with a `factorial` function that prints {n}! followed by a newline.",
            b_factorial(n), [r"factorial"])

    for n in [10, 15, 20, 25]:
        add(f"fib-nth-{n}", f"{n}th Fibonacci number", 2, ["algorithm"],
            f"Write a Zero program that prints the {n}th Fibonacci number (with fib(0)=0, fib(1)=1) and a newline.",
            b_fib_nth(n), [r"fib"])

    for n in [8, 11, 13]:
        add(f"fib-seq-{n}", f"First {n} Fibonacci numbers", 2, ["algorithm", "sequence"],
            f"Write a Zero program that prints the first {n} Fibonacci numbers (starting 0 1 1 ...) space-separated on one line, ending with a newline.",
            b_fib_seq(n))

    for a, b in [(48, 36), (1071, 462), (17, 5), (100, 75)]:
        add(f"gcd-{a}-{b}", f"GCD of {a} and {b}", 2, ["algorithm"],
            f"Write a Zero program with a `gcd` function (Euclid's algorithm) that prints gcd({a}, {b}) and a newline.",
            b_gcd(a, b), [r"gcd"])

    for n in [10, 50, 100, 7]:
        add(f"sum-to-{n}", f"Sum 0..{n}", 1, ["loop"],
            f"Write a Zero program that prints the sum of all integers from 0 to {n} inclusive, followed by a newline.",
            b_sum_to(n))

    for base, exp in [(2, 10), (3, 4), (5, 3), (7, 2)]:
        add(f"power-{base}-{exp}", f"{base}^{exp}", 2, ["loop", "arithmetic"],
            f"Write a Zero program that prints {base} raised to the power {exp} (integer exponentiation) and a newline.",
            b_power(base, exp))

    for n in [2, 17, 18, 97, 100]:
        add(f"is-prime-{n}", f"Primality of {n}", 2, ["algorithm", "branch"],
            f"Write a Zero program with an `is_prime` function that prints `prime` if {n} is prime, otherwise `not prime`, followed by a newline.",
            b_is_prime(n), [r"is_prime"])

    for n in [3, 5, 10]:
        add(f"count-down-{n}", f"Count down from {n}", 1, ["loop"],
            f"Write a Zero program that prints the integers from {n} down to 1, one per line.",
            b_count_down(n))

    for k in [3, 7, 9]:
        add(f"mult-row-{k}", f"Multiplication row for {k}", 2, ["loop"],
            f"Write a Zero program that prints the multiplication table row for {k}: {k}*1 through {k}*10, space-separated, ending with a newline.",
            b_mult_row(k))

    for n in [12345, 9999, 808]:
        add(f"digit-sum-{n}", f"Digit sum of {n}", 2, ["loop"],
            f"Write a Zero program that prints the sum of the decimal digits of {n}, followed by a newline.",
            b_digit_sum(n))

    for n in [6, 27, 7]:
        add(f"collatz-{n}", f"Collatz steps for {n}", 3, ["algorithm", "loop"],
            f"Write a Zero program that prints how many Collatz steps it takes to reach 1 starting from {n}, followed by a newline.",
            b_collatz(n))

    for n in [15, 20]:
        add(f"fizzbuzz-{n}", f"FizzBuzz to {n}", 3, ["branch", "loop"],
            f"Write a Zero program that prints FizzBuzz for 1..{n}: `Fizz` for multiples of 3, `Buzz` for multiples of 5, `FizzBuzz` for multiples of 15, otherwise the number. One entry per line.",
            b_fizzbuzz(n))

    for n in [3, 5]:
        add(f"triangle-{n}", f"Star triangle of height {n}", 1, ["loop"],
            f"Write a Zero program that prints a left-aligned triangle of `*` of height {n} (row i has i stars), one row per line.",
            b_triangle(n))

    for n in [10, 20]:
        add(f"even-count-{n}", f"Count evens up to {n}", 1, ["loop", "branch"],
            f"Write a Zero program that prints how many even numbers are in the range 1..{n} inclusive, followed by a newline.",
            b_even_count(n))

    for n in [2, 17, 99, 144]:
        add(f"isqrt-{n}", f"Integer sqrt of {n}", 2, ["algorithm", "loop"],
            f"Write a Zero program that prints the integer floor square root of {n} (largest r with r*r <= {n}), followed by a newline.",
            b_isqrt(n))

    for n in [5, 16, 255]:
        add(f"to-binary-{n}", f"{n} in binary", 2, ["loop"],
            f"Write a Zero program that prints {n} in base-2 (binary, no leading zeros), followed by a newline.",
            b_to_binary(n))

    for n in [7, 8, 255]:
        add(f"popcount-{n}", f"Set bits in {n}", 2, ["loop"],
            f"Write a Zero program that prints how many 1-bits are in the binary representation of {n}, followed by a newline.",
            b_popcount(n))

    for a, b in [(4, 6), (12, 18), (21, 6)]:
        add(f"lcm-{a}-{b}", f"LCM of {a} and {b}", 2, ["algorithm"],
            f"Write a Zero program that prints the least common multiple of {a} and {b}, followed by a newline.",
            b_lcm(a, b))

    for n in [5, 10, 100]:
        add(f"triangle-num-{n}", f"Triangular number T({n})", 1, ["arithmetic"],
            f"Write a Zero program that prints the {n}th triangular number (0+1+...+{n}), followed by a newline.",
            b_triangle_num(n))

    for c in [0, 37, 100]:
        add(f"c2f-{c}", f"{c}C to Fahrenheit", 1, ["arithmetic"],
            f"Write a Zero program that converts {c} degrees Celsius to Fahrenheit using F = C*9/5 + 32 (integer math) and prints the result with a newline.",
            b_celsius_to_f(c))

    for n in [255, 16, 4095]:
        add(f"hex-{n}", f"{n} in hex", 2, ["loop"],
            f"Write a Zero program that prints {n} in lowercase hexadecimal (no leading zeros), followed by a newline.",
            b_hex(n))

    for text, sh in [("abc", 3), ("xyz", 3), ("Hello", 1)]:
        add(f"caesar-{text}-{sh}", f"Caesar shift {text} by {sh}", 2, ["string", "loop"],
            f"Write a Zero program that prints the text `{text}` with each ASCII letter Caesar-shifted forward by {sh} (wrapping within its case, non-letters unchanged), followed by a newline.",
            b_caesar(text, sh))

    for text in ["hello", "zero", "abcd"]:
        add(f"reverse-str-{text}", f"Reverse '{text}'", 1, ["string", "loop"],
            f"Write a Zero program that prints the characters of `{text}` in reverse order, followed by a newline.",
            b_reverse_str(text))

    for text in ["education", "rhythm", "aeiou"]:
        add(f"vowels-{text}", f"Vowels in '{text}'", 2, ["string", "loop"],
            f"Write a Zero program that prints how many lowercase vowels (a, e, i, o, u) are in `{text}`, followed by a newline.",
            b_count_vowels(text))

    for ch, n in [("*", 5), ("x", 3), ("=", 8)]:
        add(f"repeat-{ch}-{n}", f"Repeat '{ch}' {n} times", 1, ["loop"],
            f"Write a Zero program that prints the character `{ch}` exactly {n} times on one line, followed by a newline.",
            b_repeat_char(ch, n))

    return out


def main():
    rows = []
    failures = []
    for slug, title, diff, tags, prompt, src, extra in specs():
        ok, stdout, diag = common.run_fixture({"main.0": src})
        if not ok:
            failures.append((slug, diag))
            continue
        task_id = f"zero_native/{slug}"
        row = {
            "id": task_id,
            "title": title,
            "family": "zero_native",
            "split": common.split_for(task_id),
            "difficulty": diff,
            "tags": ["zero"] + tags,
            "prompt": prompt + "\n\nRespond with ONLY the Zero source for a single file `main.0`.",
            "starter_files": {},
            "expected": {
                "stdout": stdout,
                "source_patterns": [PAT_MAIN, PAT_WRITE] + extra,
                "forbidden_patterns": common.FORBIDDEN_DEFAULT,
            },
            "grader": {
                "type": "zero_compiler_runtime", "entry_file": "main.0",
                "timeout_sec": 60, "reward_version": "v1", "hidden": False,
                "check": True, "run": True, "stdout_exact": True, "patterns": True,
            },
            "environment": {"type": "local", "requires_network": False, "requires_gpu": False},
            "provenance": {
                "source": "generated", "source_path": "tools/generators/gen_zero_native.py",
                "license": "MIT", "zero_version": ZERO_VERSION,
            },
            "_fixture": {"main.0": src},  # reference solution; stripped before training
        }
        row["provenance"]["content_hash"] = common.content_hash(
            {k: row[k] for k in ("id", "prompt", "expected", "_fixture")}
        )
        rows.append(row)

    common.stratified_splits(rows)
    counts = common.split_and_write(rows, "zero_native", "cases")
    print(f"zero_native: {len(rows)} verified tasks, {len(failures)} failed; splits={counts}")
    for slug, diag in failures:
        print(f"  FAILED {slug}: {diag}")
    return rows


if __name__ == "__main__":
    main()
