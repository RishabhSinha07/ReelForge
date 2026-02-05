import json
import os
from typing import List, Dict
from dotenv import load_dotenv
from langchain_aws import ChatBedrock
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

# Load environment variables from .env
load_dotenv()

class ReelIdea(BaseModel):
    title: str = Field(description="The catchy title of the reel idea")
    hook: str = Field(description="The first 3 seconds hook to grab attention")
    description: str = Field(description="Detailed explanation of the reel content (or list of facts for news)")
    tone: str = Field(description="The recommended tone for this specific idea")
    facts: List[str] = Field(default=[], description="3-5 key facts (required for news mode)")
    sources: List[str] = Field(default=[], description="Optional source hints (for news mode)")

class ReelIdeasResponse(BaseModel):
    ideas: List[ReelIdea]

class VideoScenePlan(BaseModel):
    """Video-optimized scene plan for animation generation"""
    scene_number: int = Field(description="Sequential scene number")
    characters: List[str] = Field(description="Character names appearing in this scene")
    action_prompt: str = Field(description="Detailed action description for video generation")
    camera_movement: str = Field(description="Camera instruction (zoom in, pan left, static, dolly)")
    character_references: List[str] = Field(description="Character distinctive features for consistency")
    duration_seconds: int = Field(description="Duration in multiples of 6 seconds")

class VideoScenePlanResponse(BaseModel):
    """Complete video plan for all scenes"""
    scenes: List[VideoScenePlan]

STORY_SYSTEM_PROMPT = (
    "You are a helpful social media assistant. "
    "Your task is to generate clear, engaging, and straightforward reel ideas based STRICTLY on the user's theme. "
    "Focus on literal interpretations and practical storytelling. "
    "Avoid poetic, flowery, or metaphorical language. Be direct and simple to understand. "
    "Each idea must have a clear hook and a logical progression. "
    "Use simple, conversational language in the descriptions. "
    "You must return the response in valid JSON format matching the schema provided."
)

NEWS_SYSTEM_PROMPT = (
    "You are a professional news editor. "
    "Your task is to generate factual, informative reel ideas based on current events or technical breakthroughs. "
    "NO storytelling, NO fiction, NO emotional exaggeration. "
    "For each idea: "
    "1. Generate a clear, straightforward headline. "
    "2. Provide 3-5 verified key facts. "
    "3. Provide optional source hints. "
    "Maintain a neutral, objective, and professional tone. "
    "You must return the response in valid JSON format matching the schema provided."
)

def generate_reel_ideas(count: int, theme: str, mode: str = "story") -> List[Dict]:
    # Use the Inference Profile ID (us. prefix) to support cross-region inference
    llm = ChatBedrock(
        model_id="us.anthropic.claude-3-5-sonnet-20240620-v1:0",
        model_kwargs={"temperature": 0.5 if mode == "news" else 0.7}
    )

    parser = JsonOutputParser(pydantic_object=ReelIdeasResponse)
    system_prompt = NEWS_SYSTEM_PROMPT if mode == "news" else STORY_SYSTEM_PROMPT

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "Generate {count} unique reel ideas based on the theme: '{theme}'.\n\n{format_instructions}")
    ]).partial(format_instructions=parser.get_format_instructions())

    chain = prompt | llm | parser

    try:
        response = chain.invoke({"count": count, "theme": theme})
        return response.get("ideas", [])
    except Exception as e:
        print(f"Error generating reel ideas: {e}")
        return []

def generate_video_plan(parsed_script: Dict, character_bibles: Dict, theme: str, reel_name: str = None) -> Dict:
    """
    Generate video-optimized scene plans for animation.

    Args:
        parsed_script: Output from ScriptParserAgent
        character_bibles: Output from CharacterDesignerAgent
        theme: Visual theme
        reel_name: Optional name for saving output

    Returns:
        Dictionary with video scene plans
    """
    llm = ChatBedrock(
        model_id="us.anthropic.claude-3-5-sonnet-20240620-v1:0",
        model_kwargs={"temperature": 0.4}  # Moderate creativity for planning
    )

    parser = JsonOutputParser(pydantic_object=VideoScenePlanResponse)

    system_prompt = """You are a professional film director planning animated video scenes.

Your task is to transform script scenes into detailed video generation plans.

GUIDELINES:
1. DESCRIBE CHARACTER ACTIONS in vivid detail (what they do, how they move, expressions)
2. SPECIFY CAMERA MOVEMENT that enhances the storytelling
   - Options: "zoom in", "zoom out", "pan left", "pan right", "static", "dolly forward", "dolly back", "wide shot", "close up"
3. INCLUDE CHARACTER DISTINCTIVE FEATURES from the visual bible in character_references
4. SET DURATION to multiples of 6 seconds (Nova Reel constraint)
   - Minimum 6 seconds
   - If scene needs more time, use 12, 18, or 24 seconds

ACTION PROMPT FORMAT:
- Start with character name and distinctive features
- Describe the action in present tense
- Include emotional tone and pacing
- Example: "ROBO-7, a small rusty robot with glowing blue eyes, slowly wakes up in a barren wasteland, head tilting side to side in confusion, antenna ears twitching"

CAMERA MOVEMENT GUIDELINES:
- Use dynamic camera work to enhance drama
- Match camera to emotion (zoom in for intimacy, wide shot for isolation, pan for reveal)
- Avoid static unless necessary

Return valid JSON matching the VideoScenePlanResponse schema."""

    # Build character reference lookup
    char_features = {}
    for char in character_bibles.get("characters", []):
        char_features[char["name"]] = char.get("distinctive_features", "")

    # Prepare scene context
    scenes_context = []
    for scene in parsed_script.get("scenes", []):
        char_refs = [char_features.get(c, "") for c in scene.get("characters", [])]
        scenes_context.append({
            "scene_number": scene["scene_number"],
            "characters": scene["characters"],
            "dialogue": scene["dialogue"],
            "action": scene["action"],
            "location": scene["location"],
            "camera": scene.get("camera", "static"),
            "character_features": char_refs,
            "duration_estimate": scene.get("duration_seconds", 6)
        })

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", """Theme: {theme}

Scenes to plan:
{scenes}

Transform these scenes into detailed video generation plans.

{format_instructions}""")
    ]).partial(format_instructions=parser.get_format_instructions())

    chain = prompt | llm | parser

    try:
        result = chain.invoke({
            "theme": theme,
            "scenes": json.dumps(scenes_context, indent=2)
        })

        # Save video plan if reel_name provided
        if reel_name:
            output_dir = os.path.join("output", reel_name)
            os.makedirs(output_dir, exist_ok=True)

            plan_path = os.path.join(output_dir, "video_plan.json")
            with open(plan_path, "w") as f:
                json.dump(result, f, indent=2)

            print(f"Video plan saved to: {plan_path}")

        return result

    except Exception as e:
        print(f"Error generating video plan: {e}")
        raise

if __name__ == "__main__":
    # Example usage for story mode
    print("--- Generating Story Reel Ideas ---")
    story_ideas = generate_reel_ideas(2, "The unexpected journey of a lost toy", mode="story")
    print(json.dumps(story_ideas, indent=2))

    print("\n--- Generating News Reel Ideas ---")
    news_ideas = generate_reel_ideas(1, "Breakthrough in AI-powered drug discovery", mode="news")
    print(json.dumps(news_ideas, indent=2))

    print("\n--- Testing Video Plan Generation ---")
    # Test video planning with parsed script
    test_parsed_script = {
        "scenes": [
            {
                "scene_number": 1,
                "characters": ["ROBO-7"],
                "dialogue": "Where... am I?",
                "action": "ROBO-7 wakes up in a barren wasteland, looks around confused",
                "location": "Wasteland at sunset",
                "camera": "Slow zoom in",
                "duration_seconds": 6
            }
        ]
    }

    test_character_bibles = {
        "characters": [
            {
                "name": "ROBO-7",
                "distinctive_features": "glowing blue eyes, antenna ears, rusty metal body"
            }
        ]
    }

    video_plan = generate_video_plan(
        test_parsed_script,
        test_character_bibles,
        "Cinematic Sci-Fi",
        "test_video_plan"
    )
    print(json.dumps(video_plan, indent=2))
