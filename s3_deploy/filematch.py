
import re


def compile_re(pattern):
    """Create RE pattern from glob-style pattern."""

    match_pattern = r'''(?:
          (\*)        # asterisk
        | (\?)        # question
        | (.)         # other
    )'''

    if pattern[0] == '/':
        prefix = '^'
        pattern = pattern[1:]
    else:
        prefix = r'(?:/|^)'

    re_pattern = []
    for m in re.finditer(match_pattern, pattern, re.VERBOSE):
        asterisk, question, other = m.groups()
        if asterisk is not None:
            re_pattern.append(r'[^/]+')
        elif question is not None:
            re_pattern.append(r'[^/]')
        else:
            re_pattern.append(re.escape(other))

    return prefix + ''.join(re_pattern) + '$'


def match_key(pattern, key, regexp=False):
    """Match key to a glob (gitignore-style) or regexp pattern."""

    if pattern == '':
        raise ValueError('Empty pattern is invalid')

    if not regexp:
        pattern = compile_re(pattern)

    return bool(re.search(pattern, key))
