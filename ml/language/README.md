# Model card: language detection

| | |
|---|---|
| **Used by** | enrichment service ([`language.py`](../../services/enrichment/src/sentio_enrichment/language.py)) |
| **Version in events** | `model_versions.language = "py3langid-0.4.0"` |
| **Output** | `language` (`fr`, `en` or `und`) and `language_confidence` (0 to 1), for every message (customer and agent) |
| **Type** | Off-the-shelf model, not trained by us |

## Model

[py3langid](https://github.com/adbar/py3langid) 0.4.0, a maintained, faster version of
[langid.py](https://github.com/saffsd/langid.py) (Lui & Baldwin, 2012). It is a **naive Bayes classifier over byte
n-grams** (short sequences of characters such as `eau`, ` th`, `ç`), trained by its authors on 97 languages.

- **Licence:** BSD-3-Clause. The model file ships inside the package (4.5 MB); no download at run time.
- **Training data:** chosen by the original authors (government documents, Wikipedia, news, web pages...). We do
  not train or fine-tune it, and it was never trained on Sentio data.
- **Restricted to French and English:** the model only compares these two languages, which are the languages of v1.

## How the output is computed

1. **No letter in the text** (`""`, `???`, `12,90 €`, emoji): `und`, confidence 0. There is nothing to detect.
2. Otherwise the model scores French and English, and the scores are turned into **probabilities that add up to 1**
   (`norm_probs=True`). With two languages, the best one always has a probability of at least 0.5.
3. **Probability below 0.70:** `und`, confidence 0. The model is not sure enough to commit (it happens on one- or
   two-word messages such as `Hello`, `Merci`, `Hi`, where it is close to a coin toss).
4. **Otherwise:** the most likely language, with its probability as `language_confidence`.

`language_confidence` is therefore the probability of the returned language, between 0.70 and 1, or 0 for `und`.
Naive Bayes probabilities are overconfident: full sentences almost always score above 0.99, so the value is useful
to spot short and ambiguous texts, not as a calibrated probability of being right.

## Evaluation

Reproduce with `uv run python ml/language/evaluate.py` (2026-11-17):

| Sample | Messages | Correct | Wrong | `und` |
|---|---|---|---|---|
| Simulator messages (533 distinct texts) | 2,000 | 2,000 (100 %) | 0 | 0 |
| Hand-written: full sentences | 40 | 40 (100 %) | 0 | 0 |
| Hand-written: short replies (1–3 words) | 30 | 23 (77 %) | 1 (3 %) | 6 (20 %) |
| Hand-written: French/English mixed in one sentence | 10 | 10 (100 %) | 0 | 0 |
| Hand-written: no letters (expected `und`) | 7 | 7 (100 %) | 0 | 0 |

- The **simulator** sample is easy: template sentences are long and clean. It mainly shows that the pipeline and
  the simulated traffic agree.
- The **hand-written** messages ([`eval_set.csv`](eval_set.csv)) were written for this evaluation, independently of
  the simulator templates. Not correct: `und` for `Merci`, `Je patiente`, `Salut`, `Hello`, `No signal`, `Hi`;
  wrong for `ok merci` (detected as English).

**Speed:** about 34,000 detections per second on one core (laptop); the model loads in 0.4–0.7 s.
In the service, with JSON parsing and serialisation, a message takes about 65 µs (15,000 messages/s per core),
far above the simulator's 5 messages/s.

### Alternatives compared

Same 500 simulator messages and hand-made short or mixed cases (2026-11-17):

| Library | Accuracy (simulator) | Detections/s | Installed size | Notes |
|---|---|---|---|---|
| **py3langid** (chosen) | 100 % | ~36,000 | 4.4 MB + numpy | Deterministic. Numpy is needed by scikit-learn anyway. |
| lingua (`lingua-language-detector` 2.2) | 100 % | ~10,000 | 291 MB | Very accurate on short texts in theory, but not better on ours (`Mon roaming ne marche pas` → English); would add about 300 MB to the image. |
| langdetect 1.0.9 | 97 % | ~570 | 2.4 MB | Random unless seeded; very wrong on short texts (`ok` → Slovak, `Merci` → Spanish). |

## Limits

- **Only French and English.** A message in another language (Spanish, German, Darija...) is labelled `fr` or `en`,
  sometimes with a high confidence (`Ich habe kein Netz` → `en`, 0.86). Darija support is planned after v1.
- **Very short messages** are often `und` (about 1 in 5 in our sample) and sometimes wrong.
- **Overconfident probabilities**, as explained above.
- The evaluation set is small (87 hand-written messages) and written by one person; the figures are indicative.
