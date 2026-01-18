import json
import os
from typing import List, Dict
from dotenv import load_dotenv
from langchain_aws import ChatBedrock
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from pydantic import BaseModel, Field, field_validator

load_dotenv()

class Scene(BaseModel):
    scene_number: int = Field(description="The sequential number of the scene")
    voice_line: str = Field(description="Natural flowing narration")
    visual_prompt: str = Field(description="Describe exactly what we see")
    emotion: str = Field(description="The emotion of the moment")
    duration_seconds: float = Field(description="Duration of the scene in seconds")

class Script(BaseModel):
    scenes: List[Scene] = Field(description="List of 5-7 scenes")

    @field_validator('scenes')
    @classmethod
    def validate_script_constraints(cls, v: List[Scene]) -> List[Scene]:
        if not (5 <= len(v) <= 7):
            raise ValueError(f"Script must have between 5 and 7 scenes. Found {len(v)}.")
        
        # Continuity validation: Check for transition keywords and flow
        transitions = ["then", "as", "suddenly", "moments later", "realizes", "while", "instead", "now", "finally", "because", "so", "but", "however", "therefore"]
        flow_score = 0
        emotions = set()
        total_duration = sum(s.duration_seconds for s in v)
        
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
        
        if not (10 <= total_duration <= 60): # Basic sanity check for duration
             raise ValueError(f"Total duration ({total_duration}s) must be between 10 and 60 seconds.")
            
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

def generate_script(idea: Dict, theme: str, target_duration: int = 30) -> Dict:
    llm = ChatBedrock(
        model_id="us.anthropic.claude-3-5-sonnet-20240620-v1:0",
        model_kwargs={"temperature": 0.7}
    )

    # Step 1: Story Generation
    story_prompt = ChatPromptTemplate.from_messages([
        ("system", STORY_SYSTEM_PROMPT),
        ("human", "Idea: {idea}")
    ])
    
    story_chain = story_prompt | llm | StrOutputParser()
    
    # Step 2: Split Story into Scenes
    parser = JsonOutputParser(pydantic_object=Script)
    script_prompt = ChatPromptTemplate.from_messages([
        ("system", SCENE_SYSTEM_PROMPT),
        ("human", "Story: {story}")
    ]).partial(format_instructions=parser.get_format_instructions())
    
    script_chain = script_prompt | llm | parser

    max_retries = 3
    for attempt in range(max_retries):
        try:
            story = story_chain.invoke({"idea": idea, "theme": theme, "target_duration": target_duration})
            script_data = script_chain.invoke({"story": story, "target_duration": target_duration})
            
            # Validate using Pydantic
            validated_script = Script(**script_data)
            return validated_script.model_dump()
            
        except Exception as e:
            if attempt == max_retries - 1:
                raise Exception(f"Failed to generate a continuous script: {str(e)}")
            continue

if __name__ == "__main__":
    example_idea = {
        "title": "The Golden Compass",
        "hook": "A compass that points to what you fear most.",
        "description": "An explorer in a dark cave discovers a compass that starts spinning wildly as a shadow approaches.",
        "tone": "Tense and atmospheric"
    }
    example_theme = "Mystery/Thriller"
    
    try:
        output = generate_script(example_idea, example_theme, target_duration=15)
        print(json.dumps(output, indent=2))
    except Exception as err:
        print(f"Error: {err}")
