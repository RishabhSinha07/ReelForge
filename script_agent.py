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

class Script(BaseModel):
    scenes: List[Scene] = Field(description="List of 5-7 scenes")

    @field_validator('scenes')
    @classmethod
    def validate_script_constraints(cls, v: List[Scene]) -> List[Scene]:
        if not (5 <= len(v) <= 7):
            raise ValueError(f"Script must have between 5 and 7 scenes. Found {len(v)}.")
        
        # Continuity validation: Check for transition keywords and flow
        transitions = ["then", "as ", "suddenly", "moments later", "realizes", "while", "instead", "now", "finally"]
        flow_score = 0
        for i in range(1, len(v)):
            combined_text = (v[i].voice_line + " " + v[i].visual_prompt).lower()
            if any(t in combined_text for t in transitions):
                flow_score += 1
            
            # Check for direct reference to previous scene in voice line (lightly)
            # or simply ensure they don't look like standalone facts.
            if len(v[i].voice_line.split()) < 5:
                raise ValueError(f"Scene {v[i].scene_number} voice line is too short to be part of a flow.")

        if flow_score < (len(v) // 2):
            raise ValueError("Scenes feel independent. Ensure narrative flow with transition phrases and references to previous moments.")
            
        return v

def generate_script(idea: Dict, theme: str) -> Dict:
    llm = ChatBedrock(
        model_id="us.anthropic.claude-3-5-sonnet-20240620-v1:0",
        model_kwargs={"temperature": 0.7}
    )

    # Step 1: Story Generation (Focus on Hook, Conflict, Turning Point, Resolution)
    story_prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a senior screenwriter. Write ONE complete story paragraph (80-120 words) for a short film. "
                  "The story MUST include a high-stakes hook, a clear conflict, a dramatic turning point, and a satisfying resolution. "
                  "Tone: {theme}"),
        ("human", "Idea: {idea}")
    ])
    
    story_chain = story_prompt | llm | StrOutputParser()
    
    # Step 2: Split Story into Scenes
    parser = JsonOutputParser(pydantic_object=Script)
    script_prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a director. Transform the provided story into a 5-7 scene cinematic script. "
                  "CONTINUITY RULES:\n"
                  "1. NO jumps in time. Each scene must start exactly where the previous one ended.\n"
                  "2. NO repeated information. Don't restate what we just saw or heard.\n"
                  "3. Each scene MUST reference the previous moment to maintain flow.\n"
                  "4. Use transition phrases in narration: ('then', 'as he realizes', 'suddenly', 'moments later', etc.).\n"
                  "5. Visual prompts must be specific and maintain subject/setting consistency.\n"
                  "6. Each scene must feel like a movie cut, not a bullet point.\n\n"
                  "Output JSON format:\n{format_instructions}"),
        ("human", "Story: {story}")
    ]).partial(format_instructions=parser.get_format_instructions())
    
    script_chain = script_prompt | llm | parser

    max_retries = 3
    for attempt in range(max_retries):
        try:
            story = story_chain.invoke({"idea": idea, "theme": theme})
            script_data = script_chain.invoke({"story": story})
            
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
        output = generate_script(example_idea, example_theme)
        print(json.dumps(output, indent=2))
    except Exception as err:
        print(f"Error: {err}")
