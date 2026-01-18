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

STORY_SYSTEM_PROMPT = (
    "You are an expert social media strategist and storyteller. "
    "Your task is to generate viral-ready reel ideas that focus on HUMAN EMOTION and RELATABLE STORIES. "
    "Avoid technical jargon or dry factual content. "
    "Each idea must have a strong emotional hook (fear, joy, curiosity, surprise) and a clear 'Before' and 'After' narrative potential. "
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

if __name__ == "__main__":
    # Example usage
    sample_ideas = generate_reel_ideas(1, "NASA Mars Discovery", mode="news")
    print(json.dumps(sample_ideas, indent=2))
