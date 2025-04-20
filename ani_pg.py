import os
from openai import OpenAI
from PIL import Image
import requests
from io import BytesIO

# Initialize OpenAI client
client = OpenAI(api_key="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")  # Replace with your actual API key

def generate_animated_version(input_image_path, output_path, prompt_addition=""):
    """
    Generates an animated-style version of an input photo using OpenAI's API.
    
    Args:
        input_image_path (str): Path to the input image file
        output_path (str): Where to save the result
        prompt_addition (str): Additional instructions for the animation
    """
    
    # Create a prompt for animation
    base_prompt = "Transform this photograph into Studio Ghibli animation style. Maintain the subject's likeness and basic composition, but render it with Ghibli's characteristic soft color palette, hand-painted textures, and slightly simplified features. Add subtle Ghibli elements like gentle lighting, slightly exaggerated expressions, and a warm atmosphere. The final image should look like a still from a Ghibli film while still being recognizable as the original subject."
    full_prompt = f"{base_prompt} {prompt_addition}".strip()
    
    try:
        # Call OpenAI API - using text-to-image generation
        response = client.images.generate(
            model="dall-e-3",  # or "dall-e-2"
            prompt=full_prompt,
            n=1,
            size="1024x1024",
            quality="standard",  # or "hd" for higher quality
            style="vivid"  # or "natural"
        )
        
        # Get the generated image URL
        image_url = response.data[0].url
        
        # Download and save the image
        response = requests.get(image_url)
        img = Image.open(BytesIO(response.content))
        img.save(output_path)
        print(f"Animated-style image saved to {output_path}")
        
    except Exception as e:
        print(f"Error generating animated image: {e}")

# Example usage
if __name__ == "__main__":
    input_photo = "king_khan.jpg"  # This is now only used for reference
    output_file = "animated_version.png"
    additional_instructions = "Full body Image"
    
    generate_animated_version(input_image_path=input_photo, 
                           output_path=output_file, 
                           prompt_addition=additional_instructions)