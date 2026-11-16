# simulator

Generates synthetic customer support conversations (French and English) for **Quillnet Mobile**, an invented
European telecom operator, and (soon) publishes each message to the `conversations.raw` topic.

> **Status:** the conversation generator is implemented. Publishing to Redpanda comes next.

No real data is ever used: the texts come from hand-written templates, customer identifiers are random
`CUST-` numbers, and the operator, its plans and prices are made up.

## How a conversation is built

`generate_conversation(seed, started_at, config)` in [`generator.py`](src/sentio_simulator/generator.py):

1. **Draw the conversation's profile**: language (50 % French by default), topic (billing, network, plan,
   roaming, porting, other), the customer's mood (negative / neutral / positive, with odds that depend on the
   topic: network issues are more often negative than plan questions), and the channel (chat, e-mail, call).
2. **Draw the customer**: segment (prepaid / postpaid / business), one of the segment's plans
   ([`catalog.py`](src/sentio_simulator/catalog.py)), whose price becomes the monthly revenue, and a tenure.
3. **Pick the sentences** from [`templates.py`](src/sentio_simulator/templates.py):
   a customer opener (topic + language + mood), an agent reply (topic + language + mood), then, most of
   the time, a customer follow-up (language + mood) and an agent closing (language + mood).
   A conversation has 2 to 4 messages. The agent adapts to the customer's mood: apologies and an action for an
   unhappy customer, information for a neutral one, thanks for a happy one. Agents only mention details they
   know (the customer's plan and price, the city the customer complained about), and French sentences avoid
   gendered adjectives.
4. **Fill the placeholders** (`{plan}`, `{price}`, `{amount}`, `{city}`, `{country}`, `{days}`, `{operator}`),
   with amounts written the local way (`€29.99` / `29,99 €`).
5. **Add timestamps**: the first message is sent at `started_at`, each next one after a delay that depends on
   the channel (seconds in a chat or call, hours by e-mail).
6. **Build the events** as `RawMessageEvent` objects, so every message is checked against the contract.

The result also carries the **ground truth** (intended language, topic and mood). It is not part of the
published events, but it will be used to evaluate the enrichment models.

## Reproducibility

The generator is made of pure functions: all randomness comes from a `random.Random(seed)` created inside the
call, and the start time is an argument. The same seed, start time and configuration always give exactly the
same conversation (including its UUIDs), which makes tests and bug reports reproducible.

## Development

From the repository root:

```bash
uv run python -m pytest services/simulator
uv run python -m mypy services/simulator
```
