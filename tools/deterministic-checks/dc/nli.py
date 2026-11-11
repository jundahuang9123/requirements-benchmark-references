"""One fixed NLI model, run deterministically on CPU.

Verdict = argmax over {entailment, neutral, contradiction}; no threshold. The premise is truncated first when a pair
exceeds 512 tokens (`truncation='only_first'`). torch.manual_seed(0), a fixed thread count, no autocast.
"""
import os

import numpy as np
import torch

from . import paths

LABELS = ('entailment', 'neutral', 'contradiction')
MAX_LEN = 512
THREADS = int(os.environ.get('DC_THREADS', '4'))


class NLI:
    def __init__(self, which='main', batch_size=32):
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
        name, rev = paths.NLI_MODELS[which]
        torch.manual_seed(0)
        torch.set_num_threads(THREADS)
        torch.use_deterministic_algorithms(True, warn_only=True)
        self.which, self.name, self.revision = which, name, rev
        self.tok = AutoTokenizer.from_pretrained(name, revision=rev)
        self.model = AutoModelForSequenceClassification.from_pretrained(name, revision=rev).eval()
        id2label = {int(k): v.lower() for k, v in self.model.config.id2label.items()}
        self.order = [next(i for i, l in id2label.items() if l.startswith(lab[:6])) for lab in LABELS]
        self.batch_size = batch_size

    def record(self):
        return {'model': self.name, 'revision': self.revision, 'max_length': MAX_LEN, 'truncation': 'only_first',
                'decision': 'argmax, no threshold', 'threads': THREADS, 'seed': 0, 'device': 'cpu'}

    @torch.no_grad()
    def probs(self, pairs):
        """pairs: list of (premise, hypothesis). Returns an array [n, 3] of probabilities in LABELS order."""
        out = np.zeros((len(pairs), 3), dtype=np.float64)
        # sort by length so that batches pad little; restore the order after
        idx = sorted(range(len(pairs)), key=lambda i: len(pairs[i][0]) + len(pairs[i][1]))
        for s in range(0, len(idx), self.batch_size):
            b = idx[s:s + self.batch_size]
            enc = self.tok([pairs[i][0] for i in b], [pairs[i][1] for i in b], padding=True, truncation='only_first',
                           max_length=MAX_LEN, return_tensors='pt')
            logits = self.model(**enc).logits.double()
            p = torch.softmax(logits, dim=-1)[:, self.order].cpu().numpy()
            out[b] = p
        return out

    def verdicts(self, pairs):
        """The argmax label per pair, with the probabilities rounded to 6 places (for the record, not for a threshold)."""
        p = self.probs(pairs)
        labs = [LABELS[int(i)] for i in p.argmax(axis=1)]
        return labs, np.round(p, 6).tolist()

    def truncated(self, pairs):
        """Which pairs exceed MAX_LEN tokens before truncation (so the premise was cut)."""
        enc = self.tok([a for a, _ in pairs], [b for _, b in pairs], truncation=False)
        return [len(ids) > MAX_LEN for ids in enc['input_ids']]
