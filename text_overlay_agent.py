import json
import os
import math
from typing import List, Dict, Tuple
from moviepy import TextClip, ColorClip, VideoClip

class TextOverlayAgent:
    def __init__(self):
        # Design specifications
        self.font = os.path.join(os.path.dirname(__file__), "fonts", "Montserrat-Bold.ttf")
        self.font_size = 65
        self.normal_color = "#FFFFFF"  # Pure white
        self.highlight_color = "#FFD700"  # Gold
        self.stroke_color = "#000000"
        self.stroke_width = 3
        
        # Frame specifications
        self.video_width = 1080
        self.video_height = 1920
        self.bottom_offset = 280 # Pixels from bottom for text area
        
        # Layout specifications
        self.word_spacing = 15
        self.line_spacing = 80
        self.max_line_width = 900
        self.max_words_per_line = 3

    def load_speech_marks(self, json_path: str) -> list:
        """
        Load and parse speech marks JSON.
        Polly returns newline-delimited JSON objects.
        """
        if not os.path.exists(json_path):
            print(f"Warning: Speech marks file not found at {json_path}")
            return []
            
        speech_marks = []
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        speech_marks.append(json.loads(line))
        except Exception as e:
            print(f"Error loading speech marks from {json_path}: {e}")
        return speech_marks

    def create_background_bar(self, duration: float, video_size: tuple) -> VideoClip:
        """Create semi-transparent background bar for text"""
        width, height = video_size
        bar = ColorClip(
            size=(width, self.bg_height),
            color=self.bg_color
        ).with_duration(duration).with_opacity(self.bg_opacity)
        
        # Position at the bottom area where text will be
        # bar_y is the top-left Y coordinate
        bar_y = height - self.bottom_offset - (self.bg_height / 2)
        return bar.with_position(('center', bar_y))

    def create_karaoke_clips(self, 
                            narration: str, 
                            speech_marks: list, 
                            scene_start_time: float,
                            video_size: tuple = (1080, 1920)) -> list:
        """
        Generate list of TextClip objects with karaoke highlighting
        
        Returns: List of MoviePy TextClip objects with proper timing
        """
        if not speech_marks:
            return []

        # Filter for 'word' type marks
        word_marks = [m for m in speech_marks if m.get("type") == "word"]
        if not word_marks:
            return []

        # Group words into lines based on word count and max width
        lines = []
        current_line = []
        current_width = 0
        
        # Use Montserrat-Bold from the local repo fonts directory
        active_font = self.font
        
        for mark in word_marks:
            word_text = mark["value"]
            # Estimate width to decide on line breaks
            # Using 0.8 factor to be more conservative and prevent side clipping
            estimated_w = len(word_text) * (self.font_size * 0.8)
            
            if len(current_line) >= self.max_words_per_line or (current_width + estimated_w > self.max_line_width and current_line):
                lines.append(current_line)
                current_line = [mark]
                current_width = estimated_w
            else:
                current_line.append(mark)
                current_width += estimated_w + self.word_spacing
        
        if current_line:
            lines.append(current_line)

        all_clips = []
        v_width, v_height = video_size
        
        # Calculate total Y height to center the block
        total_text_height = len(lines) * self.line_spacing
        start_y = v_height - self.bottom_offset - (total_text_height / 2)

        for line_idx, line in enumerate(lines):
            text_y_pos = start_y + (line_idx * self.line_spacing)
            
            line_start_abs = line[0]["time"] / 1000.0
            if line_idx < len(lines) - 1:
                line_end_abs = lines[line_idx+1][0]["time"] / 1000.0
            else:
                line_end_abs = (line[-1]["time"] / 1000.0) + 0.8
            
            line_duration = max(0.2, line_end_abs - line_start_abs)
            line_start_rel = max(0, line_start_abs + scene_start_time)

            # 1. Create the static Base line (White) and Highlight Template (Gold)
            words_in_line = [m["value"] for m in line]
            full_line_text = " ".join(words_in_line)
            
            try:
                # White Base Line with safety margin to prevent stroke clipping
                base_line_clip = TextClip(
                    text=full_line_text,
                    font=active_font,
                    font_size=self.font_size,
                    color=self.normal_color,
                    stroke_color=self.stroke_color,
                    stroke_width=self.stroke_width,
                    method='label',
                    margin=(20, 20)
                ).with_start(line_start_rel).with_duration(line_duration).with_position(('center', text_y_pos))
                
                line_w, line_h = base_line_clip.size
                all_clips.append(base_line_clip)
                
                # Gold Highlight Template with identical safety margin
                highlight_template = TextClip(
                    text=full_line_text,
                    font=active_font,
                    font_size=self.font_size,
                    color=self.highlight_color,
                    stroke_color=self.stroke_color,
                    stroke_width=self.stroke_width,
                    method='label',
                    margin=(20, 20)
                )
                
                line_x_start = (v_width - line_w) / 2
                char_ptr = 0
                
                for i, mark in enumerate(line):
                    word_val = mark["value"]
                    
                    # Calculate exact boundaries of the word within the full_line_text
                    start_idx = char_ptr
                    end_idx = char_ptr + len(word_val)
                    
                    # Measure the prefix width within the context of the line
                    p1_text = full_line_text[:start_idx]
                    p2_text = full_line_text[:end_idx]
                    
                    x1 = 0
                    if p1_text:
                        # Measure the prefix with safety margin
                        m1 = TextClip(text=p1_text, font=active_font, font_size=self.font_size, 
                                     method='label', stroke_color=self.stroke_color, stroke_width=self.stroke_width, margin=(20, 20))
                        x1 = m1.size[0] - 20 # Subtract one side of the margin to get the starting x of the next word
                    
                    m2 = TextClip(text=p2_text, font=active_font, font_size=self.font_size, 
                                 method='label', stroke_color=self.stroke_color, stroke_width=self.stroke_width, margin=(20, 20))
                    x2 = m2.size[0] - 20
                    
                    # CROP: Take a slice of the GOLD line template. 
                    # Width is adjusted by the margins
                    word_highlight = highlight_template.cropped(x1=x1, y1=0, width=x2-x1, height=line_h)
                    
                    # Timing
                    word_start_rel = (mark["time"] / 1000.0) + scene_start_time
                    if i < len(line) - 1:
                        word_end_rel = (line[i+1]["time"] / 1000.0) + scene_start_time
                    else:
                        word_end_rel = line_start_rel + line_duration
                    
                    word_duration = max(0.1, word_end_rel - word_start_rel)
                    
                    # Position: Anchor to the same line_x_start and line_y_pos as the white line
                    word_pos = (line_x_start + x1, text_y_pos)
                    
                    final_clip = word_highlight.with_start(word_start_rel).with_duration(word_duration).with_position(word_pos)
                    all_clips.append(final_clip)
                    
                    # Move pointer to next word (account for space)
                    char_ptr += len(word_val) + 1
                    
            except Exception as e:
                print(f"Error creating line-based clips: {e}")
                continue
                
        return all_clips

if __name__ == "__main__":
    # Example usage / testing
    agent = TextOverlayAgent()
    print("TextOverlayAgent initialized.")
    # test_marks = agent.load_speech_marks("path/to/marks.json")
    # clips = agent.create_karaoke_clips("Hello world", test_marks, 0)
