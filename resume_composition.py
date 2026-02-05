#!/usr/bin/env python3
"""
Resume Reel Generation from Composition Stage

Use this when you already have generated videos/audio and just need to:
- Compose the final video
- Add dialogue overlays

Usage:
    python3 resume_composition.py final_working_reel
"""

import sys
import json
from animation_compositor_agent import AnimationCompositorAgent
from dialogue_overlay_agent import DialogueOverlayAgent

def resume_from_composition(reel_name: str):
    """
    Resume reel generation from composition stage.

    Assumes these files exist:
    - output/{reel_name}/script_parsed.json
    - output/{reel_name}/videos/scene_*.mp4
    - output/{reel_name}/audio/scene_*_*.mp3
    """
    print("\n" + "="*60)
    print("RESUMING REEL COMPOSITION")
    print("="*60)
    print(f"\nReel: {reel_name}\n")

    base_dir = f"output/{reel_name}"

    # Load parsed script
    with open(f"{base_dir}/script_parsed.json", 'r') as f:
        parsed_script = json.load(f)

    print(f"Loaded script: {parsed_script['title']}")
    print(f"Scenes: {len(parsed_script['scenes'])}\n")

    # Collect video files
    scene_videos = []
    for i in range(1, len(parsed_script['scenes']) + 1):
        video_path = f"{base_dir}/videos/scene_{i}.mp4"
        scene_videos.append(video_path)
        print(f"✓ Found: {video_path}")

    print("\n" + "="*60)
    print("STAGE 1/2: VIDEO COMPOSITION")
    print("="*60)

    # Collect audio data
    audio_data = []
    for i, scene in enumerate(parsed_script['scenes'], 1):
        # Get the first character speaking in this scene
        character = scene['characters'][0] if scene['characters'] else "NARRATOR"
        character_safe = character.replace('-', '_').replace(' ', '_')

        audio_data.append({
            'audio_path': f"{base_dir}/audio/scene_{i}_{character_safe}.mp3",
            'speech_marks_path': f"{base_dir}/audio/scene_{i}_{character_safe}_speechmarks.json",
            'character': character,
            'dialogue': scene['dialogue']
        })

    # Run compositor
    compositor = AnimationCompositorAgent()

    try:
        composite_video_path = compositor.composite_scenes(
            scene_videos=scene_videos,
            audio_data=audio_data,
            reel_name=reel_name
        )

        print(f"\n✓ Composite video created: {composite_video_path}")

    except Exception as e:
        print(f"\n✗ ERROR in composition: {e}")
        import traceback
        traceback.print_exc()
        return None

    print("\n" + "="*60)
    print("STAGE 2/2: DIALOGUE OVERLAYS")
    print("="*60)

    # Calculate scene start times based on ACTUAL audio durations
    # (not script durations, which may be estimates)
    scene_start_times = []
    cumulative_time = 0.0

    for audio_dict in audio_data:
        scene_start_times.append(cumulative_time)

        # Get actual audio duration
        from moviepy import AudioFileClip
        audio_clip = AudioFileClip(audio_dict['audio_path'])
        actual_duration = audio_clip.duration
        audio_clip.close()

        cumulative_time += actual_duration

    print(f"\nActual scene timings: {[f'{t:.2f}s' for t in scene_start_times]}")

    # Create dialogue overlays
    overlay_agent = DialogueOverlayAgent()

    try:
        dialogue_clips = overlay_agent.create_dialogue_overlays_for_scenes(
            parsed_script=parsed_script,
            audio_data=audio_data,
            scene_start_times=scene_start_times
        )

        print(f"\n✓ Dialogue overlays created: {len(dialogue_clips)} clips")

        # Composite final video
        print("\nCompositing final video with dialogue overlays...")

        from moviepy import VideoFileClip, CompositeVideoClip

        composite_video = VideoFileClip(composite_video_path)

        if dialogue_clips:
            final_video = CompositeVideoClip([composite_video] + dialogue_clips)
        else:
            final_video = composite_video

        # Save final video
        final_path = f"{base_dir}/{reel_name}.mp4"

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

        print("\n" + "="*60)
        print("✓ REEL COMPLETE!")
        print("="*60)
        print(f"\nFinal video: {final_path}")
        print(f"\nTo watch:")
        print(f"  open {final_path}")

        return final_path

    except Exception as e:
        print(f"\n✗ ERROR in dialogue overlays: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 resume_composition.py <reel_name>")
        print("\nExample:")
        print("  python3 resume_composition.py final_working_reel")
        sys.exit(1)

    reel_name = sys.argv[1]
    resume_from_composition(reel_name)
