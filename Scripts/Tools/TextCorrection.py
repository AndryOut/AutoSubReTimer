import os
import re
import sys
import json
import tkinter as tk
from tkinter import filedialog
from pathlib import Path

def get_output_dir(input_file):
    # 1. Preferenza GUI (gui_config.json in Scripts/GUI/, due cartelle sopra Tools/)
    gui_config_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "GUI", "gui_config.json"
    )
    try:
        with open(gui_config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        out = cfg.get("output_dir")
        if out and os.path.isdir(out):
            return os.path.abspath(out)
    except (OSError, json.JSONDecodeError):
        pass

    # 2. Cartella del file di input scelto dall'utente
    if input_file:
        d = os.path.dirname(os.path.abspath(input_file))
        if os.path.isdir(d):
            return d

    # 3. Fallback: Desktop
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes

            class GUID(ctypes.Structure):
                _fields_ = [("Data1", wintypes.DWORD), ("Data2", wintypes.WORD),
                            ("Data3", wintypes.WORD), ("Data4", ctypes.c_ubyte * 8)]

            folderid_desktop = GUID(0xB4BFCC3A, 0xDB2C, 0x424C,
                                    (ctypes.c_ubyte * 8)(0xB0, 0x29, 0x7F, 0xE9, 0x9A, 0x87, 0xC6, 0x41))
            p = ctypes.c_wchar_p()
            if ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(folderid_desktop), 0, None,
                                                          ctypes.byref(p)) == 0:
                path = p.value
                ctypes.windll.ole32.CoTaskMemFree(p)
                if path and os.path.isdir(path):
                    return path
        except Exception:
            pass
    path = os.path.join(os.path.expanduser("~"), "Desktop")
    return path if os.path.isdir(path) else None

def remove_tags(text):
    return re.sub(r'\{.*?\}', '', text)

# Calcola la lunghezza del testo visibile (escludendo tag)
def get_visible_length(text):
    return len(remove_tags(text))

def capitalize_hyphenated(text):
    def process_match(match):
        first_char = match.group(1)
        remaining = match.group(2)
        
        # Processa tutti i trattini
        parts = remaining.split('-')
        processed = []
        for part in parts:
            if part and part[0].lower() == first_char.lower():
                processed.append(part[0].upper() + part[1:])
            else:
                processed.append(part)
        
        return first_char + '-'.join(processed)

    # Cerca lettera maiuscola seguita da trattino+lettera
    pattern = r'([A-Z])(-[a-z][^-\s]*)'
    while re.search(pattern, text):
        new_text = re.sub(pattern, process_match, text)
        if new_text == text:  # es. "E-mail": niente da cambiare, evita il ciclo infinito
            break
        text = new_text
    return text

# Corregge i puntini di sospensione tra le righe
def fix_puntini(lines):
    new_lines = lines.copy()
    i = 0
    
    while i < len(new_lines):
        if new_lines[i].startswith('Dialogue:'):
            parts = new_lines[i].split(',', 9)
            if len(parts) >= 10:
                # Rimuove TUTTI i tag tra graffe per l'analisi (ma li mantiene nel file)
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
                                    # Rimuove SOLO i puntini INIZIALI (senza toccare tag)
                                    next_text = next_parts[9]
                                    # Gestione speciale per puntini tra tag (es: {\i1}...text)
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

def update_header_and_styles(content):
    styles_pos = content.find('[V4+ Styles]')
    if styles_pos == -1:
        return content  # Se non trova la sezione, restituisce il contenuto originale
    
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
        # Aggiunge lo stile Default dopo l'ultimo stile esistente
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
                # Inserisce lo stile Default prima della prossima sezione
                if last_style_pos != -1:
                    new_lines.insert(last_style_pos + 1, default_style)
            
            if in_styles and line.strip().startswith('Style:'):
                last_style_pos = len(new_lines)
            
            new_lines.append(line)
        
        if in_styles and last_style_pos != -1:
            new_lines.insert(last_style_pos + 1, default_style)
        
        return '\n'.join(new_lines)

def process_text(text):
    # Controlla se il testo SENZA TAG inizia con un trattino
    clean_text_no_tags = remove_tags(text).strip()
    
    # Se inizia con "-", mantiene gli \N e applica solo capitalize_hyphenated
    if clean_text_no_tags.startswith('-'):
        return capitalize_hyphenated(text)
    else:
        # Calcola lunghezza (senza tag e senza \N) solo per le altre righe
        unbroken_text = re.sub(r'\\N', ' ', text).strip()
        unbroken_text = re.sub(r'\s+', ' ', unbroken_text)
        visible_length = get_visible_length(unbroken_text)
        
        # Applica la trasformazione in entrambi i casi
        if visible_length <= 47:
            return capitalize_hyphenated(unbroken_text)
        else:
            return capitalize_hyphenated(text)

def process_ass_file(input_path, output_path):
    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    content = update_header_and_styles(content)
    lines = content.splitlines(keepends=True)
    lines = fix_puntini(lines)  # Applica la correzione dei puntini
    processed_lines = []
    
    for line in lines:
        if line.startswith('Dialogue:'):
            parts = line.split(',', 9)
            if len(parts) < 10:
                processed_lines.append(line)
                continue
            
            text = parts[9].rstrip('\r\n')
            processed_text = process_text(text)
            parts[9] = processed_text
            processed_line = ','.join(parts)
            
            # Mantiene i terminatori di riga originali
            if line.endswith('\r\n'):
                processed_line += '\r\n'
            elif line.endswith('\n'):
                processed_line += '\n'
                
            processed_lines.append(processed_line)
        else:
            processed_lines.append(line)
    
    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        f.writelines(processed_lines)

def main():
    try:
        root = tk.Tk()
        root.withdraw()
        
        input_file = filedialog.askopenfilename(
            title="Select your .ass file",
            filetypes=[("ASS Files", "*.ass"), ("All Files", "*.*")]
        )
        
        if not input_file:
            print("No file selected. Operation cancelled.")
            return
        
        output_dir = get_output_dir(input_file)
        if output_dir is None:
            print("Error: output folder unreachable, unable to save the file.")
            return
        output_file = os.path.join(output_dir, "processed.ass")
        
        process_ass_file(input_file, output_file)

    except UnicodeDecodeError:
        print("Error: the subtitle file is not UTF-8 encoded. "
              "Open it (e.g. in Aegisub or Notepad), save it as UTF-8 and try again.")
        sys.exit(1)
    except Exception as e:
        print(f"Error during execution: {str(e)}")

if __name__ == "__main__":
    main()