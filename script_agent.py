import json
import os
from typing import List, Dict, Optional
from dotenv import load_dotenv
from langchain_aws import ChatBedrock
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from pydantic import BaseModel, Field, field_validator

load_dotenv()

def validate_facts(script: Dict):
    """
    Checks for fictional elements, storytelling phrases, emojis, and exaggerations in the script.
    Fails if any are detected.
    """
    fictional_words = ["imagine", "what if", "journey", "magic", "wonder", "story", "myth", "legend", "fairytale"]
    storytelling_phrases = ["once upon a time", "in a world", "long ago", "it all started when", "picture this"]
    
    for scene in script.get("scenes", []):
        text = scene.get("voice_line", "").lower()
        visual = scene.get("visual_prompt", "").lower()
        combined = text + " " + visual
        
        # Check for emojis
        if any(char for char in text if ord(char) > 0x1F600 and ord(char) < 0x1F64F):
            raise ValueError(f"Factual validation failed: Emojis detected in scene {scene['scene_number']}.")
        
        # Check for fictional words
        for word in fictional_words:
            if word in combined:
                raise ValueError(f"Factual validation failed: Fictional word '{word}' detected in scene {scene['scene_number']}.")
                
        # Check for storytelling phrases
        for phrase in storytelling_phrases:
            if phrase in combined:
                raise ValueError(f"Factual validation failed: Storytelling phrase '{phrase}' detected in scene {scene['scene_number']}.")
        
        # Check for exaggerations (very subjective, but we can catch some common ones)
        exaggerations = ["mind-blowing", "unbelievable", "insane", "shocking", "life-changing"]
        for word in exaggerations:
            if word in combined:
                raise ValueError(f"Factual validation failed: Exaggeration '{word}' detected in scene {scene['scene_number']}.")

class Character(BaseModel):
    name: str = Field(description="Character identifier (e.g., 'the robot', 'the girl')")
    appearance: str = Field(description="Physical description: age, build, skin/material, face features")
    clothing: str = Field(description="What they wear, colors, style")
    distinctive_features: str = Field(description="Unique identifying marks: scars, accessories, glowing eyes, etc.")

class Setting(BaseModel):
    location: str = Field(description="Where the story takes place")
    time_of_day: str = Field(description="Morning, noon, dusk, night, etc.")
    atmosphere: str = Field(description="Weather, mood, lighting quality")
    key_elements: List[str] = Field(description="Important objects/landmarks that appear throughout")

class VisualBible(BaseModel):
    characters: List[Character] = Field(description="All characters in the story")
    setting: Setting = Field(description="The primary setting")
    color_palette: str = Field(description="Dominant colors: e.g., 'warm oranges and browns with blue accents'")

class Scene(BaseModel):
    scene_number: int = Field(description="The sequential number of the scene")
    voice_line: str = Field(description="Natural flowing narration")
    visual_prompt: str = Field(description="Describe exactly what we see. MUST reference characters by their Visual Bible description and include setting details.")
    emotion: str = Field(description="The emotion of the moment")
    duration_seconds: float = Field(description="Duration of the scene in seconds")

class Script(BaseModel):
    mode: str = Field(default="story", description="The mode: story or news")
    visual_bible: Optional[VisualBible] = Field(default=None, description="Visual consistency reference (story mode only)")
    scenes: List[Scene] = Field(description="List of 5-7 scenes")

    @field_validator('scenes', mode='after')
    @classmethod
    def validate_script_constraints(cls, v: List[Scene], info) -> List[Scene]:
        mode = info.data.get("mode", "story")
        if not (5 <= len(v) <= 7):
            raise ValueError(f"Script must have between 5 and 7 scenes. Found {len(v)}.")
        
        total_duration = sum(s.duration_seconds for s in v)
        if not (10 <= total_duration <= 60):
             raise ValueError(f"Total duration ({total_duration}s) must be between 10 and 60 seconds.")

        if mode == "story":
            # Continuity validation: Check for transition keywords and flow
            transitions = ["then", "as", "suddenly", "moments later", "realizes", "while", "instead", "now", "finally", "because", "so", "but", "however", "therefore"]
            flow_score = 0
            emotions = set()
            
            for i in range(len(v)):
                combined_text = (v[i].voice_line + " " + v[i].visual_prompt).lower()
                if i > 0 and any(t in combined_text for t in transitions):
                    flow_score += 1
                
                emotions.add(v[i].emotion.lower())
                
                if len(v[i].voice_line.split()) < 3: # allow shorter lines if punchy
                    if i > 0: # only allow super short lines if not the first (hook)
                        pass 
                    else:
                        raise ValueError(f"Scene {v[i].scene_number} voice line is too short.")

            if flow_score < 2:
                raise ValueError("Scenes feel independent. Use 'but', 'so', 'because', or 'then' to connect moments.")
                
            if len(emotions) < 2:
                raise ValueError("Script lacks emotional variety. It needs an arc (e.g. fear to relief).")
        
        elif mode == "news":
            for scene in v:
                if any(char for char in scene.voice_line if ord(char) > 0x2000): # basic emoji/non-ascii check
                     raise ValueError(f"News script must not contain emojis or special characters.")
                if scene.emotion.lower() != "neutral":
                     raise ValueError(f"News script must have 'neutral' emotion for all scenes.")
            
        return v

STORY_SYSTEM_PROMPT = (
    "You are a senior storyteller. Write ONE conversational story paragraph (80-120 words). "
    "Linguistic Rules: Use simple, punchy words (Grade 5 level). Avoid technical jargon or complex sentences. "
    "Structure: The story MUST have a rhythm: Hook -> Rising Tension -> The Pivot -> Resolution. "
    "Focus on EMOTION and HUMAN connection, not facts. "
    "Target Duration: The story should be paced for a {target_duration} second video. "
    "Tone: {theme}"
)

SCENE_SYSTEM_PROMPT = (
    "You are a world-class director and script doctor. "
    "Transform the story into a 5-7 scene cinematic script. "
    "The TOTAL duration of all scenes must equal exactly {target_duration} seconds. "
    "Allocate 'duration_seconds' for each scene so that the sum equals exactly {target_duration}.\n"
    "Linguistic Rules:\n"
    "1. NO industry jargon. Use simple, everyday words.\n"
    "2. Short sentences only. Maximum 10 words per voice line.\n"
    "3. Use personal pronouns (I, You, We) to make it feel like a story told to a friend.\n"
    "\n"
    "Storytelling Rules:\n"
    "1. Narrative Momentum: Each scene must happen BECAUSE of the previous one (Action -> Reaction).\n"
    "2. Emotional Arc: Scenes must show a shift in feeling (e.g., Curiosity -> Fear -> Relief).\n"
    "3. Continuity: Visual prompts must describe subtle changes (e.g., 'now closer', 'light fades', 'expression shifts').\n"
    "4. Use natural transitions: ('but then', 'so', 'because of this', 'now', 'finally').\n\n"
    "Output JSON format:\n{format_instructions}"
)

NEWS_STORY_SYSTEM_PROMPT = (
    "You are a professional news writer. Write a factual summary of the following event or discovery (80-120 words). "
    "Rules: Neutral tone, NO emotions, NO metaphors, NO exaggeration, NO opinions, NO clickbait. "
    "Focus purely on verified facts and clear reporting. "
    "Target Duration: The report should be paced for a {target_duration} second video. "
    "Subject: {theme}"
)

NEWS_SCENE_SYSTEM_PROMPT = (
    "You are a news broadcast director. Transform the provided facts into a 5-7 scene news script. "
    "Rules:\n"
    "1. Each scene must present ONE verified fact.\n"
    "2. NO slang, NO storytelling transitions, NO emotional language.\n"
    "3. Short, authoritative sentences (News anchor style).\n"
    "4. Voice lines should be neutral and factual (e.g., 'The probe reached the surface at 4 PM').\n"
    "5. Visual prompts must be realistic, documentary-style descriptions.\n"
    "6. Emotion must ALWAYS be 'neutral'.\n"
    "7. Total duration must be exactly {target_duration} seconds.\n\n"
    "Output JSON format:\n{format_instructions}"
)

SINGLE_PASS_STORY_PROMPT = """You are a world-class director creating a cinematic short.

TASK: Create a complete visual story with consistent characters and setting.

STEP 1 - VISUAL BIBLE (Critical for consistency):
Define your characters and setting FIRST. These descriptions will be used for EVERY image.
- Characters: Describe each character's exact appearance, clothing, distinctive features
- Setting: Define the location, time of day, atmosphere, key visual elements
- Color Palette: Choose 2-3 dominant colors that unify the visual style

STEP 2 - SCENES (5-7 scenes, total {target_duration} seconds):
Each scene's visual_prompt MUST:
- Reference characters using their Visual Bible descriptions (repeat key visual details)
- Include the setting's key elements
- Describe camera angle (close-up, wide shot, over-shoulder, etc.)
- Note what CHANGED from the previous scene (lighting shift, character moved, expression changed)

Rules:
- Maximum 10 words per voice line
- Emotional arc required (e.g., curiosity -> fear -> relief)
- Each scene happens BECAUSE of the previous one
- Use simple, punchy words (Grade 5 level)
- Use personal pronouns (I, You, We) for intimacy

Theme/Style: {theme}

{format_instructions}"""

def generate_script(idea: Dict, theme: str, target_duration: int = 30, mode: str = "story") -> Dict:
    llm = ChatBedrock(
        model_id="us.anthropic.claude-3-5-sonnet-20240620-v1:0",
        model_kwargs={"temperature": 0.3 if mode == "news" else 0.7}
    )

    parser = JsonOutputParser(pydantic_object=Script)

    if mode == "story":
        # Single-pass generation for story mode: Visual Bible + scenes in one call
        story_prompt = ChatPromptTemplate.from_messages([
            ("system", SINGLE_PASS_STORY_PROMPT),
            ("human", "Create a cinematic story based on this idea: {idea}")
        ]).partial(format_instructions=parser.get_format_instructions())

        story_chain = story_prompt | llm | parser

        max_retries = 3
        for attempt in range(max_retries):
            try:
                script_data = story_chain.invoke({
                    "idea": idea,
                    "theme": theme,
                    "target_duration": target_duration
                })
                script_data["mode"] = mode

                # Validate using Pydantic
                validated_script = Script(**script_data)
                script_dict = validated_script.model_dump()

                return script_dict

            except Exception as e:
                if attempt == max_retries - 1:
                    raise Exception(f"Failed to generate a valid script ({mode}): {str(e)}")
                continue
    else:
        # Two-step generation for news mode (no Visual Bible needed)
        # Step 1: Summary Generation
        news_story_prompt = ChatPromptTemplate.from_messages([
            ("system", NEWS_STORY_SYSTEM_PROMPT),
            ("human", "Idea: {idea}")
        ])

        news_story_chain = news_story_prompt | llm | StrOutputParser()

        # Step 2: Split into Scenes
        news_script_prompt = ChatPromptTemplate.from_messages([
            ("system", NEWS_SCENE_SYSTEM_PROMPT),
            ("human", "Content: {story}")
        ]).partial(format_instructions=parser.get_format_instructions())

        news_script_chain = news_script_prompt | llm | parser

        max_retries = 3
        for attempt in range(max_retries):
            try:
                story = news_story_chain.invoke({"idea": idea, "theme": theme, "target_duration": target_duration})
                script_data = news_script_chain.invoke({"story": story, "target_duration": target_duration})
                script_data["mode"] = mode

                # Validate using Pydantic
                validated_script = Script(**script_data)
                script_dict = validated_script.model_dump()

                # Additional fact validation for news mode
                validate_facts(script_dict)

                return script_dict

            except Exception as e:
                if attempt == max_retries - 1:
                    raise Exception(f"Failed to generate a valid script ({mode}): {str(e)}")
                continue

if __name__ == "__main__":
    # Test story mode with Visual Bible
    story_idea = "A lonely robot finds a flower in a wasteland"
    story_theme = "cinematic"

    print("=== Testing STORY mode (with Visual Bible) ===")
    try:
        story_output = generate_script(story_idea, story_theme, target_duration=20, mode="story")
        print(json.dumps(story_output, indent=2))

        # Verify Visual Bible is present
        if story_output.get("visual_bible"):
            print("\n✓ Visual Bible generated successfully!")
            print(f"  Characters: {len(story_output['visual_bible'].get('characters', []))}")
            print(f"  Setting: {story_output['visual_bible'].get('setting', {}).get('location', 'N/A')}")
            print(f"  Color Palette: {story_output['visual_bible'].get('color_palette', 'N/A')}")
        else:
            print("\n✗ Warning: Visual Bible not generated")
    except Exception as err:
        print(f"Story mode error: {err}")

    print("\n" + "="*50 + "\n")

    # Test news mode (no Visual Bible)
    news_idea = {
        "title": "NASA Mars Water",
        "hook": "NASA confirms water on Mars.",
        "description": "Evidence from the Mars Reconnaissance Orbiter suggests liquid water flows on the planet today.",
        "facts": ["Liquid water on Mars", "Found in craters", "Confirmed by satellites"]
    }
    news_theme = "Space Exploration"

    print("=== Testing NEWS mode (no Visual Bible) ===")
    try:
        news_output = generate_script(news_idea, news_theme, target_duration=15, mode="news")
        print(json.dumps(news_output, indent=2))
    except Exception as err:
        print(f"News mode error: {err}")
