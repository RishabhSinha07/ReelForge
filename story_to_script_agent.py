import json
import os
from typing import Dict, List
from dotenv import load_dotenv
from langchain_aws import ChatBedrock
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

load_dotenv()

class StoryToScriptAgent:
    """
    Converts natural language story descriptions into formatted scripts.

    Takes simple inputs like:
    - Story idea/plot
    - Character descriptions
    - Theme preference

    Generates properly formatted scripts for the animated reel pipeline.
    """

    def __init__(self):
        self.llm = ChatBedrock(
            model_id="us.anthropic.claude-3-5-sonnet-20240620-v1:0",
            model_kwargs={"temperature": 0.7}  # Creative but controlled
        )
        self.parser = StrOutputParser()
        self.base_output_dir = "output"

    def generate_script(
        self,
        story: str,
        characters: Dict[str, str] = None,
        theme: str = "Cinematic",
        duration: str = "30 seconds",
        title: str = None
    ) -> str:
        """
        Generate a formatted script from natural language input.

        Args:
            story: Natural language story description
            characters: Dict of character_name: description (optional, will be inferred)
            theme: Visual theme (Cinematic, Cartoon, Cyberpunk, Sketch, Corporate)
            duration: Target duration ("15 seconds", "30 seconds", "1 minute")
            title: Optional title (will be generated if not provided)

        Returns:
            Formatted script text ready for ScriptParserAgent
        """

        # Build character section if provided
        character_section = ""
        if characters:
            character_section = "Use these characters:\n"
            for name, desc in characters.items():
                character_section += f"- {name}: {desc}\n"

        system_prompt = """You are a professional scriptwriter for animated storytelling video reels.

Your task is to convert story ideas into properly formatted scripts with rich narration and detailed visuals.

REQUIRED FORMAT:

TITLE: [Catchy title for the story]
THEME: [Visual theme - Cinematic/Cartoon/Cyberpunk/Sketch/Corporate]

CHARACTERS:
- NARRATOR: Storytelling voice (always include for narration)
- CHARACTER_NAME: Detailed physical description with distinctive features, clothing, and personality traits
- ANOTHER_CHARACTER: Detailed physical description

---

SCENE 1 (Location: Very specific location with environmental details)
NARRATOR: "A complete sentence that tells the story - what's happening, the emotion, the context. Use 15-25 words to paint the picture."
ACTION: Highly detailed visual description - what characters are doing, facial expressions, body language, environmental details, lighting, atmosphere. Be specific and vivid (30-50 words).
CAMERA: Camera movement with purpose (zoom in, pan left, static, dolly forward, wide shot, close up)

SCENE 2 (Location: Next specific location)
NARRATOR: "Continue the story with another complete narrative sentence describing what happens next."
ACTION: Detailed visual description of the scene.
CAMERA: Camera movement

---

CRITICAL RULES FOR STORYTELLING:
1. Use NARRATOR for voiceover storytelling - tell the story through narration, not just character dialogue
2. Each scene narration should be 15-25 words - a complete sentence that advances the story
3. ACTION descriptions must be 30-50 words - very detailed for AI video generation
4. Include emotional context, environmental details, lighting, atmosphere in ACTION
5. Total scenes: 4-6 for a 30-second reel (5-7 seconds per scene)
6. Character descriptions should include: appearance, clothing, distinctive features, personality traits
7. Location should be specific: "Snow-covered forest at twilight with bare trees" not just "forest"
8. Make it cinematic and emotionally engaging
9. Separate scene blocks with "---"
10. Every scene needs: NARRATOR (telling story), ACTION (detailed visuals), CAMERA (movement)

EXAMPLE OF GOOD NARRATION:
❌ Bad: "*Whimper*" or "The dog is sad"
✅ Good: "A small golden puppy shivers in the freezing snow, abandoned and alone, searching desperately for warmth."

EXAMPLE OF GOOD ACTION:
❌ Bad: "Dog walks in snow"
✅ Good: "The tiny puppy stumbles through deep snowdrifts, its golden fur matted with ice, ears drooping, leaving small pawprints in the pristine white snow as wind howls through bare trees. Its big brown eyes scan the horizon, filled with fear and hope."

CAMERA MOVEMENT OPTIONS:
- Zoom in slowly, Zoom out to reveal
- Pan left/right smoothly
- Static shot for emotion
- Dolly forward for tension, Dolly back for reveal
- Wide shot for scale, Close up for emotion
- Tracking shot following character

THEME GUIDELINES:
- Cinematic: Realistic, dramatic lighting, movie-like quality, emotional depth
- Cartoon: Vibrant colors, expressive characters, Pixar-style animation
- Cyberpunk: Neon lighting, futuristic tech, gritty urban atmosphere
- Sketch: Hand-drawn aesthetic, artistic line work
- Corporate: Clean, professional, modern minimalist"""

        user_prompt = """Story: {story}

{character_section}

Theme: {theme}
Target Duration: {duration}
{title_instruction}

Generate a complete formatted script following the exact format shown in the system prompt.
Make it engaging, visual, and perfect for animated video generation."""

        # Build title instruction
        title_instruction = f"Title: {title}" if title else "Generate an appropriate title"

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", user_prompt)
        ])

        chain = prompt | self.llm | self.parser

        try:
            script = chain.invoke({
                "story": story,
                "character_section": character_section,
                "theme": theme,
                "duration": duration,
                "title_instruction": title_instruction
            })

            return script

        except Exception as e:
            print(f"Error generating script: {e}")
            raise

    def save_script(self, script: str, filename: str) -> str:
        """
        Save generated script to a file.

        Args:
            script: Generated script text
            filename: Output filename (without extension)

        Returns:
            Path to saved script file
        """
        # Ensure filename ends with .txt
        if not filename.endswith('.txt'):
            filename = f"{filename}.txt"

        filepath = filename

        with open(filepath, 'w') as f:
            f.write(script)

        print(f"Script saved to: {filepath}")
        return filepath

    def story_to_reel(
        self,
        story: str,
        characters: Dict[str, str] = None,
        theme: str = "Cinematic",
        duration: str = "30 seconds",
        output_name: str = None
    ) -> str:
        """
        Complete workflow: story → script → saved file.

        Args:
            story: Natural language story
            characters: Optional character definitions
            theme: Visual theme
            duration: Target duration
            output_name: Output filename (defaults to generated from story)

        Returns:
            Path to saved script file
        """
        print("Generating script from story...")
        script = self.generate_script(story, characters, theme, duration)

        print("\n" + "="*60)
        print("GENERATED SCRIPT:")
        print("="*60)
        print(script)
        print("="*60 + "\n")

        # Generate filename if not provided
        if not output_name:
            # Create safe filename from title in script
            import re
            title_match = re.search(r'TITLE:\s*(.+)', script)
            if title_match:
                title = title_match.group(1).strip()
                output_name = re.sub(r'[^\w\s-]', '', title).strip().replace(' ', '_').lower()
            else:
                output_name = "generated_script"

        filepath = self.save_script(script, output_name)

        return filepath


def generate_reel_from_story(
    story: str,
    characters: Dict[str, str] = None,
    theme: str = "Cinematic",
    duration: str = "30 seconds",
    reel_name: str = None
):
    """
    Helper function: Generate script and immediately create animated reel.

    Args:
        story: Natural language story description
        characters: Character definitions
        theme: Visual theme
        duration: Target duration
        reel_name: Name for the reel (auto-generated if not provided)
    """
    agent = StoryToScriptAgent()

    # Generate and save script
    script_file = agent.story_to_reel(story, characters, theme, duration, reel_name)

    print(f"\n✓ Script generated: {script_file}")
    print("\nTo generate the animated reel, run:")
    print(f"  python3 animated_reel_orchestrator.py {script_file} {reel_name or 'my_reel'} --theme {theme}")

    return script_file


if __name__ == "__main__":
    # Example 1: Simple story with auto-generated characters
    print("=== Example 1: Simple Story ===\n")

    simple_story = """
    A lonely robot wakes up in a desert wasteland. It discovers a small flower
    growing in the sand and realizes it's not alone. A young girl appears and
    befriends the robot, showing it that there's still hope in the world.
    """

    agent = StoryToScriptAgent()
    script = agent.story_to_reel(
        story=simple_story,
        theme="Cinematic",
        duration="30 seconds",
        output_name="robot_friendship"
    )

    print("\n" + "="*60)
    print("=== Example 2: Story with Defined Characters ===\n")

    adventure_story = """
    A brave knight climbs a mountain to retrieve a magical crystal.
    At the peak, they face a dragon guardian. Instead of fighting,
    the knight makes peace with the dragon by sharing their lunch.
    """

    adventure_characters = {
        "SIR KNIGHT": "A knight in silver armor with a red cape and golden sword",
        "DRAGON": "A large purple dragon with kind eyes and golden scales"
    }

    script2 = agent.story_to_reel(
        story=adventure_story,
        characters=adventure_characters,
        theme="Cartoon",
        duration="30 seconds",
        output_name="knight_and_dragon"
    )

    print("\n✓ Examples complete!")
    print("\nGenerated scripts can be used with:")
    print("  python3 animated_reel_orchestrator.py <script_file> <reel_name> --theme <theme>")
