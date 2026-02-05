import os
from typing import List, Dict
from moviepy import VideoFileClip, AudioFileClip, CompositeVideoClip, concatenate_videoclips
from moviepy.video.fx import FadeIn, FadeOut

class AnimationCompositorAgent:
    """
    Stitches animated video clips into continuous sequence.

    Handles:
    - Video-audio synchronization
    - Crossfade transitions
    - Speed adjustments to match audio duration
    """

    def __init__(self):
        self.base_output_dir = "output"
        self.crossfade_duration = 0.3  # 300ms overlap

    def composite_scenes(
        self,
        scene_videos: List[str],
        audio_data: List[Dict],
        reel_name: str,
        target_size: tuple = (1080, 1920)  # 9:16 vertical
    ) -> str:
        """
        Composite multiple scene videos with synchronized audio.

        Args:
            scene_videos: List of video file paths
            audio_data: List of dicts with audio_path, speech_marks, etc.
            reel_name: Name for saving output
            target_size: Output resolution (width, height)

        Returns:
            Path to composited video file
        """
        print(f"\n=== Compositing {len(scene_videos)} video clips ===")

        clips = []

        for idx, (video_path, audio_dict) in enumerate(zip(scene_videos, audio_data)):
            print(f"\nProcessing scene {idx + 1}...")

            # Load video and audio
            video_clip = VideoFileClip(video_path)
            audio_path = audio_dict.get("audio_path")

            if not audio_path or not os.path.exists(audio_path):
                print(f"  Warning: Audio file not found for scene {idx + 1}, using video audio")
                clips.append(video_clip)
                continue

            audio_clip = AudioFileClip(audio_path)

            print(f"  Video duration: {video_clip.duration:.2f}s")
            print(f"  Audio duration: {audio_clip.duration:.2f}s")

            # Adjust video duration to match audio
            synced_video = self._sync_video_to_audio(video_clip, audio_clip)

            # Resize to target dimensions (crop center for vertical format)
            if synced_video.size != target_size:
                synced_video = self._resize_and_crop(synced_video, target_size)

            clips.append(synced_video)

            print(f"  ✓ Scene {idx + 1} prepared")

        # Concatenate with crossfade transitions
        print(f"\nConcatenating clips with {self.crossfade_duration}s crossfades...")

        if len(clips) == 1:
            final = clips[0]
        else:
            final = self._concatenate_with_crossfade(clips)

        # Save composite video
        output_path = os.path.join(
            self.base_output_dir,
            reel_name,
            "composite_video.mp4"
        )

        print(f"\nWriting composite video...")
        final.write_videofile(
            output_path,
            fps=24,
            codec='libx264',
            audio_codec='aac',
            temp_audiofile='temp-audio.m4a',
            remove_temp=True
        )

        # Clean up
        for clip in clips:
            clip.close()
        final.close()

        print(f"✓ Composite video saved: {output_path}")

        return output_path

    def _sync_video_to_audio(
        self,
        video_clip: VideoFileClip,
        audio_clip: AudioFileClip
    ) -> VideoFileClip:
        """
        Synchronize video duration with audio.

        Args:
            video_clip: Input video
            audio_clip: Target audio

        Returns:
            Video clip with synchronized duration and audio
        """
        video_duration = video_clip.duration
        audio_duration = audio_clip.duration

        # Sync video duration with audio (MoviePy 2.x compatible)
        if abs(video_duration - audio_duration) < 0.1:
            # Durations are close enough
            synced_video = video_clip
        elif video_duration > audio_duration:
            # Video is longer, trim it
            synced_video = video_clip.subclipped(0, audio_duration)
            print(f"    Trimming video to {audio_duration:.2f}s")
        else:
            # Video is shorter - slow it down and/or freeze last frame
            speed_factor = video_duration / audio_duration

            # If speed reduction is moderate (<0.7x), just slow down the video
            if speed_factor >= 0.7:
                synced_video = video_clip.time_transform(lambda t: t * speed_factor)
                print(f"    Slowing video to {1/speed_factor:.2f}x speed to match {audio_duration:.2f}s")
            else:
                # For larger gaps, slow to 0.7x and freeze last frame for remainder
                slowed_video = video_clip.time_transform(lambda t: t * 0.7)
                slowed_duration = video_duration / 0.7
                freeze_duration = audio_duration - slowed_duration

                # Get last frame and hold it
                last_frame = video_clip.to_ImageClip(t=video_duration - 0.1).with_duration(freeze_duration)
                synced_video = concatenate_videoclips([slowed_video, last_frame], method="compose")
                print(f"    Slowing to 1.43x + freezing last frame for {freeze_duration:.2f}s to match {audio_duration:.2f}s")

        # Set audio (MoviePy 2.x uses with_audio)
        synced_video = synced_video.with_audio(audio_clip)

        return synced_video

    def _resize_and_crop(
        self,
        video_clip: VideoFileClip,
        target_size: tuple
    ) -> VideoFileClip:
        """
        Resize and crop video to target dimensions.

        Args:
            video_clip: Input video
            target_size: (width, height)

        Returns:
            Resized and cropped video
        """
        target_width, target_height = target_size
        target_aspect = target_width / target_height

        current_width, current_height = video_clip.size
        current_aspect = current_width / current_height

        if current_aspect > target_aspect:
            # Video is wider, crop sides
            new_height = current_height
            new_width = int(current_height * target_aspect)
        else:
            # Video is taller, crop top/bottom
            new_width = current_width
            new_height = int(current_width / target_aspect)

        # Calculate crop position (center)
        x_center = current_width / 2
        y_center = current_height / 2

        x1 = int(x_center - new_width / 2)
        y1 = int(y_center - new_height / 2)

        # Crop and resize (MoviePy 2.x)
        cropped = video_clip.cropped(
            x1=x1,
            y1=y1,
            width=new_width,
            height=new_height
        )

        resized = cropped.resized(target_size)

        return resized

    def _concatenate_with_crossfade(
        self,
        clips: List[VideoFileClip]
    ) -> VideoFileClip:
        """
        Concatenate clips with crossfade transitions.

        Args:
            clips: List of video clips

        Returns:
            Concatenated video with crossfades
        """
        if not clips:
            raise ValueError("No clips to concatenate")

        if len(clips) == 1:
            return clips[0]

        # MoviePy 2.x: Simplified concatenation without crossfades
        # TODO: Re-implement crossfades when MoviePy 2.x API is more stable
        print("  Using straight cuts (crossfades temporarily disabled)")

        final = concatenate_videoclips(
            clips,
            method="compose"
        )

        return final

if __name__ == "__main__":
    # Test with example clips
    print("=== Animation Compositor Agent Test ===")
    print("\nNote: This test requires existing video and audio files")

    # Example usage (requires generated videos from previous steps)
    test_videos = [
        "output/test_robot_journey/videos/scene_1.mp4",
        "output/test_robot_journey/videos/scene_2.mp4"
    ]

    test_audio_data = [
        {"audio_path": "output/test_robot_journey/audio/scene_1_ROBO-7.mp3"},
        {"audio_path": "output/test_robot_journey/audio/scene_2_ROBO-7.mp3"}
    ]

    # Check if test files exist
    all_exist = all(os.path.exists(v) for v in test_videos)
    all_exist = all_exist and all(os.path.exists(a["audio_path"]) for a in test_audio_data)

    if not all_exist:
        print("\n✗ Test files not found. Generate videos and audio first.")
        print("  Run: python3 animated_visual_agent.py")
        print("  Then: python3 voice_agent.py")
    else:
        agent = AnimationCompositorAgent()

        try:
            composite_path = agent.composite_scenes(
                scene_videos=test_videos,
                audio_data=test_audio_data,
                reel_name="test_robot_journey"
            )

            print(f"\n✓ Test successful!")
            print(f"  Composite video: {composite_path}")

        except Exception as e:
            print(f"\n✗ Test failed: {e}")
