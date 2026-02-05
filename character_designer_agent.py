import os
import json
import base64
import boto3
from typing import List, Dict
from dotenv import load_dotenv
from langchain_aws import ChatBedrock
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

load_dotenv()

class CharacterVisualBible(BaseModel):
    """Complete visual reference for a character"""
    name: str = Field(description="Character name")
    full_description: str = Field(description="Expanded detailed physical description")
    distinctive_features: str = Field(description="Key features for consistency (e.g., 'glowing blue eyes, antenna ears, rusty metal')")
    color_palette: str = Field(description="Primary colors associated with this character")
    reference_images: List[str] = Field(description="Paths to generated reference images")
    nova_reel_prompt_template: str = Field(description="Template prompt for Nova Reel video generation")

class CharacterBibleCollection(BaseModel):
    """Collection of all character visual bibles"""
    characters: List[CharacterVisualBible]

class CharacterDesignerAgent:
    def __init__(self):
        self.region = os.getenv("AWS_REGION", "us-east-1")
        self.bedrock = boto3.client(
            service_name="bedrock-runtime",
            region_name=self.region
        )
        self.llm = ChatBedrock(
            model_id="us.anthropic.claude-3-5-sonnet-20240620-v1:0",
            model_kwargs={"temperature": 0.5}  # Moderate creativity for descriptions
        )
        self.nova_canvas_model_id = "amazon.nova-canvas-v1:0"
        self.base_output_dir = "output"

    def design_characters(self, characters: List[Dict], theme: str, reel_name: str) -> Dict:
        """
        Generate character reference images and visual descriptions.

        Args:
            characters: List of character definitions from parsed script
            theme: Visual theme (e.g., "Cinematic", "Cartoon")
            reel_name: Name for organizing output files

        Returns:
            Dictionary with complete character visual bibles
        """
        character_bibles = []

        for char in characters:
            print(f"\nDesigning character: {char['name']}")

            # Step 1: Expand character description using Claude
            expanded_desc = self._expand_character_description(
                char['name'],
                char['description'],
                theme
            )

            print(f"Expanded description generated")

            # Step 2: Generate reference images using Nova Canvas
            reference_images = self._generate_character_references(
                char['name'],
                expanded_desc['full_description'],
                theme,
                reel_name
            )

            print(f"Reference images generated: {len(reference_images)} files")

            # Step 3: Create character visual bible
            bible = CharacterVisualBible(
                name=char['name'],
                full_description=expanded_desc['full_description'],
                distinctive_features=expanded_desc['distinctive_features'],
                color_palette=expanded_desc['color_palette'],
                reference_images=reference_images,
                nova_reel_prompt_template=expanded_desc['nova_reel_prompt_template']
            )

            character_bibles.append(bible.model_dump())

        # Save complete character bible collection
        result = {
            "characters": character_bibles,
            "theme": theme
        }

        output_dir = os.path.join(self.base_output_dir, reel_name)
        os.makedirs(output_dir, exist_ok=True)

        bible_path = os.path.join(output_dir, "character_bibles.json")
        with open(bible_path, "w") as f:
            json.dump(result, f, indent=2)

        print(f"\n✓ Character bibles saved to: {bible_path}")

        return result

    def _expand_character_description(self, name: str, basic_description: str, theme: str) -> Dict:
        """
        Use Claude to expand basic character description into detailed visual bible.

        Args:
            name: Character name
            basic_description: Basic description from script
            theme: Visual theme

        Returns:
            Dictionary with expanded descriptions and distinctive features
        """
        system_prompt = """You are a professional character designer for animated videos.
Your task is to expand basic character descriptions into detailed visual references that ensure consistency across multiple video scenes.

GUIDELINES:
1. Create a FULL_DESCRIPTION (2-3 sentences) with:
   - Physical appearance (height, build, proportions)
   - Clothing/accessories details
   - Distinctive features that make character recognizable
   - Age indicators and expression tendencies

2. Extract DISTINCTIVE_FEATURES (comma-separated):
   - 3-5 unique visual elements
   - Focus on face, body, and signature items
   - Example: "glowing blue eyes, antenna ears, rusty metal body, dented chest plate"

3. Define COLOR_PALETTE (comma-separated):
   - Primary colors (2-3)
   - Secondary colors (1-2)
   - Example: "rusty orange, metallic silver, glowing cyan blue"

4. Create NOVA_REEL_PROMPT_TEMPLATE:
   - Combine character details into a reusable prompt fragment
   - Format: "[NAME], [key features], [action placeholder]"
   - Example: "ROBO-7, a small rusty robot with glowing blue eyes and antenna ears, [ACTION]"

Match the style to the theme: {theme}

CRITICAL: Return ONLY valid JSON, no explanatory text before or after."""

        parser = JsonOutputParser()
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", """Character Name: {name}
Basic Description: {description}
Theme: {theme}

Return ONLY valid JSON (no explanatory text) with these keys:
- full_description
- distinctive_features
- color_palette
- nova_reel_prompt_template""")
        ])

        chain = prompt | self.llm | parser

        try:
            result = chain.invoke({
                "name": name,
                "description": basic_description,
                "theme": theme
            })
            return result
        except Exception as e:
            print(f"Error expanding character description: {e}")
            # Fallback to basic structure
            return {
                "full_description": basic_description,
                "distinctive_features": basic_description,
                "color_palette": "neutral tones",
                "nova_reel_prompt_template": f"{name}, {basic_description}, [ACTION]"
            }

    def _generate_character_references(self, name: str, description: str, theme: str, reel_name: str) -> List[str]:
        """
        Generate character reference images using Nova Canvas.

        Args:
            name: Character name
            description: Full character description
            theme: Visual theme
            reel_name: Name for organizing output

        Returns:
            List of file paths to generated reference images
        """
        char_dir = os.path.join(self.base_output_dir, reel_name, "characters")
        os.makedirs(char_dir, exist_ok=True)

        reference_images = []

        # Define views for character model sheet
        views = [
            {
                "view": "front",
                "prompt": f"Character design reference sheet, front view of {description}. Clean white background, character centered. {theme} style, high quality character art, turnaround sheet, model sheet."
            },
            {
                "view": "three_quarter",
                "prompt": f"Character design reference sheet, three-quarter view of {description}. Clean white background, character centered. {theme} style, high quality character art, turnaround sheet, model sheet."
            },
            {
                "view": "reference",
                "prompt": f"Full character reference of {description}. Portrait style, detailed features visible. {theme} style, professional character design, high quality."
            }
        ]

        for view_config in views:
            view_name = view_config["view"]
            prompt = view_config["prompt"]

            try:
                print(f"  Generating {view_name} view...")

                # Nova Canvas API payload
                body_dict = {
                    "taskType": "TEXT_IMAGE",
                    "textToImageParams": {
                        "text": prompt
                    },
                    "imageGenerationConfig": {
                        "numberOfImages": 1,
                        "height": 1024,  # Vertical format for reference
                        "width": 576,
                        "quality": "standard",
                        "cfgScale": 8.0
                    }
                }

                response = self.bedrock.invoke_model(
                    modelId=self.nova_canvas_model_id,
                    body=json.dumps(body_dict)
                )

                response_body = json.loads(response.get("body").read())
                base64_image = response_body.get("images")[0]
                image_data = base64.b64decode(base64_image)

                # Save image
                safe_name = name.replace(" ", "_").replace("-", "_").lower()
                file_path = os.path.join(char_dir, f"{safe_name}_{view_name}.png")

                with open(file_path, "wb") as f:
                    f.write(image_data)

                reference_images.append(file_path)
                print(f"    ✓ Saved: {file_path}")

            except Exception as e:
                print(f"    ✗ Error generating {view_name} view: {e}")
                # Continue with other views even if one fails

        if not reference_images:
            print(f"  Warning: No reference images generated for {name}")

        return reference_images

if __name__ == "__main__":
    # Test with example characters
    test_characters = [
        {
            "name": "ROBO-7",
            "description": "A small, rusty robot with glowing blue eyes and antenna ears"
        },
        {
            "name": "GIRL",
            "description": "A young girl, 8 years old, wearing a yellow raincoat"
        }
    ]

    agent = CharacterDesignerAgent()

    print("=== Character Designer Agent Test ===\n")
    print(f"Designing {len(test_characters)} characters...")

    result = agent.design_characters(
        characters=test_characters,
        theme="Cinematic Sci-Fi",
        reel_name="test_robot_journey"
    )

    print("\n=== DESIGN COMPLETE ===")
    for char in result['characters']:
        print(f"\nCharacter: {char['name']}")
        print(f"  Distinctive Features: {char['distinctive_features']}")
        print(f"  Color Palette: {char['color_palette']}")
        print(f"  Reference Images: {len(char['reference_images'])}")
        print(f"  Prompt Template: {char['nova_reel_prompt_template'][:80]}...")
