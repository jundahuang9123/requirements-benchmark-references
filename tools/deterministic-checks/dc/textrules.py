"""The fixed text rules of Part A (T1, T2, T3) and Part B (T1). Standard library only.

Tokens: NFKC-normalised, lower-cased runs of letters and digits (so "DCAT-AP" is the two tokens "dcat", "ap").
Content words: tokens that are neither stop words nor template words (the actor and verb slots of the atoms' standard
form: "users can know ...", "the profile provides ...") nor pure numbers (numbers are test T2's).
Crude stemming: a fixed suffix strip (ies->y, sses->ss, es after s/x/z/sh/ch, s, ing, ed, ly); no dictionary.
A statement word is "found in the context" when its stem is among the context's stems, or when the word itself
(4 letters or more) occurs inside the context with every non-alphanumeric character removed (so "metadata" is found in
"meta-data" and "meta data"). Nothing else is matched.
"""
import re
import unicodedata

STOP_WORDS = frozenset("""
a an the and or but nor not no of in on at to from by with within without for as if then than that this these those
there here it its is are was were be been being have has had do does did will would shall should may might must can
could which who whom whose what when where whether while also any all each every either neither both such same other
another only own so too very just about above below between into through during before after over under again
further once more most some few many much how why am i you he she we they them their theirs our ours your yours his
her hers me my mine us up down out off per via etc e g i.e ie eg one ones
""".split())

TEMPLATE_WORDS = frozenset("users user profile can know find judge do".split())

_TOKEN = re.compile(r'[a-z0-9]+')
_NUMBER = re.compile(r'(?<![a-z0-9.])\d+(?:[.,]\d+)*(?![a-z0-9])')


def normalise(text):
    """NFKC, straight quotes and hyphens, soft hyphens dropped, whitespace collapsed."""
    if text is None:
        return ''
    s = unicodedata.normalize('NFKC', text)
    s = (s.replace('’', "'").replace('‘', "'").replace('“', '"').replace('”', '"')
          .replace('–', '-').replace('—', '-').replace('‑', '-').replace('­', '').replace(' ', ' '))
    return re.sub(r'\s+', ' ', s).strip()


def tokens(text):
    return _TOKEN.findall(normalise(text).lower())


def stem(w):
    if len(w) > 4 and w.endswith('ies'):
        w = w[:-3] + 'y'
    elif w.endswith('sses'):
        w = w[:-2]
    elif len(w) > 4 and w.endswith('es') and (w[-3] in 'sxz' or w[-4:-2] in ('sh', 'ch')):
        w = w[:-2]
    elif len(w) > 3 and w.endswith('s') and not w.endswith('ss'):
        w = w[:-1]
    if len(w) > 5 and w.endswith('ing'):
        w = w[:-3]
    elif len(w) > 4 and w.endswith('ed'):
        w = w[:-2]
    elif len(w) > 4 and w.endswith('ly'):
        w = w[:-2]
    return w


def content_words(text):
    """The content words of a text, in order, without repeats: (word, stem) pairs."""
    seen, out = set(), []
    for t in tokens(text):
        if t in STOP_WORDS or t in TEMPLATE_WORDS or t.isdigit() or len(t) < 2:
            continue
        s = stem(t)
        if s not in seen:
            seen.add(s)
            out.append((t, s))
    return out


def squash(text):
    return re.sub(r'[^a-z0-9]+', '', normalise(text).lower())


def missing_words(statement, context):
    """T1's core: the content words of the statement not found in the context."""
    ctx_stems = {stem(t) for t in tokens(context)}
    ctx_squashed = squash(context)
    return [w for w, s in content_words(statement) if s not in ctx_stems and not (len(w) >= 4 and w in ctx_squashed)]


def t1(statement, context):
    """Flag when two or more content words are missing and at least half of them."""
    words = content_words(statement)
    missing = missing_words(statement, context)
    flag = len(missing) >= 2 and 2 * len(missing) >= len(words)
    return {'flag': flag, 'content_words': len(words), 'missing': missing}


def numbers(text):
    return _NUMBER.findall(normalise(text).lower())


def t2(statement, context):
    """Flag when any number of the statement is not in the context."""
    ctx = normalise(context).lower()
    ctx_sq = squash(context)
    miss = [n for n in numbers(statement) if n not in ctx and n.replace('.', '').replace(',', '') not in ctx_sq]
    return {'flag': bool(miss), 'numbers': numbers(statement), 'missing': miss}


def t3(before, after):
    """Flag when the standard-form rewording added two or more content words, or dropped two or more."""
    b = {s: w for w, s in content_words(before)}
    a = {s: w for w, s in content_words(after)}
    added = [a[s] for s in a if s not in b]
    dropped = [b[s] for s in b if s not in a]
    return {'flag': len(added) >= 2 or len(dropped) >= 2, 'added': added, 'dropped': dropped}
