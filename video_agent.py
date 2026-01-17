import os
import json
import sys
from typing import Dict
from moviepy import ImageClip, AudioFileClip, concatenate_videoclips
import moviepy.video.fx as vfx

class VideoAgent:
    def __init__(self):
        self.base_dir = "output"
        self.fps = 24
        self.width = 1080
        self.height = 1920

    def create_video(self, reel_name: str, script_json: Dict):
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

        clips = []
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
                # Video Clip Creation
                clip = ImageClip(img_path).with_duration(duration)

                # Resize to fill vertical 1080x1920 (aspect-ratio preserved)
                clip = clip.resized(height=self.height)
                if clip.w < self.width:
                    clip = clip.resized(width=self.width)

                # Center Crop to exact 1080x1920
                x1 = (clip.w - self.width) / 2
                y1 = (clip.h - self.height) / 2
                clip = clip.cropped(
                    x1=max(0, x1),
                    y1=max(0, y1),
                    width=self.width,
                    height=self.height
                )

                # Audio Integration
                audio = AudioFileClip(aud_path)
                if audio.duration > duration:
                    audio = audio.with_duration(duration)
                clip = clip.with_audio(audio)

                # Fade Transitions
                clip = clip.with_effects([vfx.FadeIn(0.5), vfx.FadeOut(0.5)])

                clips.append(clip)
            except Exception as e:
                print(f"Graceful handle: Exception for scene {num}: {e}")

        if not clips:
            raise RuntimeError("No valid clips were generated.")

        # Final Assembly
        final = concatenate_videoclips(clips, method="compose")
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
    if len(sys.argv) < 3:
        print("Usage: python video_agent.py <reel_name> <path_to_script_json>")
        sys.exit(1)

    reel = sys.argv[1]
    script_path = sys.argv[2]

    try:
        with open(script_path, 'r') as f:
            script_data = json.load(f)

        agent = VideoAgent()
        output = agent.create_video(reel, script_data)
        print(f"Video created successfully: {output}")
    except Exception as error:
        print(f"Error: {error}")
        sys.exit(1)
