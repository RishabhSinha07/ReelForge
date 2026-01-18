import os
import json
import sys
from typing import Dict
from moviepy import ImageClip, AudioFileClip, concatenate_videoclips, CompositeVideoClip
import moviepy.video.fx as vfx
from text_overlay_agent import TextOverlayAgent

class VideoAgent:
    def __init__(self):
        self.base_dir = "output"
        self.fps = 24
        self.width = 1080
        self.height = 1920

    def create_video(self, reel_name: str, script_json: Dict, mode: str = "story"):
        scenes = script_json.get("scenes", [])
        reel_path = os.path.join(self.base_dir, reel_name)
        image_dir = os.path.join(reel_path, "images")
        audio_dir = os.path.join(reel_path, "audio")
        output_file = os.path.join(reel_path, f"{reel_name}.mp4")

        if not os.path.exists(reel_path):
            os.makedirs(reel_path, exist_ok=True)

        # Validation: Check image and audio folder existence
        if not os.path.exists(image_dir) or not os.path.exists(audio_dir):
            raise FileNotFoundError(f"Required directories missing: {image_dir} or {audio_dir}")

        image_files = [f for f in os.listdir(image_dir) if f.endswith(('.png', '.jpg'))]
        audio_files = [f for f in os.listdir(audio_dir) if f.endswith('.mp3')]

        # Validation: Number of scenes matches images and audio
        if len(image_files) != len(scenes):
            raise ValueError(f"Validation Mismatch: Found {len(image_files)} images for {len(scenes)} scenes.")
        if len(audio_files) != len(scenes):
            raise ValueError(f"Validation Mismatch: Found {len(audio_files)} audio files for {len(scenes)} scenes.")

        # News mode uses even simpler transitions if needed, but 0.3s crossfade is professional
        overlap = 0.1 if mode == "news" else 0.3  
        clips = []
        
        # Text Overlay Setup
        text_overlay_agent = TextOverlayAgent()
        all_text_clips = []
        current_time = 0.0
        for scene in scenes:
            num = scene.get("scene_number")
            duration = scene.get("duration_seconds")
            img_path = os.path.join(image_dir, f"scene_{num}.png")
            aud_path = os.path.join(audio_dir, f"scene_{num}.mp3")

            # Validate: All image and audio files exist for each scene
            if not os.path.exists(img_path):
                print(f"Error: Missing image for scene {num}")
                continue
            if not os.path.exists(aud_path):
                print(f"Error: Missing audio for scene {num}")
                continue

            try:
                # Audio Integration
                audio = AudioFileClip(aud_path)
                audio_duration = audio.duration

                if audio_duration <= 0:
                    audio_duration = duration

                # Video Clip Creation - extend duration by 'overlap' for the transition
                clip = ImageClip(img_path).with_duration(audio_duration + overlap)

                # Resize to fill vertical 1080x1920
                clip = clip.resized(height=self.height)
                if clip.w < self.width:
                    clip = clip.resized(width=self.width)

                # Center Crop
                x1 = (clip.w - self.width) / 2
                y1 = (clip.h - self.height) / 2
                clip = clip.cropped(x1=max(0, x1), y1=max(0, y1), width=self.width, height=self.height)

                # Attach Audio
                clip = clip.with_audio(audio)

                # Text Overlay Integration
                speech_marks_path = f"{aud_path}_speechmarks.json"
                if os.path.exists(speech_marks_path):
                    speech_marks = text_overlay_agent.load_speech_marks(speech_marks_path)
                    scene_text_clips = text_overlay_agent.create_karaoke_clips(
                        narration=scene.get("voice_line", ""),
                        speech_marks=speech_marks,
                        scene_start_time=current_time
                    )
                    all_text_clips.extend(scene_text_clips)

                clips.append(clip)
                current_time += audio_duration
            except Exception as e:
                print(f"Graceful handle: Exception for scene {num}: {e}")

        if not clips:
            raise RuntimeError("No valid clips were generated.")

        # Final Assembly with Crossfade and Text Overlays
        video_clip = concatenate_videoclips(clips, method="compose", padding=-overlap)
        final = CompositeVideoClip([video_clip] + all_text_clips)
        final.write_videofile(
            output_file,
            fps=self.fps,
            codec="libx264",
            audio_codec="aac"
        )

        # Cleanup
        for c in clips:
            c.close()

        return output_file

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Assemble Video from scenes")
    parser.add_argument("name", help="Reel name")
    parser.add_argument("script", help="Path to script.json")
    parser.add_argument("--mode", default="story", help="story or news")
    
    args = parser.parse_args()

    try:
        with open(args.script, 'r') as f:
            script_data = json.load(f)

        agent = VideoAgent()
        output = agent.create_video(args.name, script_data, mode=args.mode)
        print(f"Video created successfully: {output}")
    except Exception as error:
        print(f"Error: {error}")
        sys.exit(1)
