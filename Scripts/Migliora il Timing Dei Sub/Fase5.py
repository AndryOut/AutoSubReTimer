import pysrt
import os

project_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# Funzione per leggere un file .ass
def read_ass_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.readlines()

# Funzione per scrivere un file .ass
def write_ass_file(header, dialogue, format_line, file_path):
    with open(file_path, 'w', encoding='utf-8') as file:
        file.writelines(header + [format_line] + dialogue)

# Funzione per aggiornare i time stamps in Dialoghi.ass
def update_ass_timestamps(ass_file, srt_file, output_file):
    # Legge il file .ass
    lines = read_ass_file(ass_file)
    header_section = []
    dialogue_section = []
    capture_dialogue = False
    format_line = ""

    for line in lines:
        if line.startswith('[Events]'):
            capture_dialogue = True
            header_section.append(line)
            continue
        if capture_dialogue and line.startswith('Dialogue:'):
            dialogue_section.append(line)
        elif not capture_dialogue:
            header_section.append(line)
        if capture_dialogue and line.startswith('Format:'):
            format_line = line

    # Legge il file Final.srt
    subs = pysrt.open(srt_file, encoding='utf-8')

    # Controllo corrispondenza righe tra .ass e .srt
    if len(dialogue_section) != len(subs):
        print("Error: The number of lines in 'Dialoghi.ass' does not match the number in 'Final.srt'.")
        return

    # Aggiorna i time stamps nei dialoghi del file .ass
    updated_dialogue = []
    for idx, line in enumerate(dialogue_section):
        start_time = subs[idx].start.to_time()
        end_time = subs[idx].end.to_time()

        # Formatta i nuovi time stamps per il formato ASS
        formatted_start = f"{start_time.hour}:{start_time.minute:02}:{start_time.second:02}.{int(start_time.microsecond / 10000):02}"
        formatted_end = f"{end_time.hour}:{end_time.minute:02}:{end_time.second:02}.{int(end_time.microsecond / 10000):02}"

        # Sostituisce i time stamps nel dialogo
        parts = line.split(',', maxsplit=9)
        parts[1] = formatted_start
        parts[2] = formatted_end
        updated_dialogue.append(','.join(parts))

    # Scrive il file aggiornato
    write_ass_file(header_section, updated_dialogue, format_line, output_file)
    print(f"The timestamps have been updated and the file has been saved to: {output_file}")

# Funzione principale
def main():
    # Specifica i percorsi relativi dei file di input e output
    ass_file = os.path.join(project_path, "Dialoghi.ass")
    srt_file = os.path.join(project_path, "Final.srt")
    output_file = os.path.join(project_path, "Final.ass")

    # Controlla se il file Dialoghi.ass esiste
    if not os.path.exists(ass_file):
        print("Fase5.py skipped")
        return

    print(f"Using files from the project directory: {project_path}")
    print(f"Ass File: {ass_file}")
    print(f"SRT File: {srt_file}")
    print(f"Output file: {output_file}")

    # Aggiorna i time stamps
    update_ass_timestamps(ass_file, srt_file, output_file)

if __name__ == "__main__":
    main()
