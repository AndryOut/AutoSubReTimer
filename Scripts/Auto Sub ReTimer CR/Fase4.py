import pysrt
import os
import json

project_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# =============================================
# CARICAMENTO PARAMETRI CONFIGURABILI DA JSON
# =============================================
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "Config_Fase4.json")

# Valori di default
DEFAULT_CONFIG = {
    "max_range_next_scene": 250,
    "gap_threshold": 0,
    "scene_change_before_threshold": 250,
    "scene_change_after_threshold": 90
}

try:
    with open(CONFIG_PATH, "r") as f:
        config = json.load(f)
    MAX_RANGE_NEXT_SCENE = config.get("max_range_next_scene", DEFAULT_CONFIG["max_range_next_scene"])
    GAP_THRESHOLD = config.get("gap_threshold", DEFAULT_CONFIG["gap_threshold"])
    SCENE_CHANGE_BEFORE_THRESHOLD = config.get("scene_change_before_threshold", DEFAULT_CONFIG["scene_change_before_threshold"])
    SCENE_CHANGE_AFTER_THRESHOLD = config.get("scene_change_after_threshold", DEFAULT_CONFIG["scene_change_after_threshold"])
except (FileNotFoundError, json.JSONDecodeError):
    MAX_RANGE_NEXT_SCENE = DEFAULT_CONFIG["max_range_next_scene"]
    GAP_THRESHOLD = DEFAULT_CONFIG["gap_threshold"]
    SCENE_CHANGE_BEFORE_THRESHOLD = DEFAULT_CONFIG["scene_change_before_threshold"]
    SCENE_CHANGE_AFTER_THRESHOLD = DEFAULT_CONFIG["scene_change_after_threshold"]

# =============================================
# FUNZIONI PRINCIPALI
# =============================================

def milliseconds_to_subrip_time(milliseconds):
    hours = int(milliseconds // 3600000)
    minutes = int((milliseconds % 3600000) // 60000)
    seconds = int((milliseconds % 60000) // 1000)
    milliseconds = int(milliseconds % 1000)
    return pysrt.SubRipTime(hours=hours, minutes=minutes, seconds=seconds, milliseconds=milliseconds)

def adjust_subs_based_on_scenes(original_subs, scene_subs):
    adjusted_subs = original_subs.copy()
    for idx, sub in enumerate(adjusted_subs):
        sub_start = sub.start.ordinal
        scene_start = None

        for scene in reversed(scene_subs):
            if 0 < (sub_start - scene.start.ordinal) <= SCENE_CHANGE_BEFORE_THRESHOLD:
                scene_start = scene.start.ordinal
                break

        if scene_start is None:
            continue

        sub.start = milliseconds_to_subrip_time(scene_start)

        if idx > 0:
            prev_sub = adjusted_subs[idx - 1]
            if prev_sub.start.ordinal < scene_start < prev_sub.end.ordinal:
                prev_sub.end = milliseconds_to_subrip_time(scene_start)

    return adjusted_subs

def adjust_sub_start_based_on_scene_change(original_subs, scene_subs):
    for sub in original_subs:
        sub_start = sub.start.ordinal
        for scene in scene_subs:
            scene_start = scene.start.ordinal
            if 0 < (scene_start - sub_start) <= SCENE_CHANGE_AFTER_THRESHOLD:
                sub.start = milliseconds_to_subrip_time(scene_start)
                break
    return original_subs

def adjust_sub_end_based_on_next_scene_change(original_subs, scene_subs):
    for idx, sub in enumerate(original_subs):
        sub_end = sub.end.ordinal
        for scene in scene_subs:
            scene_start = scene.start.ordinal
            if 0 < (scene_start - sub_end) <= MAX_RANGE_NEXT_SCENE:
                if idx < len(original_subs) - 1 and original_subs[idx + 1].start.ordinal < scene_start:
                    break
                sub.end = milliseconds_to_subrip_time(scene_start)
                break

    return original_subs

def adjust_sub_end_based_on_previous_scene_change(adjusted_subs, scene_subs):
    max_range = 200
    for adjusted_sub in adjusted_subs:
        adjusted_sub_end = adjusted_sub.end.ordinal
        adjusted_sub_start = adjusted_sub.start.ordinal

        for scene in reversed(scene_subs):
            scene_end = scene.end.ordinal
            if adjusted_sub_start <= scene_end <= adjusted_sub_end and 0 < (adjusted_sub_end - scene_end) <= max_range:
                # Modifica direttamente il timestamp finale al cambio scena
                adjusted_sub.end = milliseconds_to_subrip_time(scene_end)
                break

    return adjusted_subs

# =============================================
# ESECUZIONE PRINCIPALE 
# =============================================
adjusted_subs = pysrt.open(os.path.join(project_path, 'adjusted_Sub.srt'), encoding='utf-8')
scene_subs = pysrt.open(os.path.join(project_path, 'scene_timestamps_adjusted.srt'), encoding='utf-8')
if len(scene_subs) == 0:
    print("Warning: no scene changes found (Fase3 error or unsupported codec) - scene snapping skipped")

adjusted_subs = adjust_subs_based_on_scenes(adjusted_subs, scene_subs)
adjusted_subs = adjust_sub_start_based_on_scene_change(adjusted_subs, scene_subs)
adjusted_subs = adjust_sub_end_based_on_next_scene_change(adjusted_subs, scene_subs)
adjusted_subs = adjust_sub_end_based_on_previous_scene_change(adjusted_subs, scene_subs)

adjusted_subs.save(os.path.join(project_path, 'Final.srt'), encoding='utf-8')
print("Script completed and updated subtitles saved as 'Final.srt'")