# ReelForge 🎬

**ReelForge** is an automated AI-powered pipeline designed to transform simple ideas into high-quality Instagram Reels. It orchestrates multiple specialized AI agents to handle planning, scripting, visual generation, voice-over synthesis, and video assembly.

---

## 🌟 Features

- **🧠 Smart Planning**: Generates structured content plans from a single idea.
- **✍️ Narrative Scripting**: Uses **Claude 3.5 Sonnet** to create cinematic, continuous stories (5-7 scenes) with smooth transitions.
- **🎨 AI Visuals**: Generates high-quality vertical images using **Amazon Nova Canvas** tailored to your chosen theme (Cinematic, Cartoon, Cyberpunk, etc.).
- **🎙️ Neural Voice-over**: Produces professional narration using **Amazon Polly** (Neural engine).
- **🎬 Automated Assembly**: Composes the final MP4 video (1080x1920) with cross-fade transitions, synced audio, and proper frame rates using **MoviePy**.

---

## 🚀 Getting Started

### Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) (recommended for dependency management)
- AWS Account with access to:
  - Amazon Bedrock (Claude 3.5 Sonnet & Nova Canvas)
  - Amazon Polly

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/RishabhSinha07/ReelForge.git
   cd ReelForge
   ```

2. **Setup environment variables**:
   Create a `.env` file in the root directory:
   ```env
   AWS_ACCESS_KEY_ID=your_access_key
   AWS_SECRET_ACCESS_KEY=your_secret_key
   AWS_REGION=us-east-1
   # Add any other required keys
   ```

3. **Install dependencies**:
   Using `uv`:
   ```bash
   uv sync
   ```
   Or using `pip`:
   ```bash
   pip install -r requirements.txt
   ```

---

## 🛠️ Usage

Run the `reel_orchestrator.py` script with your idea, theme, and a name for the output folder:

```bash
python reel_orchestrator.py "A lonely robot finding a flower in a wasteland" "Cinematic" "robot_flower"
```

### Arguments:
1. `reel_idea`: The core concept or story hook.
2. `theme`: Style of the video (e.g., `Cinematic`, `Cartoon`, `Cyberpunk`, `Corporate`, `Sketch`).
3. `reel_name`: The name of the output directory where all assets will be stored.

---

## 📂 Project Structure

- `reel_orchestrator.py`: The main entry point that coordinates all agents.
- `planner_agent.py`: Initial brainstorming and structure.
- `script_agent.py`: Storytelling and scene breakdown (Claude 3.5).
- `visual_agent.py`: Image generation (Nova Canvas).
- `voice_agent.py`: Audio synthesis (Polly).
- `video_agent.py`: Video composition (MoviePy).
- `output/`: Directory where generated reels, assets (images/audio), and scripts are stored.

---

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.