import pysrt
import os

def milliseconds_to_subrip_time(milliseconds):
    hours = int(milliseconds // 3600000)
    minutes = int((milliseconds % 3600000) // 60000)
    seconds = int((milliseconds % 60000) // 1000)
    milliseconds = int(milliseconds % 1000)
    return pysrt.SubRipTime(hours=hours, minutes=minutes, seconds=seconds, milliseconds=milliseconds)

def adjust_close_subtitles(srt_file, threshold_ms=150):
    subs = pysrt.open(srt_file, encoding='utf-8')
    
    # Itera attraverso tutti i sottotitoli
    for i in range(len(subs) - 1):
        current_sub = subs[i]
        next_sub = subs[i + 1]
        
        current_end_ms = current_sub.end.ordinal
        next_start_ms = next_sub.start.ordinal
        gap = next_start_ms - current_end_ms
        
        if 0 < gap <= threshold_ms:
            # Imposta il fine corrente uguale all'inizio del successivo
            current_sub.end = next_sub.start
    
    return subs

def main():
    project_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    srt_file = os.path.join(project_path, "Sub.srt")
    output_file = os.path.join(project_path, "adjusted_Sub.srt")
    
    THRESHOLD_MS = 150
    
    try:
        adjusted_subs = adjust_close_subtitles(srt_file, THRESHOLD_MS)
        
        adjusted_subs.save(output_file, encoding='utf-8')
        
        print(f"SRT file processed successfully!")
        
    except FileNotFoundError:
        print(f"Error: File not found - {srt_file}")
        raise
    except Exception as e:
        print(f"Error during processing: {str(e)}")
        raise

if __name__ == "__main__":
    main()