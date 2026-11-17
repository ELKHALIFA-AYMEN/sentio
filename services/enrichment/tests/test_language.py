"""Tests of the real language model (py3langid), on sentences written for these tests.

They are not taken from the simulator templates, so they also check that detection works on wording
the simulator never produces.
"""

import re

import pytest

from sentio_enrichment import LangidDetector, LanguageGuess
from sentio_enrichment.language import MIN_CONFIDENCE
from sentio_schemas import Language

FR = Language.FR
EN = Language.EN
UND = Language.UNDETERMINED

FRENCH = [
    "Bonjour, ma box ne capte plus rien depuis ce matin.",
    "Je voudrais savoir pourquoi ma facture a doublé ce mois-ci.",
    "Impossible d'appeler depuis hier soir, le réseau est saturé.",
    "Pouvez-vous me rappeler demain après-midi ?",
    "Je pars au Portugal la semaine prochaine, faut-il activer quelque chose ?",
    "J'ai été prélevé deux fois, remboursez-moi s'il vous plaît.",
    "Votre conseiller m'a raccroché au nez, c'est inadmissible.",
    "Merci pour votre réponse rapide, tout fonctionne maintenant.",
    "Je souhaite résilier mon abonnement à la fin du mois.",
    "La couverture est vraiment mauvaise dans mon quartier.",
    "Mon code PUK est demandé, je ne le trouve nulle part.",
    "Toujours aucune nouvelle de ma demande de portabilité.",
    "Est-ce que l'offre est disponible pour les professionnels ?",
    "Mon téléphone affiche « aucun service » depuis la mise à jour.",
    "Je n'ai jamais reçu le colis avec ma nouvelle carte SIM.",
]

ENGLISH = [
    "Hi, my router has had no signal since this morning.",
    "Why is my bill twice as high as last month?",
    "I can't make any calls since last night, the network is down.",
    "Could you call me back tomorrow afternoon?",
    "I'm travelling to Portugal next week, do I need to turn anything on?",
    "I was charged twice, please refund me.",
    "Your agent hung up on me, this is unacceptable.",
    "Thanks for the quick answer, everything works now.",
    "I want to cancel my subscription at the end of the month.",
    "Coverage is really poor in my neighbourhood.",
    "My phone asks for a PUK code and I can't find it anywhere.",
    "Still no news about my number transfer request.",
    "Is this offer available for business customers?",
    "My phone shows 'no service' since the update.",
    "I never received the parcel with my new SIM card.",
]

WITHOUT_LETTERS = ["", "   ", "???", "12,90 €", "0612", "!!! :( !!!", "👍", "...", "€19.99 / 29.99"]

TOO_SHORT_TO_TELL = ["ok", "SIM", "Quill 150 Go 5G"]
"""Brand names, abbreviations, single words used in both languages."""


@pytest.fixture(scope="module")
def detector() -> LangidDetector:
    return LangidDetector()


@pytest.mark.parametrize("text", FRENCH)
def test_french_sentences_are_detected(detector: LangidDetector, text: str) -> None:
    guess = detector.detect(text)

    assert guess.language is FR
    assert guess.confidence >= 0.9


@pytest.mark.parametrize("text", ENGLISH)
def test_english_sentences_are_detected(detector: LangidDetector, text: str) -> None:
    guess = detector.detect(text)

    assert guess.language is EN
    assert guess.confidence >= 0.9


@pytest.mark.parametrize("text", WITHOUT_LETTERS)
def test_text_without_letters_is_undetermined(detector: LangidDetector, text: str) -> None:
    assert detector.detect(text) == LanguageGuess(UND, 0.0)


@pytest.mark.parametrize("text", TOO_SHORT_TO_TELL)
def test_ambiguous_short_text_is_undetermined(detector: LangidDetector, text: str) -> None:
    assert detector.detect(text) == LanguageGuess(UND, 0.0)


@pytest.mark.parametrize(
    ("text", "language"),
    [
        ("Merci beaucoup !", FR),
        ("Thank you so much!", EN),
        ("Toujours rien.", FR),
        ("Still nothing.", EN),
        ("C'est scandaleux", FR),
        ("This is outrageous", EN),
    ],
)
def test_short_but_clear_messages_are_detected(
    detector: LangidDetector, text: str, language: Language
) -> None:
    assert detector.detect(text).language is language


@pytest.mark.parametrize(
    ("text", "language"),
    [
        # Customers mix in words of the other language; the sentence structure decides.
        ("Mon roaming ne marche pas en Espagne", FR),
        ("My forfait is way too expensive now", EN),
        ("J'ai plus de data, c'est normal ?", FR),
    ],
)
def test_borrowed_words_do_not_fool_the_detector(
    detector: LangidDetector, text: str, language: Language
) -> None:
    assert detector.detect(text).language is language


def test_a_long_message_is_detected(detector: LangidDetector) -> None:
    text = " ".join(FRENCH) * 20  # about 20,000 characters

    assert detector.detect(text).language is FR


def test_confidence_is_a_probability_above_the_threshold(detector: LangidDetector) -> None:
    for text in FRENCH + ENGLISH + ["Merci", "Hello", "ok merci"]:
        guess = detector.detect(text)
        assert isinstance(guess.confidence, float)
        if guess.language is UND:
            assert guess.confidence == 0.0
        else:
            assert MIN_CONFIDENCE <= guess.confidence <= 1.0


def test_same_text_gives_the_same_answer(detector: LangidDetector) -> None:
    text = "Le réseau est coupé"

    assert {detector.detect(text) for _ in range(20)} == {detector.detect(text)}


def test_a_stricter_threshold_gives_und_more_often() -> None:
    lenient, strict = LangidDetector(min_confidence=0.5), LangidDetector(min_confidence=0.999)

    assert lenient.detect("Hello").language is EN
    assert strict.detect("Hello").language is UND


@pytest.mark.parametrize("value", [0.49, 1.01])
def test_threshold_must_be_between_one_half_and_one(value: float) -> None:
    with pytest.raises(ValueError, match=r"between 0\.5 and 1"):
        LangidDetector(min_confidence=value)


def test_version_names_the_library_and_its_version(detector: LangidDetector) -> None:
    assert re.fullmatch(r"py3langid-\d+\.\d+\.\d+", detector.version)
