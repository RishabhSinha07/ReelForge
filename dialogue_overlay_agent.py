import json
import os
from typing import List, Dict, Tuple
from moviepy import TextClip, ColorClip, VideoClip
from text_overlay_agent import TextOverlayAgent

class DialogueOverlayAgent(TextOverlayAgent):
    """
    Extends TextOverlayAgent to add character dialogue overlays.

    Creates:
    - Character name badge (static, gold, top)
    - Karaoke-style dialogue (below name, reuses parent class logic)
    """

    def __init__(self):
        super().__init__()

        # Character name badge styling
        self.name_font_size = 32  # Smaller, less obtrusive
        self.name_color = "#FFD700"  # Gold
        self.name_bg_color = (0, 0, 0)  # Black
        self.name_bg_opacity = 0.6  # More transparent
        self.name_y_position = 1650  # Pixels from top (near bottom)

        # Adjust dialogue position to be below name badge
        self.dialogue_y_offset = 1750  # Below character name

    def create_dialogue_overlay_clips(
        self,
        character_name: str,
        dialogue: str,
        speech_marks_path: str,
        scene_start_time: float,
        scene_duration: float,
        video_size: tuple = (1080, 1920)
    ) -> List[VideoClip]:
        """
        Create complete dialogue overlay with character name and karaoke.

        Args:
            character_name: Character name to display
            dialogue: Dialogue text
            speech_marks_path: Path to speech marks JSON
            scene_start_time: Start time of scene in final video
            scene_duration: Duration of the scene
            video_size: Video dimensions

        Returns:
            List of clips (name badge + karaoke dialogue)
        """
        all_clips = []

        # 1. Character name badge - DISABLED by user request
        # (Skipping character name display)

        # 2. Load speech marks
        speech_marks = self.load_speech_marks(speech_marks_path)

        if not speech_marks:
            # Fallback: static dialogue text if no speech marks
            static_dialogue = self._create_static_dialogue(
                dialogue,
                scene_start_time,
                scene_duration,
                video_size
            )
            if static_dialogue:
                all_clips.append(static_dialogue)
        else:
            # 3. Create karaoke dialogue (reuse parent class method)
            karaoke_clips = self._create_dialogue_karaoke(
                dialogue,
                speech_marks,
                scene_start_time,
                video_size
            )
            all_clips.extend(karaoke_clips)

        return all_clips

    def _create_character_name_badge(
        self,
        character_name: str,
        start_time: float,
        duration: float,
        video_size: tuple
    ) -> VideoClip:
        """
        Create character name badge with semi-transparent background.

        Args:
            character_name: Character name
            start_time: Start time in video
            duration: Duration to display
            video_size: Video dimensions

        Returns:
            Composite clip with background and text
        """
        try:
            # Create text clip
            name_text = TextClip(
                text=character_name.upper(),
                font=self.font,
                font_size=self.name_font_size,
                color=self.name_color,
                stroke_color=self.stroke_color,
                stroke_width=2,
                method='label',
                margin=(15, 8)
            ).with_duration(duration).with_start(start_time)

            text_w, text_h = name_text.size

            # Create semi-transparent background
            bg_padding = 10
            bg = ColorClip(
                size=(text_w + 2 * bg_padding, text_h + 2 * bg_padding),
                color=self.name_bg_color
            ).with_duration(duration).with_opacity(self.name_bg_opacity).with_start(start_time)

            # Position background
            bg = bg.with_position(('center', self.name_y_position))

            # Position text on top of background
            name_text = name_text.with_position(('center', self.name_y_position + bg_padding))

            # Return both clips (will be composited)
            # Note: Return as list so caller can add to all_clips
            return [bg, name_text]

        except Exception as e:
            print(f"    Warning: Could not create character name badge: {e}")
            return None

    def _create_dialogue_karaoke(
        self,
        dialogue: str,
        speech_marks: list,
        scene_start_time: float,
        video_size: tuple
    ) -> List[VideoClip]:
        """
        Create karaoke-style dialogue clips.

        Args:
            dialogue: Dialogue text
            speech_marks: Speech marks data
            scene_start_time: Start time in video
            video_size: Video dimensions

        Returns:
            List of karaoke clips
        """
        # Temporarily adjust bottom_offset for dialogue positioning
        original_offset = self.bottom_offset
        self.bottom_offset = video_size[1] - self.dialogue_y_offset

        # Use parent class karaoke method
        karaoke_clips = self.create_karaoke_clips(
            narration=dialogue,
            speech_marks=speech_marks,
            scene_start_time=scene_start_time,
            video_size=video_size
        )

        # Restore original offset
        self.bottom_offset = original_offset

        return karaoke_clips

    def _create_static_dialogue(
        self,
        dialogue: str,
        start_time: float,
        duration: float,
        video_size: tuple
    ) -> VideoClip:
        """
        Create static dialogue text (fallback when no speech marks).

        Args:
            dialogue: Dialogue text
            start_time: Start time in video
            duration: Duration to display
            video_size: Video dimensions

        Returns:
            Text clip
        """
        try:
            text_clip = TextClip(
                text=dialogue,
                font=self.font,
                font_size=self.font_size,
                color=self.normal_color,
                stroke_color=self.stroke_color,
                stroke_width=self.stroke_width,
                method='caption',
                size=(self.max_line_width, None),
                align='center'
            ).with_duration(duration).with_start(start_time).with_position(('center', self.dialogue_y_offset))

            return text_clip

        except Exception as e:
            print(f"    Warning: Could not create static dialogue: {e}")
            return None

    def create_dialogue_overlays_for_scenes(
        self,
        parsed_script: Dict,
        audio_data: List[Dict],
        scene_start_times: List[float],
        video_size: tuple = (1080, 1920)
    ) -> List[VideoClip]:
        """
        Create dialogue overlays for all scenes.

        Args:
            parsed_script: Parsed script with scenes
            audio_data: List of audio data dicts from VoiceAgent
            scene_start_times: List of cumulative start times for each scene
            video_size: Video dimensions

        Returns:
            List of all dialogue overlay clips
        """
        all_dialogue_clips = []

        scenes = parsed_script.get("scenes", [])

        print(f"\n=== Creating dialogue overlays for {len(scenes)} scenes ===")

        for idx, (scene, audio_dict) in enumerate(zip(scenes, audio_data)):
            scene_num = scene.get("scene_number")
            character_name = audio_dict.get("character", "NARRATOR")
            dialogue = scene.get("dialogue", "")
            speech_marks_path = audio_dict.get("speech_marks_path", "")

            if not dialogue:
                print(f"\nScene {scene_num}: No dialogue, skipping")
                continue

            start_time = scene_start_times[idx]

            # Estimate duration from scene or audio
            duration = scene.get("duration_seconds", 6.0)

            print(f"\nScene {scene_num}: {character_name}")
            print(f"  Start time: {start_time:.2f}s")
            print(f"  Duration: {duration:.2f}s")

            try:
                clips = self.create_dialogue_overlay_clips(
                    character_name=character_name,
                    dialogue=dialogue,
                    speech_marks_path=speech_marks_path,
                    scene_start_time=start_time,
                    scene_duration=duration,
                    video_size=video_size
                )

                # Flatten list (name badge returns list of [bg, text])
                for clip in clips:
                    if isinstance(clip, list):
                        all_dialogue_clips.extend(clip)
                    else:
                        all_dialogue_clips.append(clip)

                print(f"  ✓ {len(clips)} dialogue clips created")

            except Exception as e:
                print(f"  ✗ Error: {e}")

        return all_dialogue_clips

if __name__ == "__main__":
    print("=== Dialogue Overlay Agent Test ===")

    # Test with example data
    test_parsed_script = {
        "scenes": [
            {
                "scene_number": 1,
                "characters": ["ROBO-7"],
                "dialogue": "Where am I?",
                "duration_seconds": 4.0
            }
        ]
    }

    test_audio_data = [
        {
            "character": "ROBO-7",
            "audio_path": "output/test_robot_journey/audio/scene_1_ROBO_7.mp3",
            "speech_marks_path": "output/test_robot_journey/audio/scene_1_ROBO_7_speechmarks.json"
        }
    ]

    test_start_times = [0.0]

    agent = DialogueOverlayAgent()

    try:
        clips = agent.create_dialogue_overlays_for_scenes(
            test_parsed_script,
            test_audio_data,
            test_start_times
        )

        print(f"\n✓ Created {len(clips)} dialogue overlay clips")

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        print("\nNote: Requires audio files to be generated first")
