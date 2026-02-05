#!/usr/bin/env python3
"""
Complete Story-to-Reel Pipeline

One-command solution: Natural language story → Animated Instagram Reel

Usage:
    python3 create_reel.py --story "Your story here" --reel-name my_reel

    Or interactive mode:
    python3 create_reel.py
"""

import argparse
import sys
import subprocess
from story_to_script_agent import StoryToScriptAgent

def interactive_mode():
    """Interactive story input mode."""
    print("\n" + "="*60)
    print("🎬 ANIMATED REEL CREATOR - Interactive Mode")
    print("="*60 + "\n")

    # Get story
    print("Tell me your story (press Enter twice when done):")
    print("-" * 60)
    story_lines = []
    empty_count = 0
    while empty_count < 1:
        line = input()
        if line.strip():
            story_lines.append(line)
            empty_count = 0
        else:
            empty_count += 1

    story = " ".join(story_lines).strip()

    if not story:
        print("Error: No story provided!")
        return None

    print(f"\n✓ Story: {story[:100]}...\n")

    # Get characters (optional)
    print("Do you want to define characters? (y/n): ", end="")
    define_chars = input().strip().lower() == 'y'

    characters = {}
    if define_chars:
        print("\nEnter characters (name: description), blank line to finish:")
        while True:
            char_input = input("Character: ").strip()
            if not char_input:
                break
            if ':' in char_input:
                name, desc = char_input.split(':', 1)
                characters[name.strip()] = desc.strip()
            else:
                print("  Format: NAME: description")

    # Get theme
    print("\nTheme options:")
    print("  1. Cinematic (realistic, dramatic)")
    print("  2. Cartoon (Pixar-style)")
    print("  3. Cyberpunk (neon, futuristic)")
    print("  4. Sketch (hand-drawn)")
    print("  5. Corporate (clean, professional)")
    print("Choose (1-5) [default: 1]: ", end="")

    theme_choice = input().strip() or "1"
    themes = {
        "1": "Cinematic",
        "2": "Cartoon",
        "3": "Cyberpunk",
        "4": "Sketch",
        "5": "Corporate"
    }
    theme = themes.get(theme_choice, "Cinematic")

    # Get duration
    print("\nDuration:")
    print("  1. 15 seconds (2-3 scenes)")
    print("  2. 30 seconds (4-5 scenes)")
    print("  3. 60 seconds (8-10 scenes)")
    print("Choose (1-3) [default: 2]: ", end="")

    dur_choice = input().strip() or "2"
    durations = {
        "1": "15 seconds",
        "2": "30 seconds",
        "3": "60 seconds"
    }
    duration = durations.get(dur_choice, "30 seconds")

    # Get reel name
    print("\nReel name (letters/numbers/underscores): ", end="")
    reel_name = input().strip() or "my_reel"
    reel_name = reel_name.replace(' ', '_').replace('-', '_')

    return {
        "story": story,
        "characters": characters if characters else None,
        "theme": theme,
        "duration": duration,
        "reel_name": reel_name
    }


def create_reel_from_story(
    story: str,
    reel_name: str,
    characters: dict = None,
    theme: str = "Cinematic",
    duration: str = "30 seconds",
    auto_generate: bool = True
):
    """
    Complete pipeline: story → script → animated reel.

    Args:
        story: Natural language story
        reel_name: Name for output reel
        characters: Optional character definitions
        theme: Visual theme
        duration: Target duration
        auto_generate: If True, automatically generate reel after script
    """
    print("\n" + "="*60)
    print("🎬 CREATING ANIMATED REEL")
    print("="*60 + "\n")

    # Step 1: Generate script
    print("📝 Step 1/2: Generating script...")
    agent = StoryToScriptAgent()

    script_file = agent.story_to_reel(
        story=story,
        characters=characters,
        theme=theme,
        duration=duration,
        output_name=f"{reel_name}_script"
    )

    print(f"\n✓ Script saved: {script_file}")

    if not auto_generate:
        print("\nTo generate reel manually, run:")
        print(f"  python3 animated_reel_orchestrator.py {script_file} {reel_name} --theme {theme}")
        return script_file

    # Step 2: Generate animated reel
    print("\n" + "="*60)
    print("🎬 Step 2/2: Generating animated reel...")
    print("="*60)
    print(f"\n⏰ This will take 15-20 minutes (Nova Reel generation)")
    print(f"💰 Estimated cost: ~$2.20\n")

    print("Proceed with reel generation? (y/n): ", end="")
    confirm = input().strip().lower()

    if confirm != 'y':
        print("\nSkipped reel generation.")
        print(f"To generate later, run:")
        print(f"  python3 animated_reel_orchestrator.py {script_file} {reel_name} --theme {theme}")
        return script_file

    print("\n🚀 Starting reel generation...\n")

    # Run the orchestrator
    cmd = [
        "python3",
        "animated_reel_orchestrator.py",
        script_file,
        reel_name,
        "--theme",
        theme
    ]

    try:
        subprocess.run(cmd, check=True)

        print("\n" + "="*60)
        print("✅ ANIMATED REEL COMPLETE!")
        print("="*60)
        print(f"\n📁 Final video: output/{reel_name}/{reel_name}.mp4")
        print(f"\nTo watch:")
        print(f"  open output/{reel_name}/{reel_name}.mp4")

        return f"output/{reel_name}/{reel_name}.mp4"

    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error generating reel: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Create animated Instagram Reels from natural language stories"
    )
    parser.add_argument(
        "--story",
        help="Your story in natural language"
    )
    parser.add_argument(
        "--reel-name",
        help="Name for the output reel"
    )
    parser.add_argument(
        "--theme",
        default="Cinematic",
        choices=["Cinematic", "Cartoon", "Cyberpunk", "Sketch", "Corporate"],
        help="Visual theme"
    )
    parser.add_argument(
        "--duration",
        default="30 seconds",
        help="Target duration (e.g., '15 seconds', '30 seconds', '1 minute')"
    )
    parser.add_argument(
        "--character",
        action="append",
        help="Character in format 'NAME:Description' (can be used multiple times)"
    )
    parser.add_argument(
        "--script-only",
        action="store_true",
        help="Only generate script, don't create video"
    )

    args = parser.parse_args()

    # Interactive mode if no story provided
    if not args.story:
        config = interactive_mode()
        if not config:
            sys.exit(1)

        create_reel_from_story(
            story=config["story"],
            reel_name=config["reel_name"],
            characters=config["characters"],
            theme=config["theme"],
            duration=config["duration"],
            auto_generate=not args.script_only
        )
    else:
        # Command-line mode
        if not args.reel_name:
            print("Error: --reel-name is required when using --story")
            sys.exit(1)

        # Parse characters
        characters = {}
        if args.character:
            for char in args.character:
                if ':' in char:
                    name, desc = char.split(':', 1)
                    characters[name.strip()] = desc.strip()

        create_reel_from_story(
            story=args.story,
            reel_name=args.reel_name,
            characters=characters if characters else None,
            theme=args.theme,
            duration=args.duration,
            auto_generate=not args.script_only
        )


if __name__ == "__main__":
    main()
