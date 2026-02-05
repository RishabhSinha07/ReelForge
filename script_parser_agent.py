import json
import os
import re
from typing import List, Dict
from dotenv import load_dotenv
from langchain_aws import ChatBedrock
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

# Load environment variables from .env
load_dotenv()

class CharacterDefinition(BaseModel):
    """Definition of a character in the script"""
    name: str = Field(description="Character name (e.g., ROBO-7, GIRL)")
    description: str = Field(description="Physical description of the character")

class ScriptScene(BaseModel):
    """A single scene from the script"""
    scene_number: int = Field(description="Sequential scene number starting from 1")
    characters: List[str] = Field(description="List of character names in this scene")
    dialogue: str = Field(description="What the character says (empty string if no dialogue)")
    action: str = Field(description="What happens in the scene (ACTION line)")
    location: str = Field(description="Where the scene takes place")
    camera: str = Field(description="Camera instruction (e.g., 'zoom in', 'static', 'pan')")
    duration_seconds: float = Field(description="Estimated duration based on dialogue length (150 words per minute)")

class ParsedScript(BaseModel):
    """Complete parsed script structure"""
    title: str = Field(description="The script title")
    theme: str = Field(description="Visual theme (e.g., Cinematic, Cartoon)")
    characters: List[CharacterDefinition] = Field(description="All characters defined in the script")
    scenes: List[ScriptScene] = Field(description="All scenes in sequential order")
    total_duration: float = Field(description="Total estimated duration in seconds")

class ScriptParserAgent:
    def __init__(self):
        self.llm = ChatBedrock(
            model_id="us.anthropic.claude-3-5-sonnet-20240620-v1:0",
            model_kwargs={"temperature": 0.3}  # Low temperature for structured parsing
        )
        self.parser = JsonOutputParser(pydantic_object=ParsedScript)
        self.base_output_dir = "output"

    def parse_script(self, script_text: str, reel_name: str = None) -> Dict:
        """
        Parse plain text script with scene markers into structured JSON.

        Args:
            script_text: Plain text script following the defined format
            reel_name: Optional name for saving output

        Returns:
            Dictionary containing parsed script structure
        """

        # Define the parsing prompt
        system_prompt = """You are a professional script parser. Your task is to parse plain text scripts into structured JSON format.

PARSING RULES:
1. Extract TITLE from "TITLE: ..." line
2. Extract THEME from "THEME: ..." line
3. Parse CHARACTERS section:
   - Each character has NAME: DESCRIPTION format
   - Extract all characters before first scene
4. Parse each SCENE:
   - Scene numbers start at 1
   - Extract character(s) speaking from "CHARACTER:" lines
   - Extract dialogue (what comes after "CHARACTER:")
   - Extract ACTION from "ACTION:" line
   - Extract location from "SCENE N (Location: ...)" line
   - Extract CAMERA from "CAMERA:" line
   - Estimate duration: 150 words per minute for dialogue + 2 seconds base for action
5. Calculate total_duration by summing all scene durations

DURATION ESTIMATION:
- Count words in dialogue
- duration_seconds = (word_count / 150) * 60 + 2
- Minimum 3 seconds per scene
- Round to 1 decimal place

Return valid JSON matching the ParsedScript schema."""

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "Parse this script:\n\n{script_text}\n\n{format_instructions}")
        ]).partial(format_instructions=self.parser.get_format_instructions())

        chain = prompt | self.llm | self.parser

        try:
            parsed = chain.invoke({"script_text": script_text})

            # Validate and fix scenes (add missing fields with defaults)
            for scene in parsed.get("scenes", []):
                # Ensure all required fields exist
                if "location" not in scene or not scene["location"]:
                    scene["location"] = "Unspecified location"
                if "camera" not in scene or not scene["camera"]:
                    scene["camera"] = "Static shot"
                if "duration_seconds" not in scene or scene["duration_seconds"] == 0:
                    # Estimate based on dialogue length
                    word_count = len(scene.get("dialogue", "").split())
                    scene["duration_seconds"] = max(5.0, round((word_count / 150) * 60 + 2, 1))
                if "action" not in scene or not scene["action"]:
                    scene["action"] = "Scene action"
                if "dialogue" not in scene:
                    scene["dialogue"] = ""
                if "characters" not in scene:
                    scene["characters"] = ["NARRATOR"]

            # Ensure total_duration is calculated (fallback if LLM doesn't provide it)
            if "total_duration" not in parsed or parsed["total_duration"] == 0:
                total = sum(scene.get("duration_seconds", 5.0) for scene in parsed.get("scenes", []))
                parsed["total_duration"] = round(total, 2)

            # Save parsed output if reel_name provided
            if reel_name:
                output_dir = os.path.join(self.base_output_dir, reel_name)
                os.makedirs(output_dir, exist_ok=True)

                output_path = os.path.join(output_dir, "script_parsed.json")
                with open(output_path, "w") as f:
                    json.dump(parsed, f, indent=2)

                print(f"Parsed script saved to: {output_path}")

            return parsed

        except Exception as e:
            print(f"Error parsing script: {e}")
            raise

    def validate_script_format(self, script_text: str) -> bool:
        """
        Validate that script text follows the expected format.

        Args:
            script_text: Plain text script to validate

        Returns:
            True if format is valid, False otherwise
        """
        required_patterns = [
            r"TITLE:",
            r"THEME:",
            r"CHARACTERS:",
            r"SCENE \d+"
        ]

        for pattern in required_patterns:
            if not re.search(pattern, script_text, re.IGNORECASE):
                print(f"Warning: Script missing required section: {pattern}")
                return False

        return True

    def estimate_scene_duration(self, dialogue: str, action: str = "") -> float:
        """
        Estimate scene duration based on dialogue length.

        Args:
            dialogue: Character dialogue
            action: Scene action description

        Returns:
            Estimated duration in seconds
        """
        # Count words in dialogue
        words = len(dialogue.split()) if dialogue else 0

        # 150 words per minute + 2 seconds base for action
        duration = (words / 150.0) * 60.0 + 2.0

        # Minimum 3 seconds per scene
        return max(3.0, round(duration, 1))

if __name__ == "__main__":
    # Example test script
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

SCENE 3 (Location: Wasteland with flower)
GIRL: "Hey little guy! Are you lost?"
ACTION: Girl in yellow raincoat runs up to ROBO-7, kneels beside him
CAMERA: Wide shot capturing both characters

---"""

    parser = ScriptParserAgent()

    # Validate format
    if parser.validate_script_format(test_script):
        print("Script format is valid!\n")

        # Parse script
        print("Parsing script...")
        result = parser.parse_script(test_script, reel_name="test_robot_journey")

        # Display results
        print("\n=== PARSED SCRIPT ===")
        print(json.dumps(result, indent=2))

        print(f"\n=== SUMMARY ===")
        print(f"Title: {result['title']}")
        print(f"Theme: {result['theme']}")
        print(f"Characters: {len(result['characters'])}")
        print(f"Scenes: {len(result['scenes'])}")
        print(f"Total Duration: {result['total_duration']} seconds")
    else:
        print("Script format validation failed!")
