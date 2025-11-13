import os
from PIL import Image, ImageDraw
import replicate
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def add_puzzle_grid(image, grid_size=(8, 8)):
    """Add a simple grid overlay to simulate puzzle pieces"""
    draw = ImageDraw.Draw(image)
    width, height = image.size
    rows, cols = grid_size

    # Draw vertical lines
    for i in range(1, cols):
        x = i * (width // cols)
        draw.line([(x, 0), (x, height)], fill=(0, 0, 0), width=3)

    # Draw horizontal lines
    for i in range(1, rows):
        y = i * (height // rows)
        draw.line([(0, y), (width, y)], fill=(0, 0, 0), width=3)

    return image

def transform_person_to_character(image_path, character_theme):
    """
    STEP 1: Transform person into a character based on theme
    Uses ByteDance SeerAI Dream-4 model
    """
    print(f"👤 STEP 1: Transforming person into {character_theme} character...")
    print(f"   Prompt: {character_theme}")

    # Pass file handle directly - Replicate will handle upload
    print("   Processing image...")
    output = replicate.run(
        "bytedance/seedream-4",
        input={
            "prompt": character_theme,
            "image_input": [open(image_path, "rb")],  # Pass file handle directly
            "size": "1K",
            "aspect_ratio": "match_input_image",
            "enhance_prompt": True
        }
    )

    return output

def place_character_in_world(character_image_path, world_prompt):
    """
    STEP 2: Place the character into a magical world scene
    Uses ByteDance SeerAI Dream-4 model
    """
    print(f"🌍 STEP 2: Placing character into magical world...")
    print(f"   Prompt: {world_prompt}")

    # Pass file handle directly - Replicate will handle upload
    print("   Processing character image...")
    output = replicate.run(
        "bytedance/seedream-4",
        input={
            "prompt": world_prompt,
            "image_input": [open(character_image_path, "rb")],  # Pass file handle directly
            "size": "1K",
            "aspect_ratio": "match_input_image",
            "enhance_prompt": True
        }
    )

    return output

def create_magical_puzzle(input_path, output_path, character_theme=None, world_prompt=None):
    """
    Main function: Load image → Transform to character → Place in world → Add puzzle grid → Save

    Args:
        input_path: Path to the person's photo
        output_path: Where to save the final puzzle
        character_theme: Theme for character transformation (e.g., "fairy tale princess with sparkles")
        world_prompt: Description of the magical world scene (e.g., "enchanted forest with castle")
    """
    import requests
    from io import BytesIO

    print(f"🚀 Starting two-step magical puzzle creation...")
    print(f"   Input: {input_path}")

    # Step 1: Load and validate image
    print("📂 Loading image...")
    img = Image.open(input_path)

    # Convert to RGB if needed (handles transparency)
    if img.mode != 'RGB':
        print("   Converting to RGB...")
        img = img.convert('RGB')

    # Resize if too large (save API costs)
    max_size = 1024
    if max(img.size) > max_size:
        print(f"   Resizing to max {max_size}px...")
        img.thumbnail((max_size, max_size))

    # Save temp file for API
    temp_path = "output/temp_input.jpg"
    os.makedirs("output", exist_ok=True)
    img.save(temp_path, quality=95)

    # Step 2: AI Transformation (Two-step process)
    if character_theme and world_prompt:
        try:
            # STEP 1: Transform person to character
            print("\n" + "="*60)
            character_url = transform_person_to_character(temp_path, character_theme)

            # Download character image
            print("⬇️  Downloading character image...")
            if isinstance(character_url, list):
                character_url = character_url[0]

            # LESSON LEARNED: Replicate API returns different types depending on version/config
            # - Might be a plain string URL
            # - Might be a FileOutput object with .url() method
            # - Might be a FileOutput object with .url property (not callable)
            # Always handle all three cases to avoid "'str' object is not callable" errors
            if isinstance(character_url, str):
                image_url = character_url
            elif hasattr(character_url, 'url'):
                # Check if url is a method or property
                url_attr = getattr(character_url, 'url')
                if callable(url_attr):
                    image_url = url_attr()
                else:
                    image_url = url_attr
            else:
                image_url = str(character_url)

            response = requests.get(image_url)
            character_img = Image.open(BytesIO(response.content))

            # Save intermediate character image
            character_path = "output/character_intermediate.png"
            character_img.save(character_path, quality=95)
            print(f"✅ Character transformation complete! Saved to {character_path}")

            # STEP 2: Place character in magical world
            print("\n" + "="*60)
            world_url = place_character_in_world(character_path, world_prompt)

            # Download final world image
            print("⬇️  Downloading final magical world image...")
            if isinstance(world_url, list):
                world_url = world_url[0]

            # Get URL - handle multiple cases
            if isinstance(world_url, str):
                image_url = world_url
            elif hasattr(world_url, 'url'):
                # Check if url is a method or property
                url_attr = getattr(world_url, 'url')
                if callable(url_attr):
                    image_url = url_attr()
                else:
                    image_url = url_attr
            else:
                image_url = str(world_url)

            response = requests.get(image_url)
            img = Image.open(BytesIO(response.content))
            print("✅ World placement complete!")
            print("="*60 + "\n")

        except Exception as e:
            print(f"⚠️  AI transformation failed: {e}")
            print("   Continuing with original image...")

    elif character_theme or world_prompt:
        print("⚠️  Warning: Both character_theme AND world_prompt required for AI transformation")
        print("   Skipping AI transformation...")

    # Step 3: Add puzzle grid overlay
    print("🧩 Adding puzzle grid...")
    img = add_puzzle_grid(img, grid_size=(8, 8))

    # Step 4: Save final result
    print(f"💾 Saving final puzzle to {output_path}...")
    img.save(output_path, quality=95)

    print("✨ Done! Your magical puzzle is ready!")
    return output_path

if __name__ == "__main__":
    # Example usage
    INPUT_IMAGE = "input/charlie-test.jpeg"  # Change this to your test image
    OUTPUT_IMAGE = "output/magical_puzzle.png"

    # Two-step AI transformation
    # Step 1: Transform person into a character
    CHARACTER_THEME = "Create an 8-bit character card in the theme of fairy tale prince with magical outfit, crown, sparkles, fantasy style. It should be a full person, standing face on like a pokemon card for example."

    # Step 2: Place character in a magical world
    WORLD_SCENE = "Place this 8-bit character into enchanted forest with glowing castle in background, magical atmosphere, vibrant fantasy colors, ethereal lighting surrounded by magical wildlife. This image will be used as a puzzle so it needs to be full of life and varied and high quality"

    # Run the full pipeline
    create_magical_puzzle(
        input_path=INPUT_IMAGE,
        output_path=OUTPUT_IMAGE,
        character_theme=CHARACTER_THEME,
        world_prompt=WORLD_SCENE
    )
