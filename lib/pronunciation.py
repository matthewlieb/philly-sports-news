"""How the narrator should say names that text-to-speech tends to get wrong.

Only the audio uses these respellings; captions keep the real spelling. Add a name whenever a video
gets it wrong. Respellings use plain syllables with the stressed one in caps, which reads naturally
for both OpenAI and ElevenLabs voices.
"""
import re

NAMES = {
    # Eagles: the team's own guide (weekly depth chart in the media guide, Nov 2026), then Pro Football Reference
    "Sirianni": "sir-ee-AH-nee",
    "Fangio": "FAN-jee-oh",
    "Lurie": "LUR-ee",
    "Saquon": "SAY-kwon",
    "Goedert": "GOD-ert",
    "Mailata": "my-LOT-uh",
    "Baun": "BAWN",
    "DeJean": "duh-ZHAHN",
    "Jihaad": "JUH-haad",
    "Kiran": "kuh-RON",
    "Amegadjie": "AH-muh-GAH-jee",
    "Uar": "OO-ar",
    "Covey": "Cuvvy",  # "CUHV-ee" gets spelled out letter by letter
    "Deguara": "duh-GWAH-ruh",
    "Ebiketie": "eb-uh-KAY-tee",
    "Epenesa": "ep-uh-NESS-uh",
    "Greenard": "gruh-NARD",
    "Jalyx": "JAY-lix",
    "Smael": "SMILE",
    "Mukuba": "muh-KOO-bah",
    "Moro": "MORE-oh",
    "Ojomo": "oh-JOE-moe",
    "Ojukwu": "oh-JOO-koo",
    "Reiger": "RYE-ger",
    "Kelee": "KEE-lee",
    "Stowers": "Stauers",  # rhymes with "hours"; "STOW-erz" comes out as "stoh"
    "Weru": "WARE-oo",
    "Wisniewski": "wiz-NESS-kee",
    "Riq": "REEK",
    "Calcaterra": "kal-kuh-TARE-uh",
    "DeVonta": "duh-VAWN-tay",
    "Dontayvion": "don-TAY-vee-in",
    "Ezukanma": "ez-oo-KAH-muh",
    "Orji": "OR-jee",
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
