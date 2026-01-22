import os
import json
import base64
import boto3
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()

class VisualAgent:
    def __init__(self):
        self.region = os.getenv("AWS_REGION", "us-east-1")
        self.bedrock = boto3.client(
            service_name="bedrock-runtime",
            region_name=self.region
        )
        self.model_id = "amazon.nova-canvas-v1:0"
        self.base_output_dir = "output"

    def _optimize_prompt(self, visual_prompt: str, theme: str, visual_bible: Optional[Dict] = None, mode: str = "story") -> str:
        if mode == "news":
            return f"photojournalism, natural lighting, real world, {visual_prompt}. High quality, documentary style, realistic, no text."

        style_mappings = {
            "cartoon": "vibrant 3D animation style, Pixar-like, expressive characters",
            "cinematic": "photorealistic, cinematic lighting, 8k, highly detailed, professional photography",
            "corporate": "clean, professional stock photo, minimalist, modern office aesthetic",
            "cyberpunk": "neon, futuristic, high-tech, dark moody lighting",
            "sketch": "artistic charcoal sketch, hand-drawn, textured paper"
        }

        style_suffix = style_mappings.get(theme.lower(), f"in the style of {theme}")

        # Build compact Visual Bible hints (only for characters mentioned in this scene)
        consistency_hints = ""
        if visual_bible:
            # Find which characters are mentioned in this scene's visual_prompt
            prompt_lower = visual_prompt.lower()
            characters = visual_bible.get("characters", [])

            mentioned_chars = []
            for c in characters:
                char_name = c.get("name", "").lower()
                # Check if character name appears in the visual prompt
                if char_name and char_name in prompt_lower:
                    # Build a compact description: just distinctive features
                    features = c.get("distinctive_features", "")
                    if features:
                        mentioned_chars.append(f"{c.get('name')}: {features}")

            if mentioned_chars:
                consistency_hints = " Character details: " + ", ".join(mentioned_chars) + "."

            # Add color palette as a subtle hint
            if visual_bible.get("color_palette"):
                consistency_hints += f" Colors: {visual_bible.get('color_palette')}."

        # SCENE ACTION FIRST, then style, then consistency hints at the end
        return f"{visual_prompt}. {style_suffix}. High quality, no text.{consistency_hints}"

    def generate_images(self, script_json: Dict, theme: str, reel_name: str, mode: str = "story") -> List[str]:
        generated_files = []
        scenes = script_json.get("scenes", [])
        visual_bible = script_json.get("visual_bible")

        reel_dir = os.path.join(self.base_output_dir, reel_name, "images")
        os.makedirs(reel_dir, exist_ok=True)

        for scene in scenes:
            scene_num = scene.get("scene_number")
            visual_prompt = scene.get("visual_prompt")

            optimized_prompt = self._optimize_prompt(visual_prompt, theme, visual_bible, mode)
            
            # Updated payload format for amazon.nova-canvas-v1:0
            body_dict = {
                "taskType": "TEXT_IMAGE",
                "textToImageParams": {
                    "text": optimized_prompt
                },
                "imageGenerationConfig": {
                    "numberOfImages": 1,
                    "height": 1024,  # 9:16 ratio
                    "width": 576,
                    "quality": "standard",
                    "cfgScale": 8.0
                }
            }

            success = False
            for attempt in range(2): # Simple retry with slightly modified prompt if filtered
                try:
                    if attempt > 0:
                        # Slightly modify prompt if it was blocked
                        if mode == "news":
                            body_dict["textToImageParams"]["text"] = f"Photo of: {visual_prompt}, natural lighting"
                        else:
                            body_dict["textToImageParams"]["text"] = f"A beautiful artistic depiction of: {visual_prompt}"

                    response = self.bedrock.invoke_model(
                        modelId=self.model_id,
                        body=json.dumps(body_dict)
                    )
                    
                    response_body = json.loads(response.get("body").read())
                    base64_image = response_body.get("images")[0]
                    image_data = base64.b64decode(base64_image)
                    
                    file_path = os.path.join(reel_dir, f"scene_{scene_num}.png")
                    with open(file_path, "wb") as f:
                        f.write(image_data)
                    
                    generated_files.append(file_path)
                    success = True
                    break
                except Exception as e:
                    if "blocked by our content filters" in str(e) and attempt == 0:
                        print(f"Content filter block for scene {scene_num}, retrying with modified prompt...")
                        continue
                    print(f"Error generating image for scene {scene_num}: {e}")
                    raise Exception(f"Failed to generate image for scene {scene_num}: {e}")
            
            if not success:
                raise Exception(f"Failed to generate image for scene {scene_num} after multiple attempts.")
                
        return generated_files

if __name__ == "__main__":
    # Example usage
    example_script = {
    "scenes": [
        {
        "scene_number": 1,
        "on_screen_text": "Rainbow Potato Paradise",
        "voice_line": "Bored with plain potatoes?",
        "visual_prompt": "A single plain potato on a white background",
        "duration_seconds": 3.0
        },
        {
        "scene_number": 2,
        "on_screen_text": "BOOM!",
        "voice_line": "Get ready for a colorful explosion!",
        "visual_prompt": "Potato bursts open, revealing layers of vibrant colors inside",
        "duration_seconds": 4.0
        },
        {
        "scene_number": 3,
        "on_screen_text": "Purple, Blue, Green",
        "voice_line": "Scoop up a rainbow of flavors!",
        "visual_prompt": "Quick cuts of hands scooping purple, blue, and green mashed potatoes onto a plate",
        "duration_seconds": 5.0
        },
        {
        "scene_number": 4,
        "on_screen_text": "Yellow, Orange, Red",
        "voice_line": "Layer on the sunny hues!",
        "visual_prompt": "Continued quick cuts of hands scooping yellow, orange, and red mashed potatoes",
        "duration_seconds": 5.0
        },
        {
        "scene_number": 5,
        "on_screen_text": "Tada!",
        "voice_line": "Behold, your potato masterpiece!",
        "visual_prompt": "Birds-eye view of the finished colorful potato artwork, sprinkled with herbs",
        "duration_seconds": 5.0
        },
        {
        "scene_number": 6,
        "on_screen_text": "Rainbow Potato Paradise",
        "voice_line": "Dig into the rainbow!",
        "visual_prompt": "Final shot of the vibrant potato creation with a fork diving in",
        "duration_seconds": 3.0
        }
    ]
    }
    
    agent = VisualAgent()
    images = agent.generate_images(example_script, "cinematic", "rainbow_potato_paradise")
    print(f"Generated images: {images}")
