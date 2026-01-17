import json
import os
from typing import List, Dict
from dotenv import load_dotenv
from langchain_aws import ChatBedrock
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field, field_validator

load_dotenv()

class Scene(BaseModel):
    scene_number: int = Field(description="The sequential number of the scene")
    on_screen_text: str = Field(description="Text to be displayed on the screen")
    voice_line: str = Field(description="The line spoken in this scene")
    visual_prompt: str = Field(description="Description of the visual elements")
    duration_seconds: float = Field(description="Duration of the scene in seconds")

class Script(BaseModel):
    scenes: List[Scene] = Field(description="List of scenes in the script")

    @field_validator('scenes')
    @classmethod
    def validate_total_duration(cls, scenes: List[Scene]) -> List[Scene]:
        total_duration = sum(scene.duration_seconds for scene in scenes)
        if not (20 <= total_duration <= 30):
            raise ValueError(f"Total script duration must be between 20 and 30 seconds. Current duration: {total_duration:.2f}s")
        return scenes

def generate_script(idea: Dict, theme: str) -> Dict:
    llm = ChatBedrock(
        model_id="us.anthropic.claude-3-5-sonnet-20240620-v1:0",
        model_kwargs={"temperature": 0.7}
    )

    parser = JsonOutputParser(pydantic_object=Script)

    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a professional scriptwriter. Generate a high-engagement, scene-by-scene script. "
                  "The tone and vocabulary must strictly match the provided theme. "
                  "The total duration of all scenes must be between 20 and 30 seconds. "
                  "Provide the script in the specified JSON format."),
        ("human", "Idea: {idea}\nTheme: {theme}\n\n{format_instructions}")
    ]).partial(format_instructions=parser.get_format_instructions())

    chain = prompt | llm | parser

    try:
        response = chain.invoke({"idea": idea, "theme": theme})
        # Explicitly validate using the Pydantic model
        validated_script = Script(**response)
        return validated_script.model_dump()
    except Exception as e:
        # Re-raise validation errors or handle general exceptions
        raise e

if __name__ == "__main__":
    example_idea = {
        "title": "The One-Tab Challenge for Devs",
        "hook": "Can you code with just one browser tab?",
        "description": "Present a challenge to work on a coding task using only one browser tab. Demonstrate techniques like using browser bookmarks efficiently, leveraging IDE features, and mastering keyboard shortcuts to navigate between resources without opening multiple tabs.",
        "tone": "Challenging and encouraging"
    }
    example_theme = "Technical Productivity"
    
    try:
        script_output = generate_script(example_idea, example_theme)
        print(json.dumps(script_output, indent=2))
    except Exception as err:
        print(f"Error: {err}")
