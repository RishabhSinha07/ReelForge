import os
import json
import boto3
from typing import Dict, List
from dotenv import load_dotenv

load_dotenv()

class VoiceAgent:
    def __init__(self, voice_id: str = "Justin", engine: str = "neural"):
        self.region = os.getenv("AWS_REGION", "us-east-1")
        self.polly = boto3.client("polly", region_name=self.region)
        self.voice_id = voice_id
        self.engine = engine
        self.base_output_dir = "output"

        # Character-to-voice mapping for animated reels
        self.character_voice_mapping = {
            "ROBO-7": "Matthew",      # Deeper male voice for robot
            "ROBOT": "Matthew",
            "GIRL": "Joanna",         # Female voice for young girl
            "BOY": "Justin",          # Male voice for boy
            "WOMAN": "Joanna",
            "MAN": "Matthew",
            "NARRATOR": "Justin"
        }

    def generate_speech_marks(self, text: str, text_type: str = "text") -> str:
        """
        Calls Amazon Polly to generate word-level speech marks for the given text.
        """
        try:
            response = self.polly.synthesize_speech(
                Text=text,
                OutputFormat="json",
                VoiceId=self.voice_id,
                Engine=self.engine,
                TextType=text_type,
                SpeechMarkTypes=["word"]
            )
            
            if "AudioStream" in response:
                return response["AudioStream"].read().decode("utf-8")
        except Exception as e:
            print(f"Error generating speech marks: {e}")
        return ""

    def generate_audio(self, script_json: Dict, reel_name: str, mode: str = "story") -> List[str]:
        generated_files = []
        scenes = script_json.get("scenes", [])
        
        audio_dir = os.path.join(self.base_output_dir, reel_name, "audio")
        os.makedirs(audio_dir, exist_ok=True)
        
        for scene in scenes:
            scene_num = scene.get("scene_number")
            
            if "voice_line" not in scene:
                raise ValueError(f"Missing voice_line field in scene {scene_num}")
                
            voice_line = scene.get("voice_line")
            
            if not voice_line or not voice_line.strip():
                continue
                
            try:
                text_to_synthesize = voice_line
                text_type = "text"
                
                if mode == "news":
                    # Use SSML for news mode to ensure a slower, professional pace
                    text_to_synthesize = f"<speak><prosody rate='slow'>{voice_line}</prosody></speak>"
                    text_type = "ssml"

                response = self.polly.synthesize_speech(
                    Text=text_to_synthesize,
                    OutputFormat="mp3",
                    VoiceId=self.voice_id,
                    Engine=self.engine,
                    TextType=text_type
                )
                
                file_path = os.path.join(audio_dir, f"scene_{scene_num}.mp3")
                if "AudioStream" in response:
                    with open(file_path, "wb") as f:
                        f.write(response["AudioStream"].read())
                    
                    # Generate and save speech marks
                    speech_marks = self.generate_speech_marks(text_to_synthesize, text_type)
                    if speech_marks:
                        speechmarks_path = f"{file_path}_speechmarks.json"
                        with open(speechmarks_path, "w") as f:
                            f.write(speech_marks)
                    
                    generated_files.append(file_path)
            except Exception as e:
                print(f"Error generating audio for scene {scene_num}: {e}")

        return generated_files

    def generate_audio_for_animated_scenes(
        self,
        parsed_script: Dict,
        reel_name: str,
        mode: str = "story"
    ) -> List[Dict]:
        """
        Generate audio with character-specific voices and viseme data.

        Args:
            parsed_script: Output from ScriptParserAgent with scenes
            reel_name: Name for organizing output
            mode: "story" or "news"

        Returns:
            List of dictionaries with audio_path, speech_marks, visemes, character
        """
        generated_audio = []
        scenes = parsed_script.get("scenes", [])

        audio_dir = os.path.join(self.base_output_dir, reel_name, "audio")
        os.makedirs(audio_dir, exist_ok=True)

        print(f"\n=== Generating audio for {len(scenes)} scenes ===")

        for scene in scenes:
            scene_num = scene.get("scene_number")
            characters = scene.get("characters", [])
            dialogue = scene.get("dialogue", "")

            if not dialogue or not dialogue.strip():
                print(f"\nScene {scene_num}: No dialogue, skipping")
                continue

            # Determine character and voice
            character_name = characters[0] if characters else "NARRATOR"
            voice_id = self._get_voice_for_character(character_name)

            print(f"\nScene {scene_num}: {character_name} ({voice_id})")
            print(f"  Dialogue: {dialogue[:50]}...")

            try:
                audio_data = self.generate_audio_with_visemes(
                    dialogue=dialogue,
                    character_name=character_name,
                    voice_id=voice_id,
                    scene_num=scene_num,
                    reel_name=reel_name,
                    mode=mode
                )

                generated_audio.append(audio_data)
                print(f"  ✓ Audio generated")

            except Exception as e:
                print(f"  ✗ Error: {e}")
                raise

        return generated_audio

    def generate_audio_with_visemes(
        self,
        dialogue: str,
        character_name: str,
        voice_id: str,
        scene_num: int,
        reel_name: str,
        mode: str = "story"
    ) -> Dict:
        """
        Generate audio, speech marks, and visemes for a character.

        Args:
            dialogue: Character dialogue text
            character_name: Character name
            voice_id: Polly voice ID
            scene_num: Scene number
            reel_name: Name for organizing output
            mode: "story" or "news"

        Returns:
            Dictionary with audio_path, speech_marks_path, visemes_path, character
        """
        audio_dir = os.path.join(self.base_output_dir, reel_name, "audio")

        # Prepare text for synthesis
        text_to_synthesize = dialogue
        text_type = "text"

        if mode == "news":
            text_to_synthesize = f"<speak><prosody rate='slow'>{dialogue}</prosody></speak>"
            text_type = "ssml"

        # Generate audio
        audio_response = self.polly.synthesize_speech(
            Text=text_to_synthesize,
            OutputFormat="mp3",
            VoiceId=voice_id,
            Engine=self.engine,
            TextType=text_type
        )

        # Safe character name for filename
        safe_char_name = character_name.replace(" ", "_").replace("-", "_")
        file_base = os.path.join(audio_dir, f"scene_{scene_num}_{safe_char_name}")

        # Save audio
        audio_path = f"{file_base}.mp3"
        with open(audio_path, "wb") as f:
            f.write(audio_response["AudioStream"].read())

        # Generate speech marks (word-level timing)
        speech_marks = self.generate_speech_marks(text_to_synthesize, text_type)
        speech_marks_path = f"{file_base}_speechmarks.json"

        with open(speech_marks_path, "w") as f:
            f.write(speech_marks)

        # Generate visemes (mouth shape data for future lip-sync)
        visemes = self._generate_visemes(text_to_synthesize, voice_id, text_type)
        visemes_path = f"{file_base}_visemes.json"

        with open(visemes_path, "w") as f:
            f.write(visemes)

        return {
            "audio_path": audio_path,
            "speech_marks_path": speech_marks_path,
            "visemes_path": visemes_path,
            "character": character_name,
            "scene_number": scene_num
        }

    def _get_voice_for_character(self, character_name: str) -> str:
        """
        Get Polly voice ID for a character.

        Args:
            character_name: Character name

        Returns:
            Polly voice ID
        """
        # Try exact match first
        if character_name in self.character_voice_mapping:
            return self.character_voice_mapping[character_name]

        # Try uppercase match
        upper_name = character_name.upper()
        if upper_name in self.character_voice_mapping:
            return self.character_voice_mapping[upper_name]

        # Default to narrator voice
        return self.voice_id

    def _generate_visemes(
        self,
        text: str,
        voice_id: str,
        text_type: str = "text"
    ) -> str:
        """
        Generate viseme data (mouth shapes) for lip-sync.

        Args:
            text: Text to synthesize
            voice_id: Polly voice ID
            text_type: "text" or "ssml"

        Returns:
            JSON string with viseme data
        """
        try:
            response = self.polly.synthesize_speech(
                Text=text,
                OutputFormat="json",
                VoiceId=voice_id,
                Engine=self.engine,
                TextType=text_type,
                SpeechMarkTypes=["viseme"]
            )

            if "AudioStream" in response:
                return response["AudioStream"].read().decode("utf-8")

        except Exception as e:
            print(f"    Warning: Could not generate visemes: {e}")

        return "[]"

if __name__ == "__main__":
    # Test legacy generate_audio
    example_script = {
        "scenes": [
            {
                "scene_number": 1,
                "voice_line": "Welcome to the world of AI agents."
            },
            {
                "scene_number": 2,
                "voice_line": "This is a voice-over generated by Amazon Polly."
            },
            {
                "scene_number": 3,
                "voice_line": ""
            }
        ]
    }

    print("=== Testing Legacy Voice Agent ===")
    agent = VoiceAgent()
    try:
        audio_files = agent.generate_audio(example_script, "example_reel_male_Matthew")
        print(f"Generated audio files: {audio_files}")
    except ValueError as e:
        print(f"Validation Error: {e}")

    # Test enhanced animated scenes
    print("\n=== Testing Enhanced Voice Agent (Animated) ===")

    test_parsed_script = {
        "scenes": [
            {
                "scene_number": 1,
                "characters": ["ROBO-7"],
                "dialogue": "Where... am I?",
                "action": "ROBO-7 wakes up in wasteland"
            },
            {
                "scene_number": 2,
                "characters": ["GIRL"],
                "dialogue": "Hey little guy! Are you lost?",
                "action": "Girl runs up to robot"
            }
        ]
    }

    enhanced_agent = VoiceAgent()
    try:
        audio_data = enhanced_agent.generate_audio_for_animated_scenes(
            test_parsed_script,
            "test_robot_journey",
            mode="story"
        )

        print("\n✓ Enhanced audio generated:")
        for data in audio_data:
            print(f"  Scene {data['scene_number']}: {data['character']}")
            print(f"    Audio: {data['audio_path']}")
            print(f"    Speech marks: {data['speech_marks_path']}")
            print(f"    Visemes: {data['visemes_path']}")

    except Exception as e:
        print(f"✗ Error: {e}")
