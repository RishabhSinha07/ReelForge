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

def orchestrate_reel(reel_idea: str, theme: str, reel_name: str):
    """
    Orchestrates the creation of an Instagram Reel from an initial idea.
    """
    output_dir = os.path.join("output", reel_name)
    os.makedirs(output_dir, exist_ok=True)
    
    logger.info(f"Starting orchestration for reel: {reel_name}")
    logger.info(f"Idea: {reel_idea}")
    logger.info(f"Theme: {theme}")

    # 1. Planner Agent
    logger.info("Step 1/5: Generating content plan...")
    plans = generate_reel_ideas(1, reel_idea)
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
        script = generate_script(plan, theme)
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
        image_paths = visual_agent.generate_images(script, theme, reel_name)
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
        audio_paths = voice_agent.generate_audio(script, reel_name)
        if not audio_paths:
            logger.error("No audio files were generated.")
            return None
        logger.info(f"Successfully generated {len(audio_paths)} audio files.")
    except Exception as e:
        logger.error(f"Error during audio generation: {e}")
        return None

    # 5. Video Agent
    logger.info("Step 5/5: Assembling final video...")
    try:
        video_agent = VideoAgent()
        video_path = video_agent.create_video(reel_name, script)
        logger.info(f"Final video created successfully: {video_path}")
        return video_path
    except Exception as e:
        logger.error(f"Error during video assembly: {e}")
        return None

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python reel_orchestrator.py <reel_idea> <theme> <reel_name>")
        sys.exit(1)

    idea_input = sys.argv[1]
    theme_input = sys.argv[2]
    name_input = sys.argv[3]

    final_path = orchestrate_reel(idea_input, theme_input, name_input)
    
    if final_path:
        print(f"\nSUCCESS! Final Reel: {final_path}")
    else:
        print("\nFAILED! Check logs for details.")
        sys.exit(1)
