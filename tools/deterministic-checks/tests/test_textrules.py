"""Unit tests of the text rules on invented sentences (no atoms)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dc import textrules as T  # noqa: E402


def test_tokens_and_stems():
    assert T.tokens('Users can know the DCAT-AP release.') == ['users', 'can', 'know', 'the', 'dcat', 'ap', 'release']
    assert T.stem('datasets') == 'dataset'
    assert T.stem('categories') == 'category'
    assert T.stem('classes') == 'class'
    assert T.stem('addresses') == 'address'
    assert T.stem('described') == 'describ'
    assert T.stem('publishing') == 'publish'
    assert T.stem('access') == 'access'
    assert T.stem('is') == 'is'


def test_content_words_drop_stop_and_template_words():
    words = [w for w, _ in T.content_words('Users can know the licence of a dataset.')]
    assert words == ['licence', 'dataset']


def test_t1_flags_when_half_missing_and_two_or_more():
    ctx = 'The licence of each dataset is given in the catalogue.'
    assert not T.t1('Users can know the licence of a dataset.', ctx)['flag']
    r = T.t1('Users can know the publisher and the contact point of a dataset.', ctx)
    assert r['missing'] == ['publisher', 'contact', 'point'] and r['flag']
    # one word missing of four: not flagged (needs two or more)
    r = T.t1('Users can know the licence, dataset and catalogue entry.', ctx)
    assert r['missing'] == ['entry'] and not r['flag']
    # two missing of six: fewer than half, not flagged
    r = T.t1('Users can know the licence, dataset, catalogue, given, and the publisher name.', ctx)
    assert len(r['missing']) == 2 and r['content_words'] == 6 and not r['flag']


def test_t1_finds_words_inside_compounds():
    r = T.t1('Users can know the metadata record.', 'Each meta-data record is listed.')
    assert r['missing'] == []


def test_t2_numbers():
    assert T.t2('The profile keeps 12 mandatory properties.', 'twelve (12) properties are mandatory')['flag'] is False
    r = T.t2('The profile uses DCAT-AP 1.1 and ISO 19115.', 'The profile uses DCAT-AP 1.1.')
    assert r['missing'] == ['19115'] and r['flag']
    assert T.t2('No numbers here.', '')['numbers'] == []


def test_t3_added_and_dropped():
    r = T.t3('Provide a contact point for each dataset.', 'The profile provides a contact point for each dataset.')
    assert r['added'] == [] and r['dropped'] == [] and not r['flag']
    r = T.t3('Provide a contact point.', 'The profile provides a contact point, a licence and a publisher.')
    assert r['added'] == ['licence', 'publisher'] and r['flag']
    r = T.t3('Provide a contact point, a licence and a publisher.', 'The profile provides a contact point.')
    assert r['dropped'] == ['licence', 'publisher'] and r['flag']
    r = T.t3('Provide a licence.', 'The profile provides a licence statement.')
    assert r['added'] == ['statement'] and not r['flag']


def test_normalise():
    assert T.normalise('meta­data  “quoted”\n– x') == 'metadata "quoted" - x'
