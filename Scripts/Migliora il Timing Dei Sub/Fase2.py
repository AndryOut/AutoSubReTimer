import pysrt
from pydub import AudioSegment
import librosa
import numpy as np
import os
import json

# =============================================
# CARICAMENTO PARAMETRI CONFIGURABILI DA JSON
# =============================================
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "Config_Fase2.json")

# Valori di default (gli stessi dello script originale)
DEFAULT_CONFIG = {
    "picco_audio_threshold": 400,
    "max_range_picco": 700,
    "lead_in": 170,
    "lead_out": 450
}

try:
    with open(CONFIG_PATH, "r") as f:
        config = json.load(f)
    # Usa i valori dal JSON, fallback ai default se mancano
    PICCO_AUDIO_THRESHOLD = config.get("picco_audio_threshold", DEFAULT_CONFIG["picco_audio_threshold"])
    MAX_RANGE_PICCO = config.get("max_range_picco", DEFAULT_CONFIG["max_range_picco"])
    LEAD_IN = config.get("lead_in", DEFAULT_CONFIG["lead_in"])
    LEAD_OUT = config.get("lead_out", DEFAULT_CONFIG["lead_out"])
except (FileNotFoundError, json.JSONDecodeError):
    # Se il JSON non esiste o è invalido, usa i default
    PICCO_AUDIO_THRESHOLD = DEFAULT_CONFIG["picco_audio_threshold"]
    MAX_RANGE_PICCO = DEFAULT_CONFIG["max_range_picco"]
    LEAD_IN = DEFAULT_CONFIG["lead_in"]
    LEAD_OUT = DEFAULT_CONFIG["lead_out"]

# =============================================
# FUNZIONI PRINCIPALI
# =============================================

def milliseconds_to_subrip_time(milliseconds):
    hours = int(milliseconds // 3600000)
    minutes = int((milliseconds % 3600000) // 60000)
    seconds = int((milliseconds % 60000) // 1000)
    milliseconds = int(milliseconds % 1000)
    return pysrt.SubRipTime(hours=hours, minutes=minutes, seconds=seconds, milliseconds=milliseconds)

def get_audio_segments(audio_file="vocali.wav", silence_threshold=320):
    y, sr = librosa.load(audio_file, sr=None)
    intervals = librosa.effects.split(y, top_db=25)

    segments = []
    for start, end in intervals:
        segments.append((start / sr * 1000, end / sr * 1000))

    return segments

def adjust_timestamps_based_on_peaks(subs, audio_file):
    audio_segments = get_audio_segments(audio_file)
    for sub in subs:
        start_ms = sub.start.ordinal
        end_ms = sub.end.ordinal

        # Modificato: 200 -> PICCO_AUDIO_THRESHOLD
        for segment_start, segment_end in audio_segments:
            if segment_start >= start_ms:
                if segment_start - start_ms > PICCO_AUDIO_THRESHOLD:
                    found = False
                    for closer_segment_start, closer_segment_end in audio_segments:
                        if start_ms <= closer_segment_start <= start_ms + 100:
                            sub.start = milliseconds_to_subrip_time(closer_segment_start)
                            found = True
                            break
                    if not found:
                        sub.start = milliseconds_to_subrip_time(start_ms)
                else:
                    sub.start = milliseconds_to_subrip_time(segment_start)
                break

        is_on_peak = any(segment_start <= end_ms <= segment_end for segment_start, segment_end in audio_segments)

        if not is_on_peak:
            # Modificato: [600, 600] -> [MAX_RANGE_PICCO, MAX_RANGE_PICCO]
            max_ranges = [MAX_RANGE_PICCO, MAX_RANGE_PICCO]
            for max_range in max_ranges:
                found = False
                for segment_start, segment_end in reversed(audio_segments):
                    if segment_end <= end_ms and segment_start >= start_ms:
                        if end_ms - segment_end <= max_range:
                            sub.end = milliseconds_to_subrip_time(segment_end)
                            found = True
                            break
                if found:
                    break

            # Modificato: 600 -> MAX_RANGE_PICCO
            if end_ms - sub.end.ordinal > MAX_RANGE_PICCO:
                for segment_start, segment_end in audio_segments:
                    if segment_end <= end_ms and segment_start >= start_ms:
                        if end_ms - segment_end <= 300:
                            sub.end = milliseconds_to_subrip_time(segment_end)
                            break
                else:
                    sub.end = milliseconds_to_subrip_time(end_ms)

    return subs

# Modificato: lead_in=200 -> lead_in=LEAD_IN, lead_out=500 -> lead_out=LEAD_OUT
def add_lead_in_out(segments, original_subs, lead_in=LEAD_IN, lead_out=LEAD_OUT):
    adjusted_segments = []
    for i, (start, end) in enumerate(segments):
        original_start_ms = original_subs[i].start.ordinal
        if start == original_start_ms:
            new_start = start
        else:
            new_start = max(0, start - lead_in)
        new_end = end + lead_out
        adjusted_segments.append((new_start, new_end))
    return adjusted_segments

def adjust_segments_for_overlap(segments, max_lead_out=50, lead_in=0, max_lead_in=0, lead_out=30):
    adjusted_segments = []
    for i in range(len(segments) - 1):
        start, end = segments[i]
        next_start, next_end = segments[i + 1]

        if (next_start - end) <= max_lead_out:
            if (next_start - end) > lead_out:
                remaining_time = next_start - end - lead_out
                end = next_start - remaining_time 
            else:
                end = next_start  
        else:
            if (next_start - end) > lead_in and (next_start - end) < max_lead_in:
                end = next_start - lead_in

        adjusted_segments.append((start, end))

    adjusted_segments.append(segments[-1])
    return adjusted_segments

# =============================================
# ESECUZIONE PRINCIPALE
# =============================================
project_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
audio_file = os.path.join(project_path, "vocali.wav")
srt_file = os.path.join(project_path, "Sub.srt")

subs = pysrt.open(srt_file, encoding='utf-8')
original_subs = pysrt.open(srt_file, encoding='utf-8')

subs = adjust_timestamps_based_on_peaks(subs, audio_file)
audio_segments = get_audio_segments(audio_file)
final_segments = [(sub.start.ordinal, sub.end.ordinal) for sub in subs]
adjusted_segments = add_lead_in_out(final_segments, original_subs)
adjusted_segments = adjust_segments_for_overlap(adjusted_segments)

for sub, (start, end) in zip(subs, adjusted_segments):
    sub.start = milliseconds_to_subrip_time(start)
    sub.end = milliseconds_to_subrip_time(end)

output_file = os.path.join(project_path, "adjusted_Sub.srt")
subs.save(output_file, encoding='utf-8')

print(f"File SRT salvato come {output_file}")