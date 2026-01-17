import os
import json
import base64
import boto3
from typing import List, Dict
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

    def _optimize_prompt(self, visual_prompt: str, theme: str) -> str:
        style_mappings = {
            "cartoon": "vibrant 3D animation style, Pixar-like, expressive characters",
            "cinematic": "photorealistic, cinematic lighting, 8k, highly detailed, professional photography",
            "corporate": "clean, professional stock photo, minimalist, modern office aesthetic",
            "cyberpunk": "neon, futuristic, high-tech, dark moody lighting",
            "sketch": "artistic charcoal sketch, hand-drawn, textured paper"
        }
        
        style_suffix = style_mappings.get(theme.lower(), f"in the style of {theme}")
        return f"{visual_prompt}. {style_suffix}. High quality, no text."

    def generate_images(self, script_json: Dict, theme: str, reel_name: str) -> List[str]:
        generated_files = []
        scenes = script_json.get("scenes", [])
        
        reel_dir = os.path.join(self.base_output_dir, reel_name, "images")
        os.makedirs(reel_dir, exist_ok=True)
        
        for scene in scenes:
            scene_num = scene.get("scene_number")
            visual_prompt = scene.get("visual_prompt")
            
            optimized_prompt = self._optimize_prompt(visual_prompt, theme)
            
            # Updated payload format for amazon.nova-canvas-v1:0
            body = json.dumps({
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
            })
            
            try:
                response = self.bedrock.invoke_model(
                    modelId=self.model_id,
                    body=body
                )
                
                response_body = json.loads(response.get("body").read())
                # Nova Canvas returns 'images' as a list of base64 strings
                base64_image = response_body.get("images")[0]
                image_data = base64.b64decode(base64_image)
                
                file_path = os.path.join(reel_dir, f"scene_{scene_num}.png")
                with open(file_path, "wb") as f:
                    f.write(image_data)
                
                generated_files.append(file_path)
            except Exception as e:
                print(f"Error generating image for scene {scene_num}: {e}")
                
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
