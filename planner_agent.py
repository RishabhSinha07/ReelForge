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
    description: str = Field(description="Detailed explanation of the reel content")
    tone: str = Field(description="The recommended tone for this specific idea")

class ReelIdeasResponse(BaseModel):
    ideas: List[ReelIdea]

def generate_reel_ideas(count: int, theme: str) -> List[Dict]:
    # Use the Inference Profile ID (us. prefix) to support cross-region inference
    # This addresses the 'on-demand throughput isn't supported' error.
    llm = ChatBedrock(
        model_id="us.anthropic.claude-3-5-sonnet-20240620-v1:0",
        model_kwargs={"temperature": 0.7}
    )

    parser = JsonOutputParser(pydantic_object=ReelIdeasResponse)

    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an expert social media strategist and content creator. "
                  "Your task is to generate viral-ready reel ideas that are highly engaging. "
                  "Adapt your tone and content style specifically to the provided theme to ensure resonance with the target audience. "
                  "You must return the response in valid JSON format matching the schema provided."),
        ("human", "Generate {count} unique reel ideas based on the theme: '{theme}'.\n\n{format_instructions}")
    ]).partial(format_instructions=parser.get_format_instructions())

    chain = prompt | llm | parser

    try:
        response = chain.invoke({"count": count, "theme": theme})
        return response.get("ideas", [])
    except Exception as e:
        print(f"Error generating reel ideas: {e}")
        return []

if __name__ == "__main__":
    # Example usage
    # sample_ideas = generate_reel_ideas(1, "Minimalist Productivity for Software Engineers")
    sample_ideas = generate_reel_ideas(1, "Colourful and fun with potatoes")
    print(json.dumps(sample_ideas, indent=2))
