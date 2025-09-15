"""
Simple braces/quotes/brackets checker for JS files.
Usage: run in repo root: python scripts/check_js_syntax.py app/static/js/MetalMask.js
It performs a basic check for balanced (), {}, [], and matching quotes.
Not a replacement for a proper JS parser/linter, but catches common mismatches.
"""
import sys

def check_file(path):
    pairs = {')':'(', '}':'{', ']':'['}
    opens = set(pairs.values())
    stack = []
    line_no = 0
    in_single = False
    in_double = False
    in_back = False
    escape = False
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line_no += 1
            for ch in line:
                if escape:
                    escape = False
                    continue
                if ch == '\\':
                    escape = True
                    continue
                if in_single:
                    if ch == "'":
                        in_single = False
                    continue
                if in_double:
                    if ch == '"':
                        in_double = False
                    continue
                if in_back:
                    if ch == '`':
                        in_back = False
                    continue
                if ch == "'":
                    in_single = True
                    continue
                if ch == '"':
                    in_double = True
                    continue
                if ch == '`':
                    in_back = True
                    continue
                if ch in opens:
                    stack.append((ch, line_no))
                    continue
                if ch in pairs:
                    if not stack:
                        print(f"Unmatched closing {ch} at line {line_no}")
                        return False
                    last, lno = stack.pop()
                    if last != pairs[ch]:
                        print(f"Mismatched {last} opened at line {lno} vs closing {ch} at line {line_no}")
                        return False
    if in_single or in_double or in_back:
        print("Unclosed string literal at EOF")
        return False
    if stack:
        last, lno = stack[-1]
        print(f"Unclosed {last} opened at line {lno}")
        return False
    print("Braces and quotes appear balanced")
    return True

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python scripts/check_js_syntax.py path/to/file.js')
        sys.exit(2)
    ok = check_file(sys.argv[1])
    sys.exit(0 if ok else 1)
