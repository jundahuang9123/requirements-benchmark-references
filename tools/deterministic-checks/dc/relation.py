"""Part C's relation of a need to an atom from the two NLI directions (fixed), Close and Exact, the separation rule
and Cohen's kappa. Standard library only."""
from statistics import median

CLOSE = ('equivalent', 'narrower', 'broader')


def relation(need_entails_atom, atom_entails_need):
    """need => atom and atom => need: equivalent; atom => need only: narrower; need => atom only: broader; else none."""
    a = need_entails_atom == 'entailment'
    b = atom_entails_need == 'entailment'
    if a and b:
        return 'equivalent'
    if b:
        return 'narrower'
    if a:
        return 'broader'
    return 'none'


def run_figures(relations, need_ids, atom_ids):
    """relations: {(atom_id, need_id): relation}. Close and Exact of a run over the given atoms."""
    needs = set(need_ids)
    close = exact = 0
    for a in atom_ids:
        rels = {relations.get((a, n), 'none') for n in needs}
        if 'equivalent' in rels:
            exact += 1
        if rels & set(CLOSE):
            close += 1
    return close, exact


def summary(values):
    vals = sorted(values)
    return {'median': median(vals) if vals else None, 'min': vals[0] if vals else None, 'max': vals[-1] if vals else None, 'runs': vals}


def separation(a_vals, b_vals):
    """The ranges of two conditions over their runs: 'a>b' or 'b>a' when they do not overlap, else 'overlap'."""
    if not a_vals or not b_vals:
        return None
    if min(a_vals) > max(b_vals):
        return 'a>b'
    if min(b_vals) > max(a_vals):
        return 'b>a'
    return 'overlap'


def kappa(pairs):
    """Cohen's kappa of a list of (label_1, label_2) pairs; None when undefined."""
    n = len(pairs)
    if n == 0:
        return None
    labels = sorted({x for p in pairs for x in p})
    po = sum(1 for a, b in pairs if a == b) / n
    pe = 0.0
    for l in labels:
        pe += (sum(1 for a, _ in pairs if a == l) / n) * (sum(1 for _, b in pairs if b == l) / n)
    if pe == 1.0:
        return None
    return (po - pe) / (1 - pe)
