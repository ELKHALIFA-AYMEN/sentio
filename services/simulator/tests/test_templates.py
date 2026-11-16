import re
from string import Formatter

import pytest

from sentio_schemas import Language, SentimentLabel, TopicLabel
from sentio_simulator import OPERATOR_NAME, templates

LANGUAGES = (Language.EN, Language.FR)
APOLOGY = re.compile(r"sorry|apolog|excuses", re.IGNORECASE)
THANKS_OR_WELCOME = re.compile(
    r"thank|glad|great|welcome|pleasure|delighted|lovely|"
    r"merci|plaisir|bienvenue|bonne nouvelle|heureux|excellente|belle",
    re.IGNORECASE,
)


def placeholders(text: str) -> set[str]:
    return {name for _, name, _, _ in Formatter().parse(text) if name is not None}


def agent_templates() -> list[str]:
    found: list[str] = []
    for by_language in templates.AGENT_REPLIES.values():
        for by_mood in by_language.values():
            for texts in by_mood.values():
                found.extend(texts)
    for by_mood in templates.CLOSINGS.values():
        for texts in by_mood.values():
            found.extend(texts)
    return found


def customer_templates() -> list[str]:
    found: list[str] = []
    for by_language in templates.OPENERS.values():
        for by_mood in by_language.values():
            for texts in by_mood.values():
                found.extend(texts)
    for by_mood in templates.FOLLOW_UPS.values():
        for texts in by_mood.values():
            found.extend(texts)
    return found


def all_templates() -> list[str]:
    return customer_templates() + agent_templates()


# --- Completeness: no missing combination ----------------------------------------


@pytest.mark.parametrize("topic", list(TopicLabel))
@pytest.mark.parametrize("language", LANGUAGES)
@pytest.mark.parametrize("mood", list(SentimentLabel))
def test_every_topic_language_and_mood_has_openers_and_agent_replies(
    topic: TopicLabel, language: Language, mood: SentimentLabel
) -> None:
    assert templates.OPENERS[topic][language][mood]
    assert templates.AGENT_REPLIES[topic][language][mood]


@pytest.mark.parametrize("language", LANGUAGES)
@pytest.mark.parametrize("mood", list(SentimentLabel))
def test_every_language_and_mood_has_follow_ups_and_closings(
    language: Language, mood: SentimentLabel
) -> None:
    assert templates.FOLLOW_UPS[language][mood]
    assert templates.CLOSINGS[language][mood]


# --- Placeholders -----------------------------------------------------------------


def test_templates_only_use_known_placeholders() -> None:
    for text in all_templates():
        assert placeholders(text) <= templates.SLOTS, text


def test_agents_only_mention_details_they_know() -> None:
    for text in agent_templates():
        assert placeholders(text) <= templates.AGENT_SLOTS, text


def test_agents_mention_a_city_only_when_the_customer_gave_one() -> None:
    for topic, by_language in templates.AGENT_REPLIES.items():
        for language, by_mood in by_language.items():
            for mood, replies in by_mood.items():
                if any("city" in placeholders(reply) for reply in replies):
                    openers = templates.OPENERS[topic][language][mood]
                    assert all("city" in placeholders(opener) for opener in openers), (
                        topic,
                        language,
                        mood,
                    )
    for by_mood in templates.CLOSINGS.values():
        for closings in by_mood.values():
            assert all("city" not in placeholders(text) for text in closings)


# --- Tone: the agent adapts to the customer's mood ------------------------------------


def test_agent_apologises_to_unhappy_customers() -> None:
    for by_language in templates.AGENT_REPLIES.values():
        for language in LANGUAGES:
            for reply in by_language[language][SentimentLabel.NEGATIVE]:
                assert APOLOGY.search(reply), reply


def test_agent_thanks_happy_customers_and_does_not_apologise() -> None:
    positive_texts = [
        text
        for by_language in templates.AGENT_REPLIES.values()
        for language in LANGUAGES
        for text in by_language[language][SentimentLabel.POSITIVE]
    ] + [
        text
        for language in LANGUAGES
        for text in templates.CLOSINGS[language][SentimentLabel.POSITIVE]
    ]
    for text in positive_texts:
        assert THANKS_OR_WELCOME.search(text), text
        assert not APOLOGY.search(text), text


def test_agent_never_apologises_to_neutral_customers() -> None:
    for by_language in templates.AGENT_REPLIES.values():
        for language in LANGUAGES:
            for reply in by_language[language][SentimentLabel.NEUTRAL]:
                assert not APOLOGY.search(reply), reply


def test_closing_for_unhappy_customers_promises_follow_up() -> None:
    for language in LANGUAGES:
        for text in templates.CLOSINGS[language][SentimentLabel.NEGATIVE]:
            assert re.search(r"escalat|priorit", text, re.IGNORECASE), text


# --- Writing quality ------------------------------------------------------------------


def test_french_templates_avoid_gendered_adjectives() -> None:
    gendered = re.compile(
        r"\b(content|contente|déçu|déçue|désolé|désolée|ravi|ravie|ravis|satisfait|satisfaite)\b",
        re.IGNORECASE,
    )
    french = [
        text
        for text in all_templates()
        if re.search(r"\b(je|vous|votre|merci|bonjour)\b", text, re.IGNORECASE)
    ]
    assert french
    for text in french:
        assert not gendered.search(text), text


def test_templates_have_no_duplicates() -> None:
    texts = all_templates()

    assert len(texts) == len(set(texts))


def test_operator_name_is_the_invented_one() -> None:
    assert OPERATOR_NAME == "Quillnet Mobile"
