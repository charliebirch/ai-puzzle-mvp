# AI Puzzle MVP

Transform family photos into magical puzzle scenes using AI! This project uses Stable Diffusion 3.5 to transform images and create custom puzzles.

## Folder Structure
```
ai-puzzle-mvp/
├── .env                    # API keys (don't commit!)
├── .env.example           # Template for environment variables
├── .gitignore
├── requirements.txt
├── README.md
├── src/
│   └── puzzle_maker.py   # Main puzzle creation script
├── input/                 # Put test images here
└── output/                # Generated puzzles go here
```

## Features

✅ Loads any image format
✅ Resizes if needed (saves API costs)
✅ AI transformation using Stable Diffusion 3.5
✅ Downloads transformed result
✅ Adds puzzle grid overlay
✅ High-quality output

## Setup Instructions

### 1. Clone and Navigate to Project
```bash
cd ai-puzzle-mvp
```

### 2. Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Set Up API Key

1. Get your Replicate API key from [replicate.com](https://replicate.com)
2. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```
3. Edit `.env` and add your API key:
   ```
   REPLICATE_API_TOKEN=r8_your_actual_key_here
   ```

### 5. Add Test Image
Put a test image (any format) in the `input/` folder. For example:
- `input/family_photo.jpg`
- `input/test.png`

### 6. Run the Script
```bash
python src/puzzle_maker.py
```

## How It Works

1. **Load Image**: Reads your input image and validates it
2. **Prepare**: Converts to RGB and resizes if needed (max 1024px)
3. **AI Transform**: Sends to Stable Diffusion 3.5 for magical transformation
4. **Download**: Retrieves the transformed image
5. **Add Grid**: Overlays an 8x8 puzzle grid
6. **Save**: Outputs high-quality PNG to `output/` folder

## Customization

Edit `src/puzzle_maker.py` to customize:

### Change Grid Size
```python
img = add_puzzle_grid(img, grid_size=(10, 10))  # 10x10 grid instead of 8x8
```

### Change Transformation Prompt
```python
create_magical_puzzle(
    input_path=INPUT_IMAGE,
    output_path=OUTPUT_IMAGE,
    transformation_prompt="underwater kingdom, mermaids, coral reef, vibrant ocean colors"
)
```

### Adjust AI Strength
```python
"prompt_strength": 0.4,  # More original image preserved
"prompt_strength": 0.8,  # More AI transformation
```

## Example Prompts

- `"magical fairy tale scene, fantasy kingdom, vibrant colors, enchanted forest background"`
- `"underwater kingdom, mermaids, coral reef, vibrant ocean colors"`
- `"space adventure, planets and stars, cosmic background"`
- `"medieval castle, knights and dragons, epic fantasy scene"`

## Troubleshooting

**API Error**: Make sure your `.env` file has the correct Replicate API token

**Module Not Found**: Activate virtual environment and run `pip install -r requirements.txt`

**Image Not Found**: Check that your test image is in the `input/` folder

**AI Transformation Fails**: The script will continue with the original image and just add the puzzle grid

## Next Steps

Future enhancements planned:
- Quality checks (resolution, contrast)
- Multiple transformation styles
- Better puzzle piece shapes (using piecemaker)
- Face preservation with ControlNet
- Batch processing multiple images
- Web interface

## Requirements

- Python 3.8+
- Replicate API key
- Internet connection for AI transformations

## License

MIT License - Feel free to use and modify!
