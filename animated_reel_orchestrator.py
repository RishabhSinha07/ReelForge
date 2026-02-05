"""
Animated Reel Orchestrator

Coordinates the 7-agent pipeline to transform scripts into animated video reels:
1. ScriptParser → Parse plain text script with scene markers
2. CharacterDesigner → Generate character reference images
3. Planner → Create video-optimized scene plans
4. AnimatedVisual → Generate 6-second video clips (Nova Reel)
5. EnhancedVoice → Generate audio with character voices + visemes
6. AnimationCompositor → Stitch video clips with audio sync
7. DialogueOverlay → Add character name badges + karaoke dialogue

Usage:
    python animated_reel_orchestrator.py <script_file> <reel_name> [--theme <theme>]
"""

import os
import sys
import json
import argparse
from typing import Dict, List
from moviepy import VideoFileClip, CompositeVideoClip

from script_parser_agent import ScriptParserAgent
from character_designer_agent import CharacterDesignerAgent
from planner_agent import generate_video_plan
from animated_visual_agent import AnimatedVisualAgent
from voice_agent import VoiceAgent
from animation_compositor_agent import AnimationCompositorAgent
from dialogue_overlay_agent import DialogueOverlayAgent


class AnimatedReelOrchestrator:
    """
    Main orchestrator for animated reel generation.
    """

    def __init__(self):
        self.base_output_dir = "output"

    def orchestrate_animated_reel(
        self,
        script_text: str,
        reel_name: str,
        theme: str = "Cinematic",
        mode: str = "story"
    ) -> str:
        """
        Full pipeline: script → animated reel with dialogue overlays.

        Args:
            script_text: Plain text script with scene markers
            reel_name: Name for organizing outputs
            theme: Visual theme (Cinematic, Cartoon, etc.)
            mode: "story" or "news"

        Returns:
            Path to final animated reel MP4
        """
        print("=" * 80)
        print("ANIMATED REEL ORCHESTRATOR")
        print("=" * 80)
        print(f"\nReel Name: {reel_name}")
        print(f"Theme: {theme}")
        print(f"Mode: {mode}\n")

        try:
            # Stage 1: Parse Script
            print("\n" + "=" * 80)
            print("STAGE 1/7: SCRIPT PARSING")
            print("=" * 80)

            script_parser = ScriptParserAgent()

            if not script_parser.validate_script_format(script_text):
                raise ValueError("Script format validation failed. Check TITLE, THEME, CHARACTERS, and SCENE sections.")

            parsed_script = script_parser.parse_script(script_text, reel_name)

            print(f"\n✓ Script parsed: {parsed_script['title']}")
            print(f"  Characters: {len(parsed_script['characters'])}")
            print(f"  Scenes: {len(parsed_script['scenes'])}")
            print(f"  Total duration: {parsed_script['total_duration']}s")

            # Stage 2: Design Characters
            print("\n" + "=" * 80)
            print("STAGE 2/7: CHARACTER DESIGN")
            print("=" * 80)

            character_designer = CharacterDesignerAgent()
            character_bibles = character_designer.design_characters(
                characters=parsed_script["characters"],
                theme=theme,
                reel_name=reel_name
            )

            print(f"\n✓ Characters designed: {len(character_bibles['characters'])}")

            # Stage 3: Plan Video Scenes
            print("\n" + "=" * 80)
            print("STAGE 3/7: VIDEO PLANNING")
            print("=" * 80)

            video_plan = generate_video_plan(
                parsed_script=parsed_script,
                character_bibles=character_bibles,
                theme=theme,
                reel_name=reel_name
            )

            print(f"\n✓ Video plan created: {len(video_plan['scenes'])} scenes")

            # Stage 4: Generate Animated Video Clips
            print("\n" + "=" * 80)
            print("STAGE 4/7: ANIMATED VIDEO GENERATION (Nova Reel)")
            print("=" * 80)
            print("\n⚠️  WARNING: Each video takes 14-17 minutes to generate!")
            print(f"   Total estimated time: {len(video_plan['scenes']) * 15} minutes\n")

            animated_visual = AnimatedVisualAgent()
            scene_videos = animated_visual.generate_scene_videos(
                video_plan=video_plan,
                character_bibles=character_bibles,
                reel_name=reel_name
            )

            print(f"\n✓ Videos generated: {len(scene_videos)} clips")

            # Stage 5: Generate Character Audio + Visemes
            print("\n" + "=" * 80)
            print("STAGE 5/7: CHARACTER VOICE SYNTHESIS")
            print("=" * 80)

            voice_agent = VoiceAgent()
            audio_data = voice_agent.generate_audio_for_animated_scenes(
                parsed_script=parsed_script,
                reel_name=reel_name,
                mode=mode
            )

            print(f"\n✓ Audio generated: {len(audio_data)} tracks")

            # Stage 6: Composite Video Clips
            print("\n" + "=" * 80)
            print("STAGE 6/7: VIDEO COMPOSITION")
            print("=" * 80)

            compositor = AnimationCompositorAgent()
            composite_video_path = compositor.composite_scenes(
                scene_videos=scene_videos,
                audio_data=audio_data,
                reel_name=reel_name
            )

            print(f"\n✓ Composite video created: {composite_video_path}")

            # Stage 7: Add Dialogue Overlays
            print("\n" + "=" * 80)
            print("STAGE 7/7: DIALOGUE OVERLAYS")
            print("=" * 80)

            # Calculate scene start times based on actual audio durations
            scene_start_times = self._calculate_scene_start_times(audio_data)

            dialogue_agent = DialogueOverlayAgent()
            dialogue_clips = dialogue_agent.create_dialogue_overlays_for_scenes(
                parsed_script=parsed_script,
                audio_data=audio_data,
                scene_start_times=scene_start_times
            )

            print(f"\n✓ Dialogue overlays created: {len(dialogue_clips)} clips")

            # Final composition
            print("\nCompositing final video with dialogue overlays...")

            composite_video = VideoFileClip(composite_video_path)

            if dialogue_clips:
                final_video = CompositeVideoClip([composite_video] + dialogue_clips)
            else:
                final_video = composite_video

            # Save final video
            final_path = os.path.join(self.base_output_dir, reel_name, f"{reel_name}.mp4")

            print(f"\nWriting final video to: {final_path}")
            final_video.write_videofile(
                final_path,
                fps=24,
                codec='libx264',
                audio_codec='aac',
                temp_audiofile='temp-audio-final.m4a',
                remove_temp=True
            )

            # Cleanup
            composite_video.close()
            final_video.close()

            print("\n" + "=" * 80)
            print("✓ ANIMATED REEL COMPLETE!")
            print("=" * 80)
            print(f"\nFinal video: {final_path}")
            print(f"Duration: {parsed_script['total_duration']}s")
            print(f"Scenes: {len(parsed_script['scenes'])}")
            print(f"Characters: {len(parsed_script['characters'])}")

            return final_path

        except Exception as e:
            print(f"\n✗ ERROR in orchestration: {e}")
            import traceback
            traceback.print_exc()
            raise

    def _calculate_scene_start_times(self, audio_data: List[Dict]) -> List[float]:
        """
        Calculate cumulative start times for each scene based on actual audio durations.

        Args:
            audio_data: List of audio data dicts with audio_path

        Returns:
            List of start times in seconds
        """
        from moviepy import AudioFileClip

        start_times = []
        cumulative_time = 0.0

        for audio_dict in audio_data:
            start_times.append(cumulative_time)

            # Get actual audio duration
            audio_clip = AudioFileClip(audio_dict['audio_path'])
            actual_duration = audio_clip.duration
            audio_clip.close()

            cumulative_time += actual_duration

        return start_times


def main():
    """
    CLI entry point for animated reel orchestration.
    """
    parser = argparse.ArgumentParser(
        description="Generate animated Instagram Reels from plain text scripts"
    )
    parser.add_argument(
        "script_file",
        help="Path to plain text script file"
    )
    parser.add_argument(
        "reel_name",
        help="Name for the generated reel (used for output directory)"
    )
    parser.add_argument(
        "--theme",
        default="Cinematic",
        choices=["Cinematic", "Cartoon", "Cyberpunk", "Sketch", "Corporate"],
        help="Visual theme for the reel"
    )
    parser.add_argument(
        "--mode",
        default="story",
        choices=["story", "news"],
        help="Content mode: story (creative) or news (factual)"
    )

    args = parser.parse_args()

    # Read script file
    if not os.path.exists(args.script_file):
        print(f"Error: Script file not found: {args.script_file}")
        sys.exit(1)

    with open(args.script_file, "r") as f:
        script_text = f.read()

    # Run orchestrator
    orchestrator = AnimatedReelOrchestrator()

    try:
        final_video = orchestrator.orchestrate_animated_reel(
            script_text=script_text,
            reel_name=args.reel_name,
            theme=args.theme,
            mode=args.mode
        )

        print(f"\n🎬 Success! Watch your animated reel: {final_video}")
        sys.exit(0)

    except Exception as e:
        print(f"\n❌ Failed to generate animated reel: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Test mode if no arguments provided
    if len(sys.argv) == 1:
        print("=" * 80)
        print("ANIMATED REEL ORCHESTRATOR - TEST MODE")
        print("=" * 80)

        # Create test script
        test_script = """TITLE: The Robot's Journey
THEME: Cinematic Sci-Fi

CHARACTERS:
- ROBO-7: A small, rusty robot with glowing blue eyes and antenna ears
- GIRL: A young girl, 8 years old, wearing a yellow raincoat

---

SCENE 1 (Location: Wasteland at sunset)
ROBO-7: "Where... am I?"
ACTION: ROBO-7 wakes up in a barren wasteland, looks around confused
CAMERA: Slow zoom in on robot's face

SCENE 2 (Location: Same wasteland)
ROBO-7: "A flower? Here?"
ACTION: ROBO-7 spots a single flower growing in the dirt, moves closer
CAMERA: Pan down from robot to flower

---"""

        orchestrator = AnimatedReelOrchestrator()

        print("\nTest script loaded. Running orchestrator...")
        print("Note: This will take approximately 30 minutes (2 scenes × 15 min each)\n")

        try:
            final_video = orchestrator.orchestrate_animated_reel(
                script_text=test_script,
                reel_name="test_robot_journey",
                theme="Cinematic",
                mode="story"
            )

            print(f"\n✓ Test successful! Video: {final_video}")

        except Exception as e:
            print(f"\n✗ Test failed: {e}")
            import traceback
            traceback.print_exc()

    else:
        main()
