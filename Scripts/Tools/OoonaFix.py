import subprocess
import sys
import re
import os
import copy
from tkinter import filedialog
import tkinter as tk
import time
import locale
import ctypes

# Paletteclass App
BG_ROOT   = "#08080B"   # canvas
BG_PANEL  = "#0F0F14"   # surface 1
BG_CARD   = "#141419"   # surface 2
BG_INPUT  = "#1A1A21"   # surface 3
BORDER    = "#232329"   # bordo
BORDER_ACC= "#3A3252"
ACCENT    = "#7C5CFA"
ACCENT_H  = "#9580FF"
ACCENT_DIM= "#221D38"
SUCCESS   = "#2ED191"
SUCCESS_H = "#3EE6A2"
DANGER    = "#F5566B"
DANGER_H  = "#FF6E82"
TEXT_1    = "#EBEBF2"
TEXT_2    = "#63636F"
TEXT_A    = "#B9A8FF"

try:
    import customtkinter as ctk
except ImportError:
    class MissingDependencyWindow(ctk.CTkTopLevel):
        def __init__(self, master=None):
            super().__init__(master)
            self.title("Dependency Error")
            self.geometry("400x180")
            self.attributes("-topmost", True)
            self.resizable(False, False)

            self.grid_rowconfigure(0, weight=1)
            self.grid_rowconfigure(1, weight=0)
            self.grid_columnconfigure(0, weight=1)

            message_label = ctk.CTkLabel(self, text="The 'customtkinter' module is not installed.",
                                         font=ctk.CTkFont(size=14, weight="bold"))
            message_label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="nsew")

            instruction_label = ctk.CTkLabel(self, text="Please run the following command to install it:",
                                             font=ctk.CTkFont(size=12))
            instruction_label.grid(row=1, column=0, padx=20, pady=(0, 5), sticky="w")

            command_frame = ctk.CTkFrame(self)
            command_frame.grid(row=2, column=0, padx=20, pady=(0, 20), sticky="ew")
            command_frame.grid_columnconfigure(0, weight=1)

            self.command_entry = ctk.CTkEntry(command_frame, width=300)
            self.command_entry.insert(0, "pip install customtkinter")
            self.command_entry.configure(state="readonly")
            self.command_entry.grid(row=0, column=0, padx=(10, 5), pady=10, sticky="ew")

            copy_button = ctk.CTkButton(command_frame, text="Copy", command=self.copy_command)
            copy_button.grid(row=0, column=1, padx=(5, 10), pady=10)

            self.protocol("WM_DELETE_WINDOW", self.on_closing)

        def copy_command(self):
            self.clipboard_clear()
            self.clipboard_append(self.command_entry.get())
            self.update()

        def on_closing(self):
            self.destroy()
            sys.exit(1)

    ctk.set_appearance_mode("Dark")
    root = tk.Tk()
    root.withdraw()
    MissingDependencyWindow(root)
    root.mainloop()
    sys.exit(1)

STANDARD_STYLES_ASS_V28 = """
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Trebuchet MS,72,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,4.0,1,2,10,10,45,1
Style: Italics,Trebuchet MS,72,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,-1,-1,0,0,100,100,0,0,1,4.0,1,2,10,10,45,1
Style: Top,Trebuchet MS,72,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,4.0,1,8,10,10,45,1
Style: Italics Top,Trebuchet MS,72,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,-1,-1,0,0,100,100,0,0,1,4.0,1,8,10,10,45,1
Style: sign,Trebuchet MS,65,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,3,1,8,10,10,45,1
"""

def fix_incomplete_italics(text):
    lines = text.split(r'\N')
    
    if len(lines) >= 2:
        first_line = lines[0].strip()
        last_line = lines[-1].strip()
        
        if (first_line.startswith('{\\i1}') and first_line.endswith('{\\i0}') and
            not last_line.endswith('{\\i0}')):
            
            lines[0] = first_line[:-5]  
            lines[-1] = last_line + '{\\i0}'
            
            return r'\N'.join(lines)
    
    return text

def normalize_text(text):
    return re.sub(r'\s{2,}', ' ', text).strip()

SPEAKER_PREFIX_PATTERN = r'^(?:\s*\{.*?\}\s*)*[\-\—–]\s*(\{\\i1\})?'

def clean_speaker_prefix(line):
    line = line.strip()
    if line.startswith(('-', '—', '–')):
        return re.sub(r'^[\-\—–]\s+', '- ', line)
    return line

ITALICS_FULL_LINE_PATTERN = re.compile(r'^\s*\{\\i1\}(.*?)\{\\i0\}\s*$', re.DOTALL)

ASS_FIELDS = ['Layer', 'Start', 'End', 'Style', 'Name', 'MarginL', 'MarginR', 'MarginV', 'Effect', 'Text']

def parse_ass_time(ass_time_str):
    h, m, scs = ass_time_str.split(':')
    s, cs = scs.split('.')
    return int(h) * 3600 + int(m) * 60 + int(s) + int(cs) / 100

def format_ass_time(seconds):
    h = int(seconds // 3600)
    seconds %= 3600
    m = int(seconds // 60)
    seconds %= 60
    s = int(seconds // 1)
    cs = int((seconds - s) * 100)
    return f"{h:01}:{m:02}:{s:02}.{cs:02}"

def remove_tags(text):
    return re.sub(r'\{.*?\}', '', text)

def get_visible_length(text):
    return len(remove_tags(text))

def capitalize_hyphenated(text):
    def process_match(match):
        first_char = match.group(1)
        remaining = match.group(2)
        
        parts = remaining.split('-')
        processed = []
        for part in parts:
            if part and part[0].lower() == first_char.lower():
                processed.append(part[0].upper() + part[1:])
            else:
                processed.append(part)
        
        return first_char + '-'.join(processed)

    pattern = r'([A-Z])(-[a-z][^-\s]*)'
    while re.search(pattern, text):
        new_text = re.sub(pattern, process_match, text)
        if new_text == text:  # es. "E-mail": niente da cambiare, evita il ciclo infinito
            break
        text = new_text
    return text

def process_an8_tags(text, current_style):
    has_an8 = False
    starts_with_combo = False
    
    start_patterns = [
        r'^\s*\{\\an8\\i1\}',
        r'^\s*\{\\i1\\an8\}', 
        r'^\s*\{\\an8\}\s*\{\\i1\}',
        r'^\s*\{\\i1\}\s*\{\\an8\}'
    ]
    
    for pattern in start_patterns:
        if re.search(pattern, text):
            starts_with_combo = True
            has_an8 = True
            break
    
    if not starts_with_combo:
        if re.search(r'\\an8', text):
            has_an8 = True
    
    if not has_an8:
        return text, current_style
    
    clean_text_no_tags = remove_tags(text).strip()
    if clean_text_no_tags.isupper():
        text = re.sub(r'\\an8', '', text)
        text = re.sub(r'\{\s*\}', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text, current_style
    
    text = re.sub(r'\\an8', '', text)
    
    if starts_with_combo:
        ends_with_i0 = text.strip().endswith('{\\i0}')
        if ends_with_i0:
            text = re.sub(r'\\i1', '', text)   
            text = re.sub(r'\\i0', '', text)
    
    text = re.sub(r'\{\s*\}', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    
    if starts_with_combo:
        if ends_with_i0:
            new_style = 'Italics Top'
        else:
            new_style = 'Top'
    elif has_an8 and current_style == 'Italics':
        new_style = 'Italics Top'
    elif has_an8:
        new_style = 'Top'
    else:
        new_style = current_style
    
    return text, new_style

def detect_top_alignment_from_original_style(event_data, original_style_name, styles_section):
    text = event_data['Text']
    
    style_alignment = None
    alignment_index = None
    
    for line in styles_section:
        if line.startswith('Format:'):
            format_parts = [x.strip() for x in line.split(':')[1].split(',')]
            if 'Alignment' in format_parts:
                alignment_index = format_parts.index('Alignment')
                break
    
    if alignment_index is not None:
        for line in styles_section:
            if line.startswith('Style:') and original_style_name in line.split(',')[0]:
                style_parts = line.split(',')
                if len(style_parts) > alignment_index:
                    style_alignment = style_parts[alignment_index].strip()
                    break
    
    if style_alignment in ['7', '8', '9']:
        has_i1_tag = re.search(r'\\i1', text) is not None
        
        cleaned_text = re.sub(r'\\an[789]', '', text)
        cleaned_text = re.sub(r'\{\s*\}', '', cleaned_text)  
        
        if has_i1_tag:
            cleaned_text = re.sub(r'\\i[01]', '', cleaned_text)
            cleaned_text = re.sub(r'\{\s*\}', '', cleaned_text)
            return cleaned_text, 'Italics Top'
        else:
            return cleaned_text, 'Top'
    
    return text, event_data['Style']

def process_text(text):
    clean_text_no_tags = remove_tags(text).strip()
    
    if clean_text_no_tags.startswith('-'):
        return capitalize_hyphenated(text)
    else:
        unbroken_text = re.sub(r'\\N', ' ', text).strip()
        unbroken_text = re.sub(r'\s+', ' ', unbroken_text)
        visible_length = get_visible_length(unbroken_text)
        
        if visible_length <= 47:
            return capitalize_hyphenated(unbroken_text)
        else:
            return capitalize_hyphenated(text)

def update_header_and_styles(content):
    styles_pos = content.find('[V4+ Styles]')
    if styles_pos == -1:
        return content  
    
    nuovo_header = """[Script Info]
ScriptType: v4.00+
PlayDepth: 0
WrapStyle: 0
PlayResX: 1920
PlayResY: 1080
LayoutResX: 1920
LayoutResY: 1080
ScaledBorderAndShadow: Yes
YCbCr Matrix: TV.709

"""
    
    contenuto_modificato = nuovo_header + content[styles_pos:]
    
    default_style = "Style: Default,Trebuchet MS,72,&H00FFFFFF,&H0000FFFF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,4,1,2,10,10,45,1"
    
    if 'Style: Default,' in contenuto_modificato:
        lines = contenuto_modificato.splitlines()
        new_lines = []
        for line in lines:
            if line.strip().startswith('Style: Default,'):
                new_lines.append(default_style)
            else:
                new_lines.append(line)
        return '\n'.join(new_lines)
    else:
        lines = contenuto_modificato.splitlines()
        new_lines = []
        in_styles = False
        last_style_pos = -1
        
        for i, line in enumerate(lines):
            if line.strip() == '[V4+ Styles]':
                in_styles = True
                new_lines.append(line)
                continue
            elif line.strip().startswith('[') and in_styles:
                in_styles = False
                if last_style_pos != -1:
                    new_lines.insert(last_style_pos + 1, default_style)
            
            if in_styles and line.strip().startswith('Style:'):
                last_style_pos = len(new_lines)
            
            new_lines.append(line)
        
        if in_styles and last_style_pos != -1:
            new_lines.insert(last_style_pos + 1, default_style)
        
        return '\n'.join(new_lines)

def process_subtitle_file(file_path, log_callback, output_filename_suffix, app_instance):
    log_callback(f"Loading file: {file_path}", 'info')
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        content = update_header_and_styles(content)
        lines = content.splitlines(keepends=True)
    except UnicodeDecodeError:
        log_callback("ERROR: the subtitle file is not UTF-8 encoded. "
                     "Open it (e.g. in Aegisub or Notepad), save it as UTF-8 and try again.", 'error')
        return False
    except Exception as e:
        log_callback(f"ERROR: Failed to load ASS file. ({e})", 'error')
        return False

    original_styles_section = []
    in_original_styles = False
    for line in lines:
        if line.strip() == '[V4+ Styles]' or line.strip() == '[V4 Styles]':
            in_original_styles = True
            original_styles_section.append(line)
            continue
        elif line.strip().startswith('[') and in_original_styles:
            in_original_styles = False
        if in_original_styles:
            original_styles_section.append(line)

    output_lines = []
    in_styles_block = False
    in_script_block = False
    dialogue_events = []
    sign_events = []
    lines = fix_puntini(lines)

    for line in lines:
        line_stripped = line.rstrip('\n')

        if line_stripped.strip() == '[V4+ Styles]' or line_stripped.strip() == '[V4 Styles]':
            in_styles_block = True
            output_lines.append('[V4+ Styles]')
            output_lines.extend(STANDARD_STYLES_ASS_V28.strip().split('\n')[1:])
            continue

        if line_stripped.strip().startswith('[') and line_stripped.strip().endswith(']'):
            in_styles_block = False

        if line_stripped.strip() == '[Events]':
            in_script_block = True
            output_lines.append(line_stripped)
            continue

        if in_styles_block and (line_stripped.startswith('Style:') or line_stripped.startswith('Format:')):
            continue

        if in_script_block and line_stripped.startswith('Format:'):
            output_lines.append(line_stripped)
            continue

        if in_script_block and line_stripped.startswith('Dialogue:'):
            content = line_stripped[len('Dialogue: '):]
            parts = content.split(',', 9)

            if len(parts) == 10:
                event_data_base = dict(zip(ASS_FIELDS, parts))
                original_style_name = parts[3].strip()
                raw_event_text = parts[9]
                event_data_base['Style'] = 'Default'
                all_raw_lines_split_by_newline = raw_event_text.split(r'\N')
                speaker_line_indices = []

                for idx, single_line_raw in enumerate(all_raw_lines_split_by_newline):
                    cleaned_line_for_prefix_check = re.sub(r'\{\\(pos|move|org)\(.*?\)\}', '', single_line_raw)
                    if re.match(SPEAKER_PREFIX_PATTERN, cleaned_line_for_prefix_check):
                        speaker_line_indices.append(idx)

                if len(speaker_line_indices) > 1:
                    whole_italic = (raw_event_text.strip().startswith('{\\i1}') and 
                                    raw_event_text.strip().endswith('{\\i0}'))

                    for i in range(len(speaker_line_indices)):
                        start_idx = speaker_line_indices[i]
                        end_idx = speaker_line_indices[i+1] if i + 1 < len(speaker_line_indices) else len(all_raw_lines_split_by_newline)

                        segment_lines = all_raw_lines_split_by_newline[start_idx:end_idx]
                        combined_segment_text = r'\N'.join(segment_lines)
                        new_event = copy.deepcopy(event_data_base)
                        cleaned_first_line_of_segment = re.sub(r'\{\\(pos|move|org)\(.*?\)\}', '', segment_lines[0])
                        speaker_prefix_match = re.match(SPEAKER_PREFIX_PATTERN, cleaned_first_line_of_segment)
                        if speaker_prefix_match:
                            prefix_text = speaker_prefix_match.group(0)
                            text = combined_segment_text.strip()
                            original_has_italics_tag = (r'{\i1}' in prefix_text) and text.endswith('{\\i0}')
                        else:
                            original_has_italics_tag = False

                        is_italic = whole_italic or original_has_italics_tag

                        new_event['Text'] = clean_speaker_prefix(combined_segment_text)
                        new_event['Text'] = fix_incomplete_italics(new_event['Text'])
                        new_event['Text'], new_event['Style'] = detect_top_alignment_from_original_style(
                            new_event, original_style_name, original_styles_section
                        )

                        if start_idx == 0:
                            new_event['Style'] = 'Italics' if is_italic else 'Default'
                        else:
                            new_event['Style'] = 'Italics Top' if is_italic else 'Top'

                        if whole_italic:
                            new_event['Text'] = re.sub(r'{\\i[01]}', '', new_event['Text'])

                        new_event['_whole_italic'] = whole_italic

                        processed_events_from_p3 = process_styles(new_event, log_callback)

                        for p3_event in processed_events_from_p3:
                            if p3_event.get('_whole_italic', False):
                                continue

                            if p3_event['Style'] != 'sign' and re.match(SPEAKER_PREFIX_PATTERN, p3_event['Text']):
                                original_speaker_prefix_match = re.match(SPEAKER_PREFIX_PATTERN, p3_event['Text'])
                                if original_speaker_prefix_match:
                                    prefix_text = original_speaker_prefix_match.group(0)
                                    text = p3_event['Text'].strip()
                                    original_has_italics_tag = (r'{\i1}' in prefix_text) and text.endswith('{\\i0}')
                                else:
                                    original_has_italics_tag = False
                                p3_event['Text'] = clean_speaker_prefix(p3_event['Text'])
                                if p3_event['Style'] not in ['Top', 'Italics Top'] and original_has_italics_tag:
                                    p3_event['Style'] = 'Italics'
                                if original_has_italics_tag:
                                    p3_event['Text'] = re.sub(r'\{\\i[01]\}', '', p3_event['Text'])

                        for p3_event in processed_events_from_p3:
                            if p3_event.get('_whole_italic', False):
                                dialogue_events.append(p3_event)
                                continue

                            p3_event['Text'] = p3_event['Text']
                            lines = p3_event['Text'].split(r'\N')
                            processed_lines = []
                            all_lines_have_italics = True
                            overall_has_italics = False

                            if len(lines) > 0:
                                first_line_clean = lines[0].strip()
                                last_line_clean = lines[-1].strip()
                                overall_has_italics = (first_line_clean.startswith('{\\i1}') and 
                                                      last_line_clean.endswith('{\\i0}'))
                            first_line_has_combo = False
                            if lines and len(lines) > 0:
                                first_line = lines[0].strip()
                                first_line_has_combo = ('{\\an8\\i1}' in first_line or '{\\i1\\an8}' in first_line)

                            for line in lines:
                                if line.startswith('{\\i1}') and line.endswith('{\\i0}') and not first_line_has_combo:
                                    processed_lines.append(line[5:-5])  
                                elif overall_has_italics:
                                    if line == lines[0]:  
                                        processed_lines.append(line[5:])  
                                    elif line == lines[-1]:  
                                        processed_lines.append(line[:-5])  
                                    else:  
                                        processed_lines.append(line)
                                else:
                                    processed_lines.append(line)
                                    all_lines_have_italics = False

                            if all_lines_have_italics or overall_has_italics:
                                current_style = p3_event['Style']
                                if current_style == 'Default':
                                    p3_event['Style'] = 'Italics'
                                elif current_style == 'Top':
                                    p3_event['Style'] = 'Italics Top'

                            p3_event['Text'] = r'\N'.join(processed_lines)
                            p3_event['Text'], p3_event['Style'] = process_an8_tags(p3_event['Text'], p3_event['Style'])
                            p3_event['Text'] = process_text(p3_event['Text'])
                            dialogue_events.append(p3_event)
                else:
                    event_data_to_process = copy.deepcopy(event_data_base)
                    event_data_to_process['Text'] = raw_event_text
                    event_data_to_process['Text'] = re.sub(r'\{\\(pos|move|org)\(.*?\)\}', '', event_data_to_process['Text'])

                    if re.match(SPEAKER_PREFIX_PATTERN, event_data_to_process['Text']):
                        original_speaker_prefix_match = re.match(SPEAKER_PREFIX_PATTERN, raw_event_text)
                        if original_speaker_prefix_match:
                            prefix_text = original_speaker_prefix_match.group(0)
                            text = raw_event_text.strip()
                            original_has_italics_tag = (r'{\i1}' in prefix_text) and text.endswith('{\\i0}')
                        else:
                            original_has_italics_tag = False

                        event_data_to_process['Text'] = clean_speaker_prefix(raw_event_text)

                        if original_has_italics_tag:
                            event_data_to_process['Style'] = 'Italics'

                    event_data_to_process['Text'] = event_data_to_process['Text']
                    
                    event_data_to_process['Text'] = fix_incomplete_italics(event_data_to_process['Text'])
                    event_data_to_process['Text'], event_data_to_process['Style'] = detect_top_alignment_from_original_style(
                        event_data_to_process, original_style_name, original_styles_section
                    )
                    processed_events_from_p3 = process_styles(event_data_to_process, log_callback)

                    for p3_event in processed_events_from_p3:
                        if p3_event['Style'] != 'sign' and re.match(SPEAKER_PREFIX_PATTERN, p3_event['Text']):
                            original_speaker_prefix_match = re.match(SPEAKER_PREFIX_PATTERN, p3_event['Text'])
                            if original_speaker_prefix_match:
                                prefix_text = original_speaker_prefix_match.group(0)
                                text = p3_event['Text'].strip()
                                original_has_italics_tag = (r'{\i1}' in prefix_text) and text.endswith('{\\i0}')
                            else:
                                original_has_italics_tag = False
                            p3_event['Text'] = clean_speaker_prefix(p3_event['Text'])
                            if p3_event['Style'] not in ['Top', 'Italics Top'] and original_has_italics_tag:
                                p3_event['Style'] = 'Italics'
                            if original_has_italics_tag:
                                p3_event['Text'] = re.sub(r'\{\\i[01]\}', '', p3_event['Text'])

                    for p3_event in processed_events_from_p3:
                        p3_event['Text'] = p3_event['Text']
                        lines = p3_event['Text'].split(r'\N')
                        processed_lines = []
                        all_lines_have_italics = True
                        overall_has_italics = False

                        if len(lines) > 0:
                            first_line_clean = lines[0].strip()
                            last_line_clean = lines[-1].strip()
                            overall_has_italics = (first_line_clean.startswith('{\\i1}') and 
                                                  last_line_clean.endswith('{\\i0}'))
                        first_line_has_combo = False
                        if lines and len(lines) > 0:
                            first_line = lines[0].strip()
                            first_line_has_combo = ('{\\an8\\i1}' in first_line or '{\\i1\\an8}' in first_line)

                        for line in lines:
                            if line.startswith('{\\i1}') and line.endswith('{\\i0}') and not first_line_has_combo:
                                processed_lines.append(line[5:-5])  
                            elif overall_has_italics:
                                if line == lines[0]:  
                                    processed_lines.append(line[5:])  
                                elif line == lines[-1]:  
                                    processed_lines.append(line[:-5])  
                                else:  
                                    processed_lines.append(line)
                            else:
                                processed_lines.append(line)
                                all_lines_have_italics = False

                        if all_lines_have_italics or overall_has_italics:
                            current_style = p3_event['Style']
                            if current_style == 'Default':
                                p3_event['Style'] = 'Italics'
                            elif current_style == 'Top':
                                p3_event['Style'] = 'Italics Top'

                        p3_event['Text'] = r'\N'.join(processed_lines)
                        p3_event['Text'], p3_event['Style'] = process_an8_tags(p3_event['Text'], p3_event['Style'])
                        p3_event['Text'] = process_text(p3_event['Text'])
                        dialogue_events.append(p3_event)
        else:
            output_lines.append(line_stripped)

    temp_dialogue_events = []
    for event in dialogue_events:
        if event['Style'] == 'sign':
            sign_events.append(event)
        else:
            temp_dialogue_events.append(event)

    dialogue_events[:] = temp_dialogue_events
    processed_dialogue_events = merge_timings(dialogue_events, log_callback)
    dialogue_events[:] = processed_dialogue_events

    if sign_events:
        processed_sign_events = merge_timings(sign_events, log_callback)
        sign_events[:] = processed_sign_events

    final_output_lines = []
    events_inserted = False

    for line in output_lines:
        final_output_lines.append(line)
        if line.strip() == '[Events]' and not events_inserted:
            for event_data in dialogue_events:
                 event_parts = [event_data[key] for key in ASS_FIELDS]
                 final_output_lines.append('Dialogue: ' + ','.join(event_parts))

            final_output_lines.append(f"Dialogue: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,,{app_instance.lang_selector.get_text('formatting_comment')}")
            
            if sign_events:
                for event_data in sign_events:
                    event_parts = [event_data[key] for key in ASS_FIELDS]
                    final_output_lines.append('Dialogue: ' + ','.join(event_parts))
            events_inserted = True

    base, ext = os.path.splitext(file_path)
    output_path = f"{base}{output_filename_suffix}.ass"
    log_callback(f"Saving file: {output_path}", 'info')

    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(final_output_lines))
    except Exception as e:
        log_callback(f"ERROR: Failed to save file. ({e})", 'error')
        return False

    log_callback("--- Processing completed successfully! ---", 'success')
    return True

def process_styles(event_data, log_callback):
    original_text = event_data['Text']
    lines = original_text.split(r'\N')
    all_capital_parts = []
    dialogue_parts = []

    for line in lines:
        cleaned_line_for_check = re.sub(r'\{\\.*?\}', '', line).strip()
        if cleaned_line_for_check and cleaned_line_for_check.isupper():
            all_capital_parts.append(line)
        else:
            dialogue_parts.append(line)

    if not dialogue_parts and all_capital_parts:
        event_data['Style'] = 'sign'
        return [event_data]

    if dialogue_parts and all_capital_parts:
        dialogue_text = r'\N'.join(dialogue_parts).strip()
        sign_text = r'\N'.join(all_capital_parts).strip()
        sign_event = copy.copy(event_data)
        sign_event['Style'] = 'sign'
        sign_event['Text'] = sign_text
        event_data['Text'] = dialogue_text
        return [event_data, sign_event]
    return [event_data]

def merge_timings(dialogue_events, log_callback):
    if not dialogue_events:
        return dialogue_events
    
    return dialogue_events

def fix_puntini(lines):
    new_lines = lines.copy()
    i = 0
    
    while i < len(new_lines):
        if new_lines[i].startswith('Dialogue:'):
            parts = new_lines[i].split(',', 9)
            if len(parts) >= 10:
                raw_text = parts[9]
                clean_text = re.sub(r'\{.*?\}', '', raw_text).strip()
                
                if clean_text.endswith('...'):
                    max_lookahead = min(i + 4, len(new_lines))
                    for j in range(i + 1, max_lookahead):
                        if new_lines[j].startswith('Dialogue:'):
                            next_parts = new_lines[j].split(',', 9)
                            if len(next_parts) >= 10:
                                next_raw = next_parts[9]
                                next_clean = re.sub(r'\{.*?\}', '', next_raw).strip()
                                
                                if next_clean.startswith('...') and j == i + 1:
                                    next_text = next_parts[9]
                                    if next_text.lstrip().startswith('{'):
                                        tag_end = next_text.find('}') + 1
                                        after_tags = next_text[tag_end:]
                                        if after_tags.lstrip().startswith('...'):
                                            cleaned = after_tags.lstrip()[3:].lstrip()
                                            next_parts[9] = next_text[:tag_end] + cleaned
                                    else:
                                        next_parts[9] = re.sub(r'^\.+', '', next_text, count=1)
                                    new_lines[j] = ','.join(next_parts)
                                    break
        i += 1
    return new_lines

class LanguageSelector:
    def __init__(self):
        self.languages = {
            "English": {
                "title": "HS - ooona subtitle fixer",
                "select_file": "No file selected.",
                "browse_button": "Select ASS File",
                "process_button": "START PROCESSING",
                "initial_message": "Please select an ASS file to process.",
                "file_selected": "Selected file:",
                "file_canceled": "File selection canceled.",
                "processing_started": "Processing started...",
                "processing_success": "Processing completed successfully!",
                "processing_failed": "Processing failed.",
                "error_no_file": "ERROR: No file selected.",
                "error_load_failed": "ERROR: Failed to load ASS file.",
                "error_save_failed": "ERROR: Failed to save file.",
                "output_suffix": "-fixed",
                "watermark": "HS",
                "formatting_comment": "-----------Formatting-----------"
            },
            "Magyar": {
                "title": "SárkányokTeaM - ooona felirat javító",
                "select_file": "Nincs fájl kiválasztva.",
                "browse_button": "ASS Fájl Kiválasztása",
                "process_button": "FELDOLGOZÁS INDÍTÁSA",
                "initial_message": "Kérem válasszon ki egy ASS fájlt a feldolgozáshoz.",
                "file_selected": "Kiválasztott fájl:",
                "file_canceled": "Fájl kiválasztása megszakítva.",
                "processing_started": "Feldolgozás elindítva...",
                "processing_success": "Feldolgozás sikeresen befejeződött!",
                "processing_failed": "Feldolgozás sikertelen.",
                "error_no_file": "HIBA: Nincs kiválasztva fájl.",
                "error_load_failed": "HIBA: Nem sikerült betölteni az ASS fájlt.",
                "error_save_failed": "HIBA: Nem sikerült menteni a fájlt.",
                "output_suffix": "-javitott",
                "watermark": "HS",
                "formatting_comment": "-----------Formázás-----------"
            },
            "Deutsch": {
                "title": "SárkányokTeaM - ooona Untertitel-Reparatur",
                "select_file": "Keine Datei ausgewählt.",
                "browse_button": "ASS-Datei auswählen",
                "process_button": "VERARBEITUNG STARTEN",
                "initial_message": "Bitte wählen Sie eine ASS-Datei zur Verarbeitung aus.",
                "file_selected": "Ausgewählte Datei:",
                "file_canceled": "Dateiauswahl abgebrochen.",
                "processing_started": "Verarbeitung gestartet...",
                "processing_success": "Verarbeitung erfolgreich abgeschlossen!",
                "processing_failed": "Verarbeitung fehlgeschlagen.",
                "error_no_file": "FEHLER: Keine Datei ausgewählt.",
                "error_load_failed": "FEHLER: ASS-Datei konnte nicht geladen werden.",
                "error_save_failed": "FEHLER: Datei konnte nicht gespeichert werden.",
                "output_suffix": "-korrigiert",
                "watermark": "HS",
                "formatting_comment": "-----------Formatierung-----------"
            },
            "日本語": {
                "title": "SárkányokTeaM - ooona 字幕修正",
                "select_file": "ファイルが選択されていません。",
                "browse_button": "ASSファイルを選択",
                "process_button": "処理を開始",
                "initial_message": "処理するASSファイルを選択してください。",
                "file_selected": "選択されたファイル:",
                "file_canceled": "ファイル選択がキャンセルされました。",
                "processing_started": "処理を開始しました...",
                "processing_success": "処理が正常に完了しました！",
                "processing_failed": "処理に失敗しました。",
                "error_no_file": "エラー: ファイルが選択されていません。",
                "error_load_failed": "エラー: ASSファイルの読み込みに失敗しました。",
                "error_save_failed": "エラー: ファイルの保存に失敗しました。",
                "output_suffix": "-修正済み",
                "watermark": "HS",
                "formatting_comment": "-----------書式設定-----------"
            }
        }
        self.current_lang = "English"
        self.set_default_language()

    def set_default_language(self):
        try:
            lang_code = None

            if sys.platform == "win32":
                try:
                    windll = ctypes.windll.kernel32
                    # Get user default UI language (preferred by user)
                    lang_id = windll.GetUserDefaultUILanguage()
                    lang_code = locale.windows_locale.get(lang_id, None)
                    if not lang_code:
                        # Fallback to system default UI language
                        lang_id = windll.GetSystemDefaultUILanguage()
                        lang_code = locale.windows_locale.get(lang_id, None)
                except AttributeError:
                    # Fallback if ctypes.windll is not available (e.g., non-Windows)
                    pass

                if lang_code:
                    lang_code = lang_code.split('_')[0].lower()
            else:
                lang_code = os.getenv('LANG') or os.getenv('LC_ALL')
                if lang_code:
                    lang_code = lang_code.split('.')[0].split('_')[0].lower()
            
            if lang_code:
                if lang_code.startswith('hu'):
                    self.current_lang = "Magyar"
                elif lang_code.startswith('de'):
                    self.current_lang = "Deutsch"
                elif lang_code.startswith('ja'):
                    self.current_lang = "日本語"
        except Exception:
            pass

    def get_text(self, key):
        return self.languages.get(self.current_lang, self.languages["English"]).get(key, key)

    def set_language(self, lang):
        if lang in self.languages:
            self.current_lang = lang
        else:
            self.current_lang = "English"

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.lang_selector = LanguageSelector()

        # Impostazioni finestra e tema
        ctk.set_appearance_mode("dark")
        self.configure(fg_color=BG_ROOT)
        self.geometry("550x300")
        self.resizable(False, False)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # Frame superiore (selezione file)
        self.select_frame = ctk.CTkFrame(
            self,
            fg_color=BG_CARD,
            corner_radius=8,
            border_width=1,
            border_color=BORDER
        )
        self.select_frame.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        self.select_frame.grid_columnconfigure(0, weight=1)

        self.path_label = ctk.CTkLabel(
            self.select_frame,
            text="",
            fg_color="transparent",
            anchor="w",
            text_color=TEXT_1,
            font=("Segoe UI", 11)
        )
        self.path_label.grid(row=0, column=0, padx=10, pady=5, sticky="ew")

        self.browse_button = ctk.CTkButton(
            self.select_frame,
            text="",
            command=self.browse_file,
            fg_color=ACCENT,
            hover_color=ACCENT_H,
            text_color="#FFFFFF",
            font=("Segoe UI", 11, "bold"),
            corner_radius=6
        )
        self.browse_button.grid(row=0, column=1, padx=10, pady=5)

        # Pulsante di elaborazione
        self.convert_button = ctk.CTkButton(
            self,
            text="",
            command=self.start_conversion,
            state="disabled",
            fg_color=SUCCESS,
            hover_color=SUCCESS_H,
            text_color="#0B0B12",
            font=("Segoe UI", 13, "bold"),
            corner_radius=8
        )
        self.convert_button.grid(row=1, column=0, padx=20, pady=10, sticky="ew")

        # Area log
        self.log_textbox = ctk.CTkTextbox(
            self,
            height=100,
            fg_color=BG_INPUT,
            text_color=TEXT_1,
            font=("Consolas", 11),
            corner_radius=8,
            border_width=1,
            border_color=BORDER
        )
        self.log_textbox.grid(row=2, column=0, padx=20, pady=(0, 20), sticky="nsew")
        self.log_textbox.configure(state="disabled")

        # Frame per il selettore lingua e watermark
        bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        bottom_frame.grid(row=3, column=0, padx=20, pady=(0, 10), sticky="sw")
        bottom_frame.grid_columnconfigure(1, weight=1)

        self.lang_optionmenu = ctk.CTkOptionMenu(
            bottom_frame,
            values=list(self.lang_selector.languages.keys()),
            command=self.change_language,
            fg_color=BG_INPUT,
            button_color=ACCENT,
            button_hover_color=ACCENT_H,
            text_color=TEXT_1,
            font=("Segoe UI", 11)
        )
        self.lang_optionmenu.set(self.lang_selector.current_lang)
        self.lang_optionmenu.grid(row=0, column=0, padx=0, pady=0)

        # Watermark (posizionato a destra del frame inferiore)
        self.watermark_label = ctk.CTkLabel(
            bottom_frame,
            text=self.lang_selector.get_text("watermark"),
            font=("Segoe UI", 10, "bold"),
            text_color=TEXT_2,
            anchor="e"
        )
        self.watermark_label.grid(row=0, column=1, padx=10, pady=0, sticky="e")

        self.update_gui_texts()
        self.log_message(self.lang_selector.get_text("initial_message"), 'info')

    def update_gui_texts(self):
        self.title(self.lang_selector.get_text("title"))
        self.path_label.configure(text=self.lang_selector.get_text("select_file"))
        self.browse_button.configure(text=self.lang_selector.get_text("browse_button"))
        self.convert_button.configure(text=self.lang_selector.get_text("process_button"))
        self.watermark_label.configure(text=self.lang_selector.get_text("watermark"))

    def change_language(self, new_lang):
        self.lang_selector.set_language(new_lang)
        self.update_gui_texts()
        self.log_textbox.delete("1.0", "end")
        self.log_message(self.lang_selector.get_text("initial_message"), 'info')

    def log_message(self, message, message_type='log'):
        self.log_textbox.configure(state="normal")
        color = "white"
        if message_type == 'info':
            color = "#8fbc8f"
        elif message_type == 'error':
            color = "#ff6347"
        elif message_type == 'success':
            color = "#32cd32"

        self.log_textbox.insert("end", f"{message}\n", (message_type, f"color_tag_{color}"))
        self.log_textbox.tag_config(f"color_tag_{color}", foreground=color)
        self.log_textbox.see("end")
        self.log_textbox.configure(state="disabled")

    def browse_file(self):
        filetypes = [("ASS Files", "*.ass"), ("All Files", "*.*")]
        path = filedialog.askopenfilename(filetypes=filetypes)
        if path:
            self.file_path = path
            self.path_label.configure(text=os.path.basename(path))
            self.convert_button.configure(state="normal")
            self.log_message(f"{self.lang_selector.get_text('file_selected')} {os.path.basename(path)}", 'info')
        else:
            self.log_message(self.lang_selector.get_text("file_canceled"), 'info')

    def start_conversion(self):
        if hasattr(self, 'file_path') and self.file_path:
            self.log_textbox.delete("1.0", "end")
            self.log_message(self.lang_selector.get_text("processing_started"), 'info')
            self.browse_button.configure(state="disabled")
            self.convert_button.configure(state="disabled")
            output_suffix = self.lang_selector.get_text("output_suffix")
            
            result = process_subtitle_file(self.file_path, self.log_message, output_suffix, self)

            self.browse_button.configure(state="normal")
            self.convert_button.configure(state="normal")

            if result:
                self.log_message(self.lang_selector.get_text("processing_success"), 'success')
            else:
                self.log_message(self.lang_selector.get_text("processing_failed"), 'error')
        else:
            self.log_message(self.lang_selector.get_text("error_no_file"), 'error')

if __name__ == "__main__":
    app = App()
    app.mainloop()