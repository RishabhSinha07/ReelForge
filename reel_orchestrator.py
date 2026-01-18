import os
import json
import logging
import sys
from planner_agent import generate_reel_ideas
from script_agent import generate_script
from visual_agent import VisualAgent
from voice_agent import VoiceAgent
from video_agent import VideoAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def orchestrate_reel(reel_idea: str, theme: str, reel_name: str, duration: int = 30, mode: str = "story"):
    """
    Orchestrates the creation of an Instagram Reel from an initial idea.
    """
    output_dir = os.path.join("output", reel_name)
    os.makedirs(output_dir, exist_ok=True)
    
    logger.info(f"Starting orchestration for reel: {reel_name}")
    logger.info(f"Mode: {mode}")
    logger.info(f"Idea: {reel_idea}")
    logger.info(f"Theme: {theme}")
    logger.info(f"Target Duration: {duration}s")

    # 1. Planner Agent
    logger.info("Step 1/5: Generating content plan...")
    plans = generate_reel_ideas(1, reel_idea, mode=mode)
    if not plans:
        logger.error("Failed to generate content plan.")
        return None
    
    plan = plans[0]
    plan_path = os.path.join(output_dir, "plan.json")
    with open(plan_path, "w") as f:
        json.dump(plan, f, indent=2)
    logger.info(f"Plan generated and saved to {plan_path}")

    # 2. Script Agent
    logger.info("Step 2/5: Generating detailed script...")
    try:
        script = generate_script(plan, theme, target_duration=duration, mode=mode)
        script_path = os.path.join(output_dir, "script.json")
        with open(script_path, "w") as f:
            json.dump(script, f, indent=2)
        logger.info(f"Script generated and saved to {script_path}")
    except Exception as e:
        logger.error(f"Failed to generate script: {e}")
        return None

    # 3. Visual Agent
    logger.info("Step 3/5: Generating images for each scene...")
    try:
        visual_agent = VisualAgent()
        image_paths = visual_agent.generate_images(script, theme, reel_name, mode=mode)
        if not image_paths:
            logger.error("No images were generated.")
            return None
        logger.info(f"Successfully generated {len(image_paths)} images.")
    except Exception as e:
        logger.error(f"Error during image generation: {e}")
        return None

    # 4. Voice Agent
    logger.info("Step 4/5: Generating voice-over audio...")
    try:
        voice_agent = VoiceAgent()
        audio_paths = voice_agent.generate_audio(script, reel_name, mode=mode)
        if not audio_paths:
            logger.error("No audio files were generated.")
            return None
        logger.info(f"Successfully generated {len(audio_paths)} audio files and corresponding speech marks for karaoke.")
    except Exception as e:
        logger.error(f"Error during audio generation: {e}")
        return None

    # 5. Video Agent
    logger.info("Step 5/5: Assembling final video...")
    try:
        video_agent = VideoAgent()
        video_path = video_agent.create_video(reel_name, script, mode=mode)
        logger.info(f"Final video created successfully: {video_path}")
        return video_path
    except Exception as e:
        logger.error(f"Error during video assembly: {e}")
        return None

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Orchestrate Reel Creation")
    parser.add_argument("idea", help="The initial idea or topic for the reel")
    parser.add_argument("theme", help="The style/theme (e.g., cinematic, cartoon)")
    parser.add_argument("name", help="The unique name for the reel output")
    parser.add_argument("--duration", type=int, default=30, help="Target duration in seconds (default: 30)")
    parser.add_argument("--mode", choices=["story", "news"], default="story", help="Content mode: story or news (default: story)")
    
    args = parser.parse_args()

    final_path = orchestrate_reel(
        args.idea, 
        args.theme, 
        args.name, 
        duration=args.duration,
        mode=args.mode
    )
    
    if final_path:
        print(f"\nSUCCESS! Final Reel: {final_path}")
    else:
        print("\nFAILED! Check logs for details.")
        sys.exit(1)
