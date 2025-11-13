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

def transform_with_ai(image_path, prompt="magical fairy tale scene, enchanted forest, fantasy art style"):
    """Transform image using Replicate's Stable Diffusion"""
    print(f"🎨 Transforming image with AI...")
    print(f"   Prompt: {prompt}")

    # Use Stable Diffusion 3.5 for image-to-image transformation
    output = replicate.run(
        "stability-ai/stable-diffusion-3.5-large",
        input={
            "image": open(image_path, "rb"),
            "prompt": prompt,
            "prompt_strength": 0.6,  # 0.4 = preserve more original, 0.8 = more AI transformation
            "output_format": "png",
            "output_quality": 95
        }
    )

    return output

def create_magical_puzzle(input_path, output_path, transformation_prompt=None):
    """
    Main function: Load image → AI transform → Add puzzle grid → Save
    """
    print(f"🚀 Starting puzzle creation...")
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

    # Step 2: AI Transformation
    if transformation_prompt:
        try:
            result_url = transform_with_ai(temp_path, transformation_prompt)

            # Download transformed image
            print("⬇️  Downloading transformed image...")
            import requests
            from io import BytesIO

            if isinstance(result_url, list):
                result_url = result_url[0]

            response = requests.get(str(result_url))
            img = Image.open(BytesIO(response.content))
            print("✅ AI transformation complete!")

        except Exception as e:
            print(f"⚠️  AI transformation failed: {e}")
            print("   Continuing with original image...")

    # Step 3: Add puzzle grid overlay
    print("🧩 Adding puzzle grid...")
    img = add_puzzle_grid(img, grid_size=(8, 8))

    # Step 4: Save final result
    print(f"💾 Saving to {output_path}...")
    img.save(output_path, quality=95)

    print("✨ Done! Your magical puzzle is ready!")
    return output_path

if __name__ == "__main__":
    # Example usage
    INPUT_IMAGE = "input/family_photo.jpg"  # Change this to your test image
    OUTPUT_IMAGE = "output/magical_puzzle.png"

    # Run the full pipeline
    create_magical_puzzle(
        input_path=INPUT_IMAGE,
        output_path=OUTPUT_IMAGE,
        transformation_prompt="magical fairy tale scene, fantasy kingdom, vibrant colors, enchanted forest background"
    )
