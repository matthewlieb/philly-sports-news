"""Narration: text-to-speech per beat, then word timings so captions can follow the voice.

VOICE_PROVIDER=openai (default) or elevenlabs.
"""
import os
import subprocess
from pathlib import Path

import requests
from openai import OpenAI

_OPENAI_INSTRUCTIONS = (
    "Energetic Philadelphia sports-radio host giving a quick update. Fast, punchy pace with confident emphasis "
    "on names and numbers. Conversational, a little edge, never shouty. No long pauses between sentences."
)


def _tts_openai(text: str, path: Path) -> None:
    with OpenAI().audio.speech.with_streaming_response.create(
        model=os.environ.get("OPENAI_TTS_MODEL", "gpt-4o-mini-tts"),
        voice=os.environ.get("OPENAI_TTS_VOICE", "ash"),
        input=text,
        instructions=_OPENAI_INSTRUCTIONS,
        response_format="mp3",
    ) as resp:
        resp.stream_to_file(path)


def _tts_elevenlabs(text: str, path: Path) -> None:
    voice_id = os.environ["ELEVENLABS_VOICE_ID"]
    resp = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
        headers={"xi-api-key": os.environ["ELEVENLABS_API_KEY"]},
        json={"text": text, "model_id": os.environ.get("ELEVENLABS_MODEL", "eleven_multilingual_v2"),
              "voice_settings": {"stability": 0.35, "similarity_boost": 0.8, "style": 0.45}},
        timeout=120,
    )
    resp.raise_for_status()
    path.write_bytes(resp.content)


def duration(path: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


def _whisper_words(path: Path) -> list[dict]:
    with open(path, "rb") as f:
        result = OpenAI().audio.transcriptions.create(
            model="whisper-1", file=f, response_format="verbose_json", timestamp_granularities=["word"])
    return [{"word": w.word, "start": w.start, "end": w.end} for w in (result.words or [])]



def align(script_words: list[str], heard: list[dict], total: float) -> list[tuple[float, float]]:
    """Timing for each script word. Uses Whisper's timings when the words line up, otherwise spreads
    words across the clip in proportion to their length (numbers and names often transcribe differently)."""
    if len(heard) == len(script_words):
        return [(h["start"], h["end"]) for h in heard]
    start = heard[0]["start"] if heard else 0.0
    end = heard[-1]["end"] if heard else total
    weights = [len(w) + 2 for w in script_words]
    span, t, out = end - start, start, []
    for w in weights:
        d = span * w / sum(weights)
        out.append((t, t + d))
        t += d
    return out


def narrate(beats: list[dict], workdir: Path) -> tuple[Path, list[dict]]:
    """Synthesize every beat, join them, and return the audio plus per-beat timings:
    [{"start", "end", "words": [(word, start, end), ...]}] in seconds on the final timeline."""
    provider = os.environ.get("VOICE_PROVIDER", "openai").lower()
    tts = _tts_elevenlabs if provider == "elevenlabs" else _tts_openai
    tempo = float(os.environ.get("VOICE_TEMPO", "1.18"))
    gap = 0.12
    wavs, timeline, t = [], [], 0.0
    silence = workdir / "gap.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
                    "-t", str(gap), str(silence)], check=True)
    for i, beat in enumerate(beats):
        mp3, wav = workdir / f"beat{i}.mp3", workdir / f"beat{i}.wav"
        tts(beat["say"], mp3)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(mp3), "-af", f"atempo={tempo}",
                        "-ar", "44100", "-ac", "1", str(wav)], check=True)
        d = duration(wav)
        words = beat["say"].split()
        times = align(words, _whisper_words(wav), d)
        timeline.append({"start": t, "end": t + d,
                         "words": [(w, t + s, t + e) for w, (s, e) in zip(words, times)]})
        wavs += [wav, silence]
        t += d + gap

    concat_list = workdir / "voice.txt"
    concat_list.write_text("".join(f"file '{w.name}'\n" for w in wavs[:-1]))
    voice = workdir / "voice.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(concat_list),
                    "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "44100", str(voice)], check=True)
    return voice, timeline
