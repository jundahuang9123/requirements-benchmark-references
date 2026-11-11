"""Unit tests of Part C's relation mapping, run figures, separation rule and kappa on invented data."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dc import relation as R  # noqa: E402


def test_relation_mapping():
    assert R.relation('entailment', 'entailment') == 'equivalent'
    assert R.relation('neutral', 'entailment') == 'narrower'       # atom => need only: the need says less
    assert R.relation('entailment', 'neutral') == 'broader'        # need => atom only: the need says more
    assert R.relation('neutral', 'neutral') == 'none'
    assert R.relation('contradiction', 'contradiction') == 'none'
    assert R.relation('entailment', 'contradiction') == 'broader'


def test_run_figures():
    rels = {('A1', 'n1'): 'equivalent', ('A2', 'n2'): 'narrower', ('A3', 'n3'): 'broader', ('A4', 'n4'): 'none', ('A1', 'n5'): 'narrower'}
    assert R.run_figures(rels, ['n1', 'n2', 'n3', 'n4'], ['A1', 'A2', 'A3', 'A4', 'A5']) == (3, 1)
    assert R.run_figures(rels, ['n5'], ['A1', 'A2']) == (1, 0)
    assert R.run_figures(rels, [], ['A1']) == (0, 0)


def test_separation():
    assert R.separation([5, 6, 7], [1, 2, 4]) == 'a>b'
    assert R.separation([1, 2, 4], [5, 6, 7]) == 'b>a'
    assert R.separation([1, 5], [5, 9]) == 'overlap'
    assert R.separation([3], [3]) == 'overlap'
    assert R.separation([], [1]) is None


def test_kappa():
    assert R.kappa([('a', 'a'), ('b', 'b'), ('a', 'a'), ('b', 'b')]) == 1.0
    assert abs(R.kappa([('a', 'a'), ('a', 'b'), ('b', 'a'), ('b', 'b')])) < 1e-12
    assert R.kappa([]) is None
    assert R.kappa([('a', 'a'), ('a', 'a')]) is None   # one label on both sides: undefined
    k = R.kappa([('a', 'a')] * 7 + [('b', 'b')] * 1 + [('a', 'b')] * 1 + [('b', 'a')] * 1)
    assert abs(k - 0.375) < 1e-9


def test_summary():
    s = R.summary([3, 1, 2])
    assert s == {'median': 2, 'min': 1, 'max': 3, 'runs': [1, 2, 3]}
