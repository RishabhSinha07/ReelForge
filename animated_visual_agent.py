import os
import json
import base64
import time
import random
import uuid
import boto3
import requests
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()

class AnimatedVisualAgent:
    """
    Generates animated video clips using Amazon Nova Reel 1.1.

    Creates 6-second video clips per scene with character animation,
    using reference images for consistency.
    """

    def __init__(self):
        self.region = os.getenv("AWS_REGION", "us-east-1")
        self.bedrock_runtime = boto3.client(
            service_name="bedrock-runtime",
            region_name=self.region
        )
        self.s3_client = boto3.client("s3", region_name=self.region)
        self.model_id = os.getenv("NOVA_REEL_MODEL_ID", "amazon.nova-reel-v1:1")
        self.s3_bucket = os.getenv("S3_BUCKET_NAME", "reelforge-video-output")
        self.s3_prefix = os.getenv("S3_VIDEO_PREFIX", "generated-videos/")
        self.base_output_dir = "output"

    def generate_scene_videos(
        self,
        video_plan: Dict,
        character_bibles: Dict,
        reel_name: str
    ) -> List[str]:
        """
        Generate animated video clips for all scenes.

        Args:
            video_plan: Dictionary with scene plans from PlannerAgent
            character_bibles: Character visual bible collection
            reel_name: Name for organizing output

        Returns:
            List of file paths to generated video clips
        """
        scenes = video_plan.get("scenes", [])
        generated_videos = []

        videos_dir = os.path.join(self.base_output_dir, reel_name, "videos")
        os.makedirs(videos_dir, exist_ok=True)

        print(f"\n=== Generating {len(scenes)} animated video clips ===")

        for i, scene in enumerate(scenes):
            scene_num = scene.get("scene_number")
            print(f"\nScene {scene_num}:")

            try:
                video_path = self.generate_scene_video(
                    scene=scene,
                    character_bibles=character_bibles,
                    reel_name=reel_name
                )
                generated_videos.append(video_path)
                print(f"  ✓ Video saved: {video_path}")

                # Add delay between scenes to avoid rate limits (except after last scene)
                if i < len(scenes) - 1:
                    delay = 5  # 5 seconds between scenes
                    print(f"  Waiting {delay}s before next scene...")
                    time.sleep(delay)

            except Exception as e:
                print(f"  ✗ Error generating scene {scene_num}: {e}")
                raise

        return generated_videos

    def generate_scene_video(
        self,
        scene: Dict,
        character_bibles: Dict,
        reel_name: str
    ) -> str:
        """
        Generate a single animated video clip using Nova Reel.

        Args:
            scene: Scene plan with action_prompt, characters, camera_movement
            character_bibles: Character visual bible for reference
            reel_name: Name for organizing output

        Returns:
            File path to generated video
        """
        scene_num = scene.get("scene_number")

        # Build video prompt
        video_prompt = self._build_video_prompt(scene, character_bibles)

        # Truncate to 512 chars max (Nova Reel limit)
        if len(video_prompt) > 512:
            video_prompt = video_prompt[:509] + "..."
            print(f"  Prompt truncated to 512 chars")

        print(f"  Prompt ({len(video_prompt)} chars): {video_prompt[:100]}...")

        # Get character reference image (if available)
        character_ref_path = self._get_character_reference(
            scene.get("characters", []),
            character_bibles,
            reel_name
        )

        # Prepare Nova Reel request
        s3_output_uri = f"s3://{self.s3_bucket}/{self.s3_prefix}{reel_name}/scene_{scene_num}/"

        model_input = {
            "taskType": "TEXT_VIDEO",
            "textToVideoParams": {
                "text": video_prompt
            },
            "videoGenerationConfig": {
                "fps": 24,
                "dimension": "1280x720",  # Nova Reel only supports horizontal (will crop to vertical later)
                "seed": random.randint(0, 2147483646),
                "durationSeconds": 6
            }
        }

        # Reference images must be 1280x720 (horizontal) for Nova Reel
        # For now, skip reference images - rely on detailed text prompts for consistency
        # TODO: Generate horizontal reference images at 1280x720
        # if character_ref_path and os.path.exists(character_ref_path):
        #     print(f"  Using reference image: {os.path.basename(character_ref_path)}")
        #     with open(character_ref_path, "rb") as f:
        #         image_bytes = base64.b64encode(f.read()).decode('utf-8')
        #     model_input["textToVideoParams"]["images"] = [{
        #         "format": "png",
        #         "source": {"bytes": image_bytes}
        #     }]

        # Start async job
        print(f"  Starting Nova Reel generation (this takes 14-17 minutes)...")

        try:
            # Use direct HTTP request (boto3's start_async_invoke doesn't work)
            invocation_arn = self._start_async_invoke_direct(model_input, s3_output_uri)
            print(f"  Job ARN: {invocation_arn}")

            # Poll S3 for completion
            video_path = self._poll_and_download(
                s3_output_uri,
                reel_name,
                scene_num
            )

            return video_path

        except Exception as e:
            print(f"  Error in Nova Reel API call: {e}")
            raise

    def _build_video_prompt(self, scene: Dict, character_bibles: Dict) -> str:
        """
        Build detailed video generation prompt.

        Args:
            scene: Scene plan with action and camera info
            character_bibles: Character descriptions

        Returns:
            Formatted prompt string for Nova Reel
        """
        # Get character prompt templates
        characters = scene.get("characters", [])
        action = scene.get("action_prompt", scene.get("action", ""))
        camera = scene.get("camera_movement", scene.get("camera", "static"))

        # Find character in bible
        char_prompts = []
        for char_name in characters:
            for char_bible in character_bibles.get("characters", []):
                if char_bible["name"] == char_name:
                    template = char_bible.get("nova_reel_prompt_template", "")
                    if template:
                        # Replace [ACTION] placeholder with actual action
                        char_prompt = template.replace("[ACTION]", action)
                        char_prompts.append(char_prompt)
                        break

        # If no character templates found, use basic action
        if not char_prompts:
            base_prompt = action
        else:
            base_prompt = ", ".join(char_prompts)

        # Add camera movement
        camera_instruction = f"Camera: {camera}."

        # Add style and quality
        style = "Cinematic, high quality, professional animation, 9:16 vertical format."

        return f"{base_prompt} {camera_instruction} {style}"

    def _get_character_reference(
        self,
        characters: List[str],
        character_bibles: Dict,
        reel_name: str
    ) -> Optional[str]:
        """
        Get reference image path for character consistency.

        Args:
            characters: List of character names in scene
            character_bibles: Character visual bible collection
            reel_name: Name for finding files

        Returns:
            Path to reference image, or None if not found
        """
        if not characters:
            return None

        # Use first character's reference image
        char_name = characters[0]

        # Find in character bibles
        for char_bible in character_bibles.get("characters", []):
            if char_bible["name"] == char_name:
                ref_images = char_bible.get("reference_images", [])
                if ref_images:
                    # Prefer the "reference" view, otherwise use first
                    for img in ref_images:
                        if "reference" in img:
                            return img
                    return ref_images[0]

        return None

    def _start_async_invoke_direct(
        self,
        model_input: Dict,
        s3_output_uri: str
    ) -> str:
        """
        Start async invocation using direct HTTP request (boto3 method doesn't work).

        Args:
            model_input: Model input parameters
            s3_output_uri: S3 URI for output

        Returns:
            Invocation ARN
        """
        # Build request body exactly like AWS console
        body = {
            "modelId": f"arn:aws:bedrock:{self.region}::foundation-model/{self.model_id}",
            "modelInput": model_input,
            "outputDataConfig": {
                "s3OutputDataConfig": {
                    "s3Uri": s3_output_uri
                }
            },
            "clientRequestToken": str(uuid.uuid4())
        }

        url = f"https://bedrock-runtime.{self.region}.amazonaws.com/async-invoke"

        # Sign request
        session = boto3.Session()
        credentials = session.get_credentials()

        request = AWSRequest(
            method='POST',
            url=url,
            data=json.dumps(body),
            headers={'Content-Type': 'application/json'}
        )
        SigV4Auth(credentials, 'bedrock', self.region).add_auth(request)

        # Make request with retry logic for rate limits
        max_retries = 5
        base_delay = 10  # Start with 10 seconds

        for attempt in range(max_retries):
            response = requests.post(url, data=json.dumps(body), headers=dict(request.headers))

            if response.status_code == 200:
                result = response.json()
                return result["invocationArn"]

            elif response.status_code == 429:
                # Rate limit hit - wait and retry with exponential backoff
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)  # 10s, 20s, 40s, 80s, 160s
                    print(f"  Rate limit hit (429). Retrying in {delay}s... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                else:
                    raise Exception(f"Nova Reel API failed after {max_retries} attempts: {response.status_code} - {response.text}")

            else:
                # Other error - fail immediately
                raise Exception(f"Nova Reel API failed: {response.status_code} - {response.text}")

        raise Exception("Nova Reel API failed: Max retries exceeded")

    def _poll_and_download(
        self,
        s3_output_uri: str,
        reel_name: str,
        scene_num: int,
        poll_interval: int = 30,
        max_wait: int = 1200  # 20 minutes max
    ) -> str:
        """
        Poll S3 for video generation completion and download.

        Args:
            s3_output_uri: S3 URI where video will be saved
            reel_name: Name for organizing output
            scene_num: Scene number
            poll_interval: Seconds between polls
            max_wait: Maximum seconds to wait

        Returns:
            Local file path to downloaded video
        """
        # Parse S3 URI
        s3_path = s3_output_uri.replace(f"s3://{self.s3_bucket}/", "")

        print(f"  Polling S3: s3://{self.s3_bucket}/{s3_path}")

        start_time = time.time()
        attempts = 0

        while time.time() - start_time < max_wait:
            attempts += 1

            try:
                # List objects in output path
                response = self.s3_client.list_objects_v2(
                    Bucket=self.s3_bucket,
                    Prefix=s3_path
                )

                if "Contents" in response:
                    # Look for video file (usually .mp4)
                    for obj in response["Contents"]:
                        key = obj["Key"]
                        if key.endswith(".mp4"):
                            print(f"  ✓ Video found in S3: {key}")

                            # Download to local
                            local_path = os.path.join(
                                self.base_output_dir,
                                reel_name,
                                "videos",
                                f"scene_{scene_num}.mp4"
                            )

                            self.s3_client.download_file(
                                self.s3_bucket,
                                key,
                                local_path
                            )

                            print(f"  ✓ Downloaded to: {local_path}")
                            return local_path

            except Exception as e:
                print(f"  Poll attempt {attempts} - checking S3: {str(e)[:50]}...")

            # Wait before next poll
            elapsed = int(time.time() - start_time)
            print(f"  Waiting... ({elapsed}s / {max_wait}s)")
            time.sleep(poll_interval)

        raise TimeoutError(f"Video generation timed out after {max_wait} seconds")

if __name__ == "__main__":
    # Test with example scene
    test_video_plan = {
        "scenes": [
            {
                "scene_number": 1,
                "characters": ["ROBO-7"],
                "action_prompt": "ROBO-7 wakes up in a barren wasteland, looks around confused",
                "camera_movement": "slow zoom in",
                "duration_seconds": 6
            }
        ]
    }

    test_character_bibles = {
        "characters": [
            {
                "name": "ROBO-7",
                "nova_reel_prompt_template": "ROBO-7, a small rusty robot with glowing blue eyes and antenna ears, [ACTION]",
                "reference_images": ["output/test_robot_journey/characters/robo_7_reference.png"]
            }
        ]
    }

    agent = AnimatedVisualAgent()

    print("=== Animated Visual Agent Test ===")
    print("NOTE: This will take 14-17 minutes per scene!")
    print("\nGenerating test video...")

    try:
        videos = agent.generate_scene_videos(
            video_plan=test_video_plan,
            character_bibles=test_character_bibles,
            reel_name="test_robot_journey"
        )

        print(f"\n✓ Generated videos: {videos}")

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        print("\nNote: Ensure S3 bucket exists and AWS credentials are configured")
