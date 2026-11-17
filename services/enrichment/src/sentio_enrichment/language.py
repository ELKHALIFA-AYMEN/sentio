"""Language detection: French, English, or undetermined.

The detector is py3langid, a small naive Bayes classifier over byte n-grams (see the model
card, ml/language.md, for the choice, the evaluation and the limits). It is restricted to the
two languages of v1, so it answers "which of French and English is this?"; ``und`` is returned
when it cannot tell.
"""

from dataclasses import dataclass
from importlib.metadata import version
from typing import Protocol

from py3langid.langid import MODEL_FILE, LanguageIdentifier

from sentio_schemas import Language

SUPPORTED = (Language.FR, Language.EN)

MIN_CONFIDENCE = 0.70
"""Below this probability the detector does not commit to a language: the answer is ``und``.

Full sentences score above 0.99. One- or two-word messages ("ok", "Hello", "SIM") score between 0.5
and 0.7, where the guess is close to a coin toss.
"""


@dataclass(frozen=True, slots=True)
class LanguageGuess:
    language: Language
    confidence: float
    """Probability of ``language`` (0 to 1). Always 0 for ``und``: no language is claimed."""


UNDETERMINED = LanguageGuess(Language.UNDETERMINED, 0.0)


class LanguageDetector(Protocol):
    @property
    def version(self) -> str:
        """Name and version of the model, written in the enriched event's ``model_versions``."""
        ...

    def detect(self, text: str) -> LanguageGuess: ...


class LangidDetector:
    """French/English detector based on py3langid.

    Loading the model takes about half a second: build one detector when the service starts and
    reuse it. ``detect`` is deterministic (same text, same answer).
    """

    def __init__(self, min_confidence: float = MIN_CONFIDENCE) -> None:
        if not 0.5 <= min_confidence <= 1.0:
            # With two languages the best one always has a probability of at least 0.5.
            raise ValueError("min_confidence must be between 0.5 and 1")
        self._min_confidence = min_confidence
        # norm_probs=True turns the model's scores into probabilities that add up to 1
        # over the allowed languages.
        self._identifier = LanguageIdentifier.from_model_file(MODEL_FILE, norm_probs=True)
        self._identifier.set_languages([language.value for language in SUPPORTED])
        self._version = f"py3langid-{version('py3langid')}"

    @property
    def version(self) -> str:
        return self._version

    def detect(self, text: str) -> LanguageGuess:
        if not any(character.isalpha() for character in text):
            # Only digits, punctuation, symbols or emoji ("12,90 €", "???"): nothing to detect.
            return UNDETERMINED
        code, probability = self._identifier.classify(text)
        if probability < self._min_confidence:
            return UNDETERMINED
        return LanguageGuess(Language(code), float(probability))
