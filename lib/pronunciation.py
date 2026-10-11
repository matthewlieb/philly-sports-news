"""How the narrator should say names that text-to-speech tends to get wrong.

Only the audio uses these respellings; captions keep the real spelling. Add a name whenever a video
gets it wrong. Respellings use plain syllables with the stressed one in caps, which reads naturally
for both OpenAI and ElevenLabs voices.
"""
import re

NAMES = {
    # Eagles
    "Sirianni": "sir-ee-AH-nee",
    "Goedert": "GED-ert",
    "Mailata": "my-LAH-tah",
    "Baun": "BAWN",
    "DeJean": "duh-ZHAHN",
    "Ojomo": "oh-JOH-moh",
    "Jihaad": "jee-HAHD",
    "Saquon": "SAY-kwon",
    "Fangio": "FAN-jee-oh",
    "Lurie": "LUR-ee",
    # Sixers
    "Embiid": "em-BEED",
    "Oubre": "OO-bray",
    # Phillies
    "Realmuto": "ree-al-MOO-toh",
    "Alvarado": "al-vuh-RAH-doh",
    "Dombrowski": "dom-BROW-skee",
    # Flyers
    "Michkov": "MEESH-kov",
    "Konecny": "kuh-NETS-nee",
    "Tocchet": "TOCK-it",
    "Sanheim": "SAN-hime",
}

_PATTERN = re.compile(r"\b(" + "|".join(map(re.escape, NAMES)) + r")\b")


def for_speech(text: str) -> str:
    return _PATTERN.sub(lambda m: NAMES[m.group(1)], text)
