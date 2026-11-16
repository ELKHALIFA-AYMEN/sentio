"""Sentence templates used to build synthetic conversations.

Templates are written by hand, in English and French, for every topic and customer mood.
Placeholders between braces are filled by the generator; ``SLOTS`` lists the allowed ones.
No template contains a person's name, a phone number or an e-mail address, and French templates
avoid gendered adjectives (the customer and the agent can be anyone).

Agents adapt their tone to the customer's mood: apologies and an action for an unhappy customer,
information for a neutral one, thanks for a happy one.
"""

from sentio_schemas import Language, SentimentLabel, TopicLabel

SLOTS = frozenset({"operator", "plan", "price", "amount", "city", "country", "days"})

AGENT_SLOTS = frozenset({"operator", "plan", "price", "city"})
"""Details an agent may mention: the agent knows the customer's account (operator, plan, price)
and repeats the city the customer complained about. An agent never invents an amount, a country or
a number of days the customer did not give."""

EN = Language.EN
FR = Language.FR
NEG = SentimentLabel.NEGATIVE
NEU = SentimentLabel.NEUTRAL
POS = SentimentLabel.POSITIVE

Templates = tuple[str, ...]

# First customer message: depends on the topic, the language and the customer's mood.
OPENERS: dict[TopicLabel, dict[Language, dict[SentimentLabel, Templates]]] = {
    TopicLabel.BILLING: {
        EN: {
            NEG: (
                "I've been charged {amount} more than usual on my last bill and nobody told me why. "
                "This is the second time.",
                "My bill is wrong again. I pay {price} a month for {plan} and you took {amount} extra.",
            ),
            NEU: (
                "Hello, I don't understand a line of {amount} on my latest invoice. Can you explain it?",
                "Hi, can you tell me when my next payment for {plan} will be taken?",
            ),
            POS: (
                "Hi! I saw the {amount} refund on my bill, thank you for sorting it out so quickly.",
                "Hello, quick question about my invoice, otherwise everything is fine with {plan}.",
            ),
        },
        FR: {
            NEG: (
                "On m'a facturé {amount} de plus que d'habitude sur ma dernière facture, sans aucune "
                "explication. C'est la deuxième fois.",
                "Ma facture est encore fausse. Je paie {price} par mois pour {plan} et vous avez "
                "prélevé {amount} en plus.",
            ),
            NEU: (
                "Bonjour, je ne comprends pas une ligne de {amount} sur ma dernière facture. "
                "Pouvez-vous m'expliquer ?",
                "Bonjour, pouvez-vous me dire quand sera prélevé le prochain paiement de {plan} ?",
            ),
            POS: (
                "Bonjour ! J'ai vu le remboursement de {amount} sur ma facture, merci d'avoir réglé "
                "ça si vite.",
                "Bonjour, petite question sur ma facture, sinon tout va bien avec {plan}.",
            ),
        },
    },
    TopicLabel.NETWORK: {
        EN: {
            NEG: (
                "I've had no 4G at all in {city} for {days} days. I can't work like this.",
                "My calls have been dropping in {city} for {days} days. What is wrong with your network?",
            ),
            NEU: (
                "Hello, is there any maintenance planned on the network around {city}?",
                "Hi, my mobile data has been a bit slow in {city} today. Is it a known issue?",
            ),
            POS: (
                "Hi, just wanted to say the 5G in {city} is much better since last week, well done.",
                "Hello, the network issue in {city} seems fixed now, thanks for the update.",
            ),
        },
        FR: {
            NEG: (
                "Je n'ai plus du tout de 4G à {city} depuis {days} jours. Je ne peux pas travailler.",
                "Mes appels coupent sans arrêt à {city} depuis {days} jours. Que se passe-t-il avec "
                "votre réseau ?",
            ),
            NEU: (
                "Bonjour, une maintenance est-elle prévue sur le réseau autour de {city} ?",
                "Bonjour, mes données mobiles sont un peu lentes à {city} aujourd'hui. Est-ce un "
                "problème connu ?",
            ),
            POS: (
                "Bonjour, je voulais juste dire que la 5G à {city} est bien meilleure depuis la "
                "semaine dernière, bravo.",
                "Bonjour, le problème de réseau à {city} semble réglé, merci pour le suivi.",
            ),
        },
    },
    TopicLabel.ROAMING: {
        EN: {
            NEG: (
                "I'm {country} and my phone has no data at all, even though roaming is included "
                "in {plan}.",
                "I was charged {amount} in roaming fees for a short trip. This is outrageous.",
            ),
            NEU: (
                "Hello, I'm travelling {country} next week. Does {plan} include roaming there?",
                "Hi, how do I activate roaming before my trip? I'll be {country}.",
            ),
            POS: (
                "Hi, I'm {country} and everything works perfectly, roaming was really easy to use.",
                "Hello, thanks for the roaming tips, my phone worked fine during my whole trip.",
            ),
        },
        FR: {
            NEG: (
                "Je suis {country} et je n'ai aucune donnée mobile, alors que l'itinérance est "
                "incluse dans {plan}.",
                "On m'a facturé {amount} de frais d'itinérance pour un court séjour. C'est scandaleux.",
            ),
            NEU: (
                "Bonjour, je pars {country} la semaine prochaine. Est-ce que {plan} inclut "
                "l'itinérance là-bas ?",
                "Bonjour, comment activer l'itinérance avant mon voyage ? Je serai {country}.",
            ),
            POS: (
                "Bonjour, je suis {country} et tout fonctionne parfaitement, l'itinérance est "
                "vraiment simple.",
                "Bonjour, merci pour les conseils sur l'itinérance, mon téléphone a bien marché "
                "pendant tout le voyage.",
            ),
        },
    },
    TopicLabel.PLAN: {
        EN: {
            NEG: (
                "I've paid {price} a month for {plan} for years and new customers get a better "
                "deal. That's unfair.",
                "My data runs out every month with {plan}, and the upgrade you offer is far too "
                "expensive.",
            ),
            NEU: (
                "Hello, I'd like to compare {plan} with your other offers. What are my options?",
                "Hi, can I change my plan in the middle of the month?",
            ),
            POS: (
                "Hi, I just switched to {plan} and I'm very happy with it, thanks.",
                "Hello, {plan} is exactly what I needed, great value for {price}.",
            ),
        },
        FR: {
            NEG: (
                "Je paie {price} par mois pour {plan} depuis des années et les nouveaux clients ont "
                "une meilleure offre. C'est injuste.",
                "Je n'ai plus de données chaque mois avec {plan}, et l'option que vous proposez est "
                "beaucoup trop chère.",
            ),
            NEU: (
                "Bonjour, j'aimerais comparer {plan} avec vos autres offres. Quelles sont mes options ?",
                "Bonjour, est-ce que je peux changer de forfait en milieu de mois ?",
            ),
            POS: (
                "Bonjour, je viens de passer à {plan} et il me convient parfaitement, merci.",
                "Bonjour, {plan} correspond exactement à mes besoins, très bon rapport qualité-prix "
                "pour {price}.",
            ),
        },
    },
    TopicLabel.PORTING: {
        EN: {
            NEG: (
                "I want to take my number to another operator. Your service has been terrible "
                "lately.",
                "I asked to port my number out {days} days ago and it still isn't done. "
                "Stop blocking it.",
            ),
            NEU: (
                "Hello, what do I need to keep my number if I move to another operator?",
                "Hi, I'm thinking of changing operator. How long does number porting take?",
            ),
            POS: (
                "Hi, my number was transferred to {operator} without any problem, thank you.",
                "Hello, I just joined {operator} and kept my number, it went very smoothly.",
            ),
        },
        FR: {
            NEG: (
                "Je veux partir chez un autre opérateur avec mon numéro. Votre service est "
                "catastrophique ces derniers temps.",
                "J'ai demandé la portabilité de mon numéro il y a {days} jours et ce n'est toujours "
                "pas fait. Arrêtez de bloquer.",
            ),
            NEU: (
                "Bonjour, que dois-je faire pour garder mon numéro si je change d'opérateur ?",
                "Bonjour, je pense changer d'opérateur. Combien de temps prend la portabilité ?",
            ),
            POS: (
                "Bonjour, mon numéro a été transféré chez {operator} sans aucun souci, merci.",
                "Bonjour, je viens d'arriver chez {operator} en gardant mon numéro, tout s'est très "
                "bien passé.",
            ),
        },
    },
    TopicLabel.OTHER: {
        EN: {
            NEG: (
                "Your mobile app keeps logging me out and I can't access my account. Very annoying.",
                "I lost my SIM card {days} days ago and I'm still waiting for the new one.",
            ),
            NEU: (
                "Hello, how do I update my postal address in my account?",
                "Hi, can I get an eSIM instead of a physical SIM card?",
            ),
            POS: (
                "Hi, the new version of your app is really nice, well done.",
                "Hello, my new SIM card arrived quickly and works fine, thanks.",
            ),
        },
        FR: {
            NEG: (
                "Votre application me déconnecte sans arrêt et je n'arrive pas à accéder à mon "
                "compte. C'est très pénible.",
                "J'ai perdu ma carte SIM il y a {days} jours et j'attends toujours la nouvelle.",
            ),
            NEU: (
                "Bonjour, comment mettre à jour mon adresse postale dans mon compte ?",
                "Bonjour, est-ce que je peux avoir une eSIM à la place d'une carte SIM physique ?",
            ),
            POS: (
                "Bonjour, la nouvelle version de votre application est vraiment réussie, bravo.",
                "Bonjour, ma nouvelle carte SIM est arrivée vite et fonctionne bien, merci.",
            ),
        },
    },
}


# Agent's answer to the opener: depends on the topic, the language and the customer's mood.
AGENT_REPLIES: dict[TopicLabel, dict[Language, dict[SentimentLabel, Templates]]] = {
    TopicLabel.BILLING: {
        EN: {
            NEG: (
                "I'm sorry about this, it shouldn't have happened. I'm reviewing your last invoice now and I'll correct any error.",
                "My apologies for the trouble. I'm opening a billing claim so that anything charged by mistake is refunded.",
            ),
            NEU: (
                "Of course. I'm opening your account to go through your invoice and payment details with you.",
                "Sure, let me look at the billing history of your {plan} plan.",
            ),
            POS: (
                "Thank you for your kind message, that's nice to hear! Let me check your invoice so everything stays clear.",
                "Thanks a lot for the feedback, we're glad you're happy with {plan}.",
            ),
        },
        FR: {
            NEG: (
                "Toutes nos excuses, cela n'aurait pas dû arriver. Je vérifie votre dernière facture et je corrige toute erreur.",
                "Je vous présente nos excuses pour ce désagrément. J'ouvre une réclamation pour que tout montant prélevé par erreur vous soit remboursé.",
            ),
            NEU: (
                "Bien sûr. J'ouvre votre compte pour passer en revue votre facture et vos paiements avec vous.",
                "Bien sûr, je regarde l'historique de facturation de votre forfait {plan}.",
            ),
            POS: (
                "Merci pour votre gentil message, ça fait plaisir ! Je vérifie votre facture pour que tout reste clair.",
                "Merci beaucoup pour votre retour, nous sommes heureux que {plan} vous convienne.",
            ),
        },
    },
    TopicLabel.NETWORK: {
        EN: {
            NEG: (
                "I'm very sorry for the disruption. Our technical team is already working on an incident around {city}, and I'm flagging your line.",
                "My apologies for this. I've opened a priority ticket for the network in {city} and I'm checking your line now.",
            ),
            NEU: (
                "Thanks for asking. Maintenance is planned around {city} this week, which can slow mobile data down for a few hours.",
                "Let me check. I don't see any major incident in {city} right now, but I'm running a test on your line.",
            ),
            POS: (
                "Thank you for letting us know, I'll pass your feedback on to our network team!",
                "That's great to hear, thank you! Our teams recently upgraded several sites around {city}.",
            ),
        },
        FR: {
            NEG: (
                "Toutes nos excuses pour cette coupure. Notre équipe technique travaille déjà sur un incident autour de {city}, et je signale votre ligne.",
                "Je vous présente nos excuses. J'ouvre un ticket prioritaire pour le réseau à {city} et je vérifie votre ligne.",
            ),
            NEU: (
                "Merci pour votre question. Une maintenance est prévue autour de {city} cette semaine, elle peut ralentir les données mobiles quelques heures.",
                "Je regarde. Je ne vois pas d'incident majeur à {city} pour l'instant, mais je lance un test sur votre ligne.",
            ),
            POS: (
                "Merci de nous le faire savoir, je transmets votre retour à notre équipe réseau !",
                "C'est une très bonne nouvelle, merci ! Nos équipes ont récemment amélioré plusieurs antennes autour de {city}.",
            ),
        },
    },
    TopicLabel.ROAMING: {
        EN: {
            NEG: (
                "I'm sorry you're having this trouble abroad. I'm checking the roaming settings and the charges on your line right now.",
                "My apologies. I'm escalating this to our roaming team so it gets fixed, and refunded if you were charged by mistake.",
            ),
            NEU: (
                "Of course. {plan} includes roaming in most European countries; I'll check the details for your destination.",
                "Sure. Roaming can be turned on in the app under 'My line', and I can also activate it for you now.",
            ),
            POS: (
                "Thank you for the feedback, we're glad roaming works well for you!",
                "That's great to hear, thank you. Enjoy your travels with {operator}!",
            ),
        },
        FR: {
            NEG: (
                "Toutes nos excuses pour ce problème à l'étranger. Je vérifie tout de suite les réglages d'itinérance et les frais sur votre ligne.",
                "Je vous présente nos excuses. Je transmets votre dossier à notre équipe itinérance pour corriger le problème, et vous rembourser en cas d'erreur.",
            ),
            NEU: (
                "Bien sûr. {plan} inclut l'itinérance dans la plupart des pays européens ; je vérifie les conditions pour votre destination.",
                "Bien sûr. L'itinérance s'active dans l'application, rubrique « Ma ligne », et je peux aussi l'activer pour vous maintenant.",
            ),
            POS: (
                "Merci pour votre retour, nous sommes heureux que l'itinérance fonctionne bien pour vous !",
                "Très bonne nouvelle, merci. Bon voyage avec {operator} !",
            ),
        },
    },
    TopicLabel.PLAN: {
        EN: {
            NEG: (
                "I understand your frustration, and I'm sorry. Let me see what I can offer you on {plan} as a long-standing customer.",
                "I'm sorry about that. I'm checking which options would give you more data without a big price increase.",
            ),
            NEU: (
                "Of course. You're on {plan} at {price} a month; I'll go through the other plans you're eligible for.",
                "Sure, I'll check which plans you're eligible for and what would change on your bill.",
            ),
            POS: (
                "Thank you, we're delighted that {plan} suits you!",
                "That's lovely to hear, thank you for being with {operator}.",
            ),
        },
        FR: {
            NEG: (
                "Je comprends votre mécontentement, et toutes nos excuses. Je regarde ce que je peux vous proposer sur {plan}, compte tenu de votre ancienneté.",
                "Toutes nos excuses. Je vérifie quelles options vous donneraient plus de données sans forte hausse de prix.",
            ),
            NEU: (
                "Bien sûr. Vous avez {plan} à {price} par mois ; je passe en revue les autres forfaits auxquels vous avez droit.",
                "Bien sûr, je vérifie les forfaits auxquels vous avez droit et ce qui changerait sur votre facture.",
            ),
            POS: (
                "Merci, c'est un plaisir de savoir que {plan} vous convient !",
                "Ça fait plaisir à lire, merci de votre confiance envers {operator}.",
            ),
        },
    },
    TopicLabel.PORTING: {
        EN: {
            NEG: (
                "I'm sorry to hear that. I'm checking your line and your request right now; may I ask what went wrong?",
                "My apologies for the trouble. I'm looking into your request straight away.",
            ),
            NEU: (
                "Of course. To keep your number you'll need your porting code, which I can send you by message.",
                "A number transfer usually takes one working day. May I ask what makes you consider a change?",
            ),
            POS: (
                "Welcome to {operator}! I'm glad the transfer went smoothly.",
                "Thank you, and welcome! Your number is now fully active on our network.",
            ),
        },
        FR: {
            NEG: (
                "Toutes nos excuses. Je vérifie tout de suite votre ligne et votre demande ; puis-je vous demander ce qui ne va pas ?",
                "Je vous présente nos excuses pour ce désagrément. Je m'occupe de votre demande immédiatement.",
            ),
            NEU: (
                "Bien sûr. Pour garder votre numéro, il vous faut votre code de portabilité, que je peux vous envoyer par message.",
                "Un transfert de numéro prend en général un jour ouvré. Puis-je vous demander ce qui vous fait envisager un changement ?",
            ),
            POS: (
                "Bienvenue chez {operator} ! C'est une bonne nouvelle que le transfert se soit bien passé.",
                "Merci, et bienvenue ! Votre numéro est maintenant pleinement actif sur notre réseau.",
            ),
        },
    },
    TopicLabel.OTHER: {
        EN: {
            NEG: (
                "I'm sorry for the trouble. I'm checking your account right now to fix this.",
                "My apologies. I'm making this a priority and I'll update you as soon as it's sorted.",
            ),
            NEU: (
                "Of course, I can help you with that from here.",
                "Sure, let me check your account and walk you through it.",
            ),
            POS: (
                "Thank you for your kind words, I'll share them with the team!",
                "Thanks for letting us know, that's great to hear.",
            ),
        },
        FR: {
            NEG: (
                "Toutes nos excuses pour ce désagrément. Je vérifie votre compte tout de suite pour régler le problème.",
                "Je vous présente nos excuses. Je traite votre demande en priorité et je reviens vers vous dès que c'est réglé.",
            ),
            NEU: (
                "Bien sûr, je peux vous aider à le faire d'ici.",
                "Bien sûr, je vérifie votre compte et je vous guide.",
            ),
            POS: (
                "Merci pour vos gentils mots, je les transmets à l'équipe !",
                "Merci de nous le faire savoir, ça fait plaisir.",
            ),
        },
    },
}

# Customer's second message: depends on the language and the mood (not on the topic).
FOLLOW_UPS: dict[Language, dict[SentimentLabel, Templates]] = {
    EN: {
        NEG: (
            "That's not good enough. If this isn't fixed quickly I'm cancelling my contract.",
            "I've already explained all this twice. I'm seriously thinking of leaving {operator}.",
            "Honestly I'm very disappointed with {operator}.",
        ),
        NEU: (
            "Okay, thanks. I'll wait for your answer.",
            "Alright. Can you send me a confirmation by message?",
            "I see. How long will it take?",
        ),
        POS: (
            "Great, thank you very much for your help!",
            "Perfect, that's very clear. Have a nice day.",
            "Thanks a lot, I appreciate it.",
        ),
    },
    FR: {
        NEG: (
            "Ce n'est pas suffisant. Si ce n'est pas réglé rapidement, je résilie mon contrat.",
            "J'ai déjà tout expliqué deux fois. Je pense sérieusement à quitter {operator}.",
            "Franchement, {operator} me déçoit beaucoup.",
        ),
        NEU: (
            "D'accord, merci. J'attends votre retour.",
            "Très bien. Pouvez-vous m'envoyer une confirmation par message ?",
            "Je vois. Combien de temps cela va-t-il prendre ?",
        ),
        POS: (
            "Super, merci beaucoup pour votre aide !",
            "Parfait, c'est très clair. Bonne journée.",
            "Merci beaucoup, c'est très gentil.",
        ),
    },
}

# Agent's last message: depends on the language and the mood.
CLOSINGS: dict[Language, dict[SentimentLabel, Templates]] = {
    EN: {
        NEG: (
            "I've noted everything on your file and escalated it. We'll get back to you within 48 hours.",
            "Again, I'm sorry for the inconvenience. Your case is now a priority and you'll receive an update by message.",
        ),
        NEU: (
            "I've noted everything on your file. Is there anything else I can do for you?",
            "You'll receive a confirmation by message shortly. Have a good day.",
        ),
        POS: (
            "Thank you for choosing {operator}. Have a great day!",
            "It was a pleasure to help. Have a lovely day!",
        ),
    },
    FR: {
        NEG: (
            "J'ai tout noté dans votre dossier et je l'ai transmis en priorité. Nous revenons vers vous sous 48 heures.",
            "Encore toutes nos excuses pour la gêne. Votre dossier est désormais prioritaire et vous recevrez un suivi par message.",
        ),
        NEU: (
            "J'ai tout noté dans votre dossier. Puis-je faire autre chose pour vous ?",
            "Vous allez recevoir une confirmation par message. Bonne journée.",
        ),
        POS: (
            "Merci d'avoir choisi {operator}. Excellente journée !",
            "Ce fut un plaisir de vous aider. Belle journée !",
        ),
    },
}
