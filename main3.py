import streamlit as st
import os
import requests
import base64
import tempfile
import PyPDF2
import json
import random
from PIL import Image
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph
from reportlab.lib.enums import TA_CENTER

# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
st.title("🎨 Ghibli-Style Storybook Generator")

# Pastel colors for page backgrounds
PASTEL_COLORS = [
    (1.0, 0.95, 0.95),  # Light pink
    (0.95, 1.0, 0.95),  # Light green
    (0.95, 0.95, 1.0),  # Light blue
    (1.0, 1.0, 0.95),  # Light yellow
    (1.0, 0.95, 1.0),  # Light purple
    (0.95, 1.0, 1.0),  # Light cyan
    (1.0, 0.98, 0.9),  # Light peach
    (0.97, 0.95, 1.0)   # Light lavender
]

# Consistent Fonts
TITLE_FONT = "Helvetica-Bold"
SUBTITLE_FONT = "Helvetica-BoldOblique"
BODY_FONT = "Helvetica"
EMPHASIS_FONT = "Helvetica-Oblique"

# Font Sizes
TITLE_SIZE = 28
SUBTITLE_SIZE = 22
BODY_SIZE = 18
SMALL_SIZE = 16
TINY_SIZE = 14

# Consistent Colors
TITLE_COLOR = (0.1, 0.2, 0.6)  # Dark blue
SUBTITLE_COLOR = (0.3, 0.3, 0.7)  # Medium blue
BODY_COLOR = (0.2, 0.2, 0.4)  # Dark slate
EMPHASIS_COLOR = (0.5, 0.1, 0.1)  # Dark red
ACCENT_COLOR = (0.7, 0.7, 0.9)  # Light purple blue

# Fonts and styles for reference (using consistent fonts now)
def get_custom_styles():
    styles = getSampleStyleSheet()
    
    # Title style
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Title'],
        fontName=TITLE_FONT,
        fontSize=TITLE_SIZE,
        leading=34,
        alignment=TA_CENTER,
        textColor=colors.darkblue
    )
    
    # Subtitle style
    subtitle_style = ParagraphStyle(
        'SubtitleStyle',
        parent=styles['Heading2'],
        fontName=SUBTITLE_FONT,
        fontSize=SUBTITLE_SIZE,
        leading=28,
        alignment=TA_CENTER,
        textColor=colors.darkslategray
    )
    
    # Story text style
    story_style = ParagraphStyle(
        'StoryStyle',
        parent=styles['Normal'],
        fontName=BODY_FONT,
        fontSize=BODY_SIZE,
        leading=24,
        textColor=colors.black
    )
    
    # Ending style
    ending_style = ParagraphStyle(
        'EndingStyle',
        parent=styles['Heading1'],
        fontName=TITLE_FONT,
        fontSize=SUBTITLE_SIZE,
        leading=30,
        alignment=TA_CENTER,
        textColor=colors.darkblue
    )
    
    return {
        'title': title_style,
        'subtitle': subtitle_style,
        'story': story_style,
        'ending': ending_style
    }

def extract_text_from_pdf(pdf_file):
    """Extract text from uploaded PDF"""
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        st.error(f"Error reading PDF: {str(e)}")
        return None

def analyze_story(story_text):
    """Analyze the story structure and extract animal interactions"""
    try:
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "gpt-4o",  # Updated from gpt-4-turbo
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": f"""
                    Analyze this children's story and extract the sequence of animal interactions.
                    Return a JSON object with a key called 'interactions' which contains an array where each element has:
                    - 'animal': the animal name
                    - 'description': why it wasn't suitable
                    - 'interaction': how the child interacts with it
                    
                    I need at least 4-6 different animal interactions from the story.
                    
                    Example format:
                    {{
                        "interactions": [
                            {{
                                "animal": "elephant",
                                "description": "too big",
                                "interaction": "The child measured the elephant with a tape measure"
                            }},
                            {{
                                "animal": "giraffe",
                                "description": "too tall",
                                "interaction": "The child looked up at the giraffe with wonder"
                            }},
                            ...and so on for all animals in the story
                        ]
                    }}
                    
                    Story:
                    {story_text}
                    """}
                ]
            }],
            "response_format": { "type": "json_object" },
            "max_tokens": 1000
        }
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        st.error(f"Story analysis failed: {str(e)}")
        return None

def generate_ghibli_child_base(child_description, photo_description=None):
    """Generate a consistent base image of the child in Ghibli style to be used across pages"""
    try:
        full_prompt = (
            f"Studio Ghibli-style watercolor illustration showing a full-body portrait of {child_description}. "
            f"The child should be standing in a gentle, neutral pose that can be easily combined with various animals. "
            f"Soft colors, delicate features, dreamy atmosphere, with visible watercolor textures and brush strokes. "
            f"Make sure the child has very consistent, recognizable features for use across multiple illustrations."
        )
        
        if photo_description:
            full_prompt += f" Child's distinctive features: {photo_description}"
        
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "dall-e-3",
            "prompt": full_prompt,
            "n": 1,
            "size": "1024x1024",
            "response_format": "b64_json",
            "style": "vivid"
        }
        response = requests.post(
            "https://api.openai.com/v1/images/generations",
            headers=headers,
            json=payload,
            timeout=60
        )
        response.raise_for_status()
        return response.json()["data"][0]["b64_json"]
    except Exception as e:
        st.error(f"Child base image generation failed: {str(e)}")
        return None

def generate_detailed_child_description(child_base_img_data, name, photo_description=None):
    """Generate a detailed description of the child from the base image to ensure consistency"""
    try:
        if not child_base_img_data:
            return None
            
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # Convert base64 data to image URL format for Vision API
        image_url = f"data:image/png;base64,{child_base_img_data}"
        
        payload = {
            "model": "gpt-4o",  # Updated from gpt-4-vision-preview
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": f"""
                    Please provide a VERY detailed description of how this Ghibli-style child looks.
                    Focus on all specific visual details that should be consistent across multiple illustrations:
                    - Exact hair style, color, and length
                    - Face shape and specific facial features
                    - Eye shape, size, and color
                    - Nose and mouth details
                    - Skin tone
                    - Body type and proportions
                    - Clothing details including colors, styles, and patterns
                    - Any distinctive accessories
                    
                    This description will be used to maintain consistent appearance across multiple images.
                    Be extremely specific about colors (use exact color names), shapes, and proportions.
                    """}, 
                    {"type": "image_url", "image_url": {"url": image_url}}
                ]
            }],
            "max_tokens": 1000
        }
        
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )
        response.raise_for_status()
        
        # Get the detailed description
        detailed_description = response.json()["choices"][0]["message"]["content"]
        
        # Incorporate photo description if available
        if photo_description:
            detailed_description += f"\n\nAdditional distinctive features from the reference photo: {photo_description}"
            
        return detailed_description
        
    except Exception as e:
        st.error(f"Error generating detailed child description: {str(e)}")
        # Provide fallback behavior to continue even if description fails
        return f"A child named {name} in Ghibli style with soft features and expressive eyes"

def generate_ghibli_scene(child_description, animal_data, photo_description=None, child_base_image=None, detailed_child_desc=None):
    """Generate Ghibli-style image of child with animal"""
    try:
        # Use the detailed child description if available
        child_reference = ""
        if detailed_child_desc:
            child_reference = (
                f"IMPORTANT: The child must look EXACTLY like this description to maintain consistency across "
                f"all illustrations: {detailed_child_desc}. "
                f"The child should be the SAME child in EVERY way as the previous illustrations. "
            )
        
        full_prompt = (
            f"Full-body Studio Ghibli-style watercolor illustration of {child_description} "
            f"interacting with a {animal_data['animal']}. {animal_data['interaction']}. "
            f"{child_reference}"
            f"Soft colors, delicate features, dreamy atmosphere, detailed background, "
            f"whimsical details. Beautiful watercolor textures with visible brush strokes. "
            f"Full-body characters in dynamic poses showing the interaction clearly."
        )
        
        if photo_description and not detailed_child_desc:
            full_prompt += f" Child's distinctive features: {photo_description}"
        
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "dall-e-3",
            "prompt": full_prompt,
            "n": 1,
            "size": "1024x1024",
            "response_format": "b64_json",
            "style": "vivid"
        }
        response = requests.post(
            "https://api.openai.com/v1/images/generations",
            headers=headers,
            json=payload,
            timeout=60
        )
        response.raise_for_status()
        return response.json()["data"][0]["b64_json"]
    except Exception as e:
        st.error(f"Image generation failed: {str(e)}")
        return None

def create_stylish_storybook(name, gender, story_data, photo_description=None, user_image=None):
    """Create personalized Ghibli-style storybook with colored pages and stylish text"""
    pronouns = {
        'she/her': {'subject': 'she', 'object': 'her', 'possessive': 'her'},
        'he/him': {'subject': 'he', 'object': 'him', 'possessive': 'his'},
        'they/them': {'subject': 'they', 'object': 'them', 'possessive': 'their'}
    }
    
    chosen_pronouns = pronouns[gender]
    
    # Debug: Print story data to verify we have multiple animals
    st.write(f"Creating storybook with {len(story_data)} animal interactions")
    
    # Create PDF buffer
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    
    # Get custom styles
    styles = get_custom_styles()
    
    # Shuffle pastel colors to use for pages
    page_colors = PASTEL_COLORS.copy()
    random.shuffle(page_colors)
    
    # Generate base child image for consistency
    child_description = f"{name}, a {gender.split('/')[0]} child" if name else "a child"
    child_base_img_data = generate_ghibli_child_base(
        child_description=child_description,
        photo_description=photo_description
    )
    
    # Display base child image for reference
    if child_base_img_data:
        st.write("Generated base child image for consistency:")
        base_img = Image.open(BytesIO(base64.b64decode(child_base_img_data)))
        st.image(base_img, caption="Base Child Image (Used for Consistency)", width=300)
        
        # Generate detailed child description for consistency across images
        detailed_child_desc = generate_detailed_child_description(
            child_base_img_data=child_base_img_data,
            name=name,
            photo_description=photo_description
        )
        
        if detailed_child_desc:
            st.write("Generated detailed child description for consistency across images")
        else:
            # Fallback description if the detailed one fails
            detailed_child_desc = f"A child named {name} with Ghibli-style features and expressive eyes"
            st.warning("Using simplified child description for consistency")
    else:
        detailed_child_desc = None
        st.warning("Could not generate base child image")
    
    # Cover Page with User Photo (Light gold background)
    c.setFillColorRGB(1.0, 0.98, 0.9)  # Light gold for cover
    c.rect(0, 0, letter[0], letter[1], fill=True)
    
    # Add decorative border to cover
    c.setStrokeColorRGB(0.8, 0.7, 0.3)  # Gold border
    c.setLineWidth(5)
    c.rect(20, 20, letter[0]-40, letter[1]-40, stroke=True)
    
    # Title with shadow effect
    title_text = f"{name}'s Magical Ghibli Zoo Adventure"
    c.setFillColorRGB(0.3, 0.3, 0.7)  # Shadow color
    c.setFont(TITLE_FONT, TITLE_SIZE)
    c.drawCentredString(302, 748, title_text)  # Shadow
    c.setFillColorRGB(*TITLE_COLOR)  # Title color
    c.drawCentredString(300, 750, title_text)  # Main title
    
    # Subtitle
    c.setFillColorRGB(0.3, 0.3, 0.3)
    c.setFont(SUBTITLE_FONT, SUBTITLE_SIZE)
    c.drawCentredString(300, 700, "A whimsical Studio Ghibli-style adventure")
    
    # Add decorative elements to cover
    c.setFillColorRGB(0.9, 0.8, 0.3)  # Gold stars
    for i in range(5):
        x = 100 + i * 100
        y = 650
        c.circle(x, y, 10, fill=True)
    
    if user_image:
        try:
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
                user_image.save(tmp.name, format='JPEG')
                tmp_path = tmp.name
            
            # Draw decorative frame around the image
            c.setFillColorRGB(1, 1, 1)  # White background for photo
            c.rect(175, 375, 250, 250, fill=True)
            
            # Draw the image
            c.drawImage(tmp_path, 200, 400, width=200, height=200)
            
            # Draw decorative frame border
            c.setStrokeColorRGB(0.3, 0.3, 0.7)  # Blue frame
            c.setLineWidth(3)
            c.rect(175, 375, 250, 250, stroke=True)
            
            os.unlink(tmp_path)
        except Exception as e:
            st.error(f"Error adding user photo: {str(e)}")
    
    # Created for text
    c.setFillColorRGB(0.3, 0.3, 0.3)
    c.setFont(EMPHASIS_FONT, TINY_SIZE)
    c.drawCentredString(300, 100, f"Created especially for {name}")
    c.drawCentredString(300, 80, "April 2025")
    
    c.showPage()
    
    # Story Pages
    # Add intro page with a different background color
    bg_color = page_colors[0]
    c.setFillColorRGB(*bg_color)
    c.rect(0, 0, letter[0], letter[1], fill=True)
    
    # Add decorative elements
    c.setStrokeColorRGB(0.5, 0.5, 0.8)
    c.setLineWidth(2)
    c.line(50, 680, 550, 680)
    c.line(50, 640, 550, 640)
    
    # Intro text with stylish formatting
    c.setFillColorRGB(*SUBTITLE_COLOR)
    c.setFont(TITLE_FONT, SUBTITLE_SIZE)
    c.drawCentredString(300, 750, "The Adventure Begins...")
    
    c.setFillColorRGB(*BODY_COLOR)
    c.setFont(BODY_FONT, BODY_SIZE)
    c.drawCentredString(300, 660, f"Once upon a time, in a house filled with dreams,")
    c.drawCentredString(300, 630, f"{name} wrote a special letter to the zoo.")
    c.drawCentredString(300, 600, f"{chosen_pronouns['subject'].capitalize()} asked them to send a perfect pet,")
    c.drawCentredString(300, 570, "and so their magical journey began...")
    
    # Add some decorative elements
    c.setFillColorRGB(*ACCENT_COLOR)
    c.circle(100, 500, 30, fill=True)
    c.circle(500, 500, 30, fill=True)
    
    # Add zoo image placeholder or decorative element
    c.setFillColorRGB(0.8, 0.8, 0.9)
    c.roundRect(150, 200, 300, 300, 20, fill=True)
    c.setFillColorRGB(*SUBTITLE_COLOR)
    c.setFont(TITLE_FONT, SUBTITLE_SIZE)
    c.drawCentredString(300, 350, "The Zoo")
    c.setFont(BODY_FONT, BODY_SIZE)
    c.drawCentredString(300, 310, "Where magical animals")
    c.drawCentredString(300, 280, "were waiting to be discovered...")
    
    c.showPage()
    
    # Generate a page for each animal with rotating background colors
    for i, animal_data in enumerate(story_data):
        st.write(f"Processing animal {i+1}/{len(story_data)}: {animal_data['animal']}")
        
        # Set background color for this page
        bg_color = page_colors[i % len(page_colors)]
        c.setFillColorRGB(*bg_color)
        c.rect(0, 0, letter[0], letter[1], fill=True)
        
        # Add decorative header
        c.setFillColorRGB(*SUBTITLE_COLOR)
        c.roundRect(50, 730, 500, 60, 10, fill=True)
        c.setFillColorRGB(1, 1, 1)
        c.setFont(TITLE_FONT, SUBTITLE_SIZE)
        c.drawCentredString(300, 760, f"The {animal_data['animal'].title()}")
        
        # Generate Ghibli-style illustration using same child base and detailed description
        img_data = generate_ghibli_scene(
            child_description=child_description,
            animal_data=animal_data,
            photo_description=photo_description,
            child_base_image=child_base_img_data,
            detailed_child_desc=detailed_child_desc
        )
        
        # Text for this animal page with consistent styling
        c.setFillColorRGB(*BODY_COLOR)
        c.setFont(BODY_FONT, BODY_SIZE)
        c.drawString(90, 700, f"They sent {name} a {animal_data['animal']}...")
        
        c.setFillColorRGB(*EMPHASIS_COLOR)
        c.setFont(TITLE_FONT, BODY_SIZE)
        c.drawString(100, 670, f"But it was {animal_data['description']}!")
        
        c.setFillColorRGB(*BODY_COLOR)
        c.setFont(EMPHASIS_FONT, BODY_SIZE)
        c.drawString(90, 640, animal_data['interaction'])
        
        # Add decorative divider
        c.setStrokeColorRGB(0.5, 0.5, 0.7)
        c.setLineWidth(2)
        c.line(100, 625, 500, 625)
        
        if img_data:
            try:
                img = Image.open(BytesIO(base64.b64decode(img_data)))
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                    img.save(tmp.name, format='PNG')
                    tmp_path = tmp.name
                
                # Create decorative frame for image
                c.setFillColorRGB(1, 1, 1)
                c.roundRect(75, 150, 450, 450, 10, fill=True)
                
                # Draw the image
                c.drawImage(tmp_path, 100, 175, width=400, height=400)
                
                # Add decorative frame border
                c.setStrokeColorRGB(0.5, 0.5, 0.7)
                c.setLineWidth(3)
                c.roundRect(75, 150, 450, 450, 10, stroke=True)
                
                os.unlink(tmp_path)
                
                # Show the image in the Streamlit UI for preview
                st.image(img, caption=f"Scene with {animal_data['animal']}", width=300)
                
            except Exception as e:
                st.error(f"Error adding illustration for {animal_data['animal']}: {str(e)}")
                c.drawString(300, 400, f"[Illustration not available]")
        else:
            c.drawString(300, 400, f"[Illustration not available]")
        
        # Add page number with decorative element
        c.setFillColorRGB(*SUBTITLE_COLOR)
        c.circle(550, 50, 20, fill=True)
        c.setFillColorRGB(1, 1, 1)
        c.setFont(TITLE_FONT, TINY_SIZE)
        c.drawCentredString(550, 45, str(i+1))
        
        c.showPage()  # Create a new page for the next animal
    
    # Final page with special background
    c.setFillColorRGB(0.95, 0.98, 1.0)  # Light blue background
    c.rect(0, 0, letter[0], letter[1], fill=True)
    
    # Add decorative elements
    c.setStrokeColorRGB(0.5, 0.6, 0.8)
    c.setLineWidth(4)
    c.rect(50, 50, letter[0]-100, letter[1]-100, stroke=True)
    
    # Inner decorative border
    c.setStrokeColorRGB(0.7, 0.8, 0.9)
    c.setLineWidth(2)
    c.rect(70, 70, letter[0]-140, letter[1]-140, stroke=True)
    
    # The End text with shadow effect
    c.setFillColorRGB(0.2, 0.3, 0.6)  # Shadow color
    c.setFont(TITLE_FONT, 36)
    c.drawCentredString(302, 698, "The End")  # Shadow
    c.setFillColorRGB(*TITLE_COLOR)  # Text color
    c.drawCentredString(300, 700, "The End")
    
    # Add stars around "The End"
    c.setFillColorRGB(*ACCENT_COLOR)
    star_positions = [(230, 700), (370, 700), (270, 650), (330, 650)]
    for x, y in star_positions:
        c.circle(x, y, 8, fill=True)
    
    # Final message
    c.setFillColorRGB(*BODY_COLOR)
    c.setFont(EMPHASIS_FONT, SUBTITLE_SIZE)
    c.drawCentredString(300, 600, f"And finally, they sent {name} a...")
    
    c.setFillColorRGB(0.2, 0.5, 0.3)
    c.setFont(TITLE_FONT, SUBTITLE_SIZE)
    c.drawCentredString(300, 550, "Perfect Pet!")
    
    c.setFillColorRGB(*BODY_COLOR)
    c.setFont(EMPHASIS_FONT, BODY_SIZE)
    c.drawCentredString(300, 500, f"It was just what {chosen_pronouns['subject']} wanted!")
    
    # Add decorative elements at the bottom
    c.setFillColorRGB(*ACCENT_COLOR)
    for i in range(5):
        x = 150 + i * 75
        y = 200
        c.circle(x, y, 15, fill=True)
    
    # Final message
    c.setFillColorRGB(*BODY_COLOR)
    c.setFont(BODY_FONT, SMALL_SIZE)
    c.drawCentredString(300, 120, f"Hope you enjoyed your magical Ghibli adventure, {name}!")
    c.setFont(EMPHASIS_FONT, TINY_SIZE)
    c.drawCentredString(300, 90, "Every story has a happy ending...")
    
    c.showPage()
    
    c.save()
    buffer.seek(0)
    return buffer

# Streamlit UI
st.markdown("## Upload Original Story PDF")
original_pdf = st.file_uploader("📄 Upload 'Aanya Writes to the Zoo' PDF:", type=["pdf"])

st.markdown("## Personalize Your Story")
name = st.text_input("👶 Child's Name (leave blank to keep original):", "Aanya")
gender = st.selectbox("🧑 Pronouns:", ["she/her", "he/him", "they/them"], index=0)
photo = st.file_uploader("📸 Upload Photo for Ghibli-style Adaptation (optional):", type=["jpg", "jpeg", "png"])

if st.button("✨ Create Ghibli Storybook"):
    if not original_pdf:
        st.warning("Please upload the original story PDF")
    elif not OPENAI_API_KEY:
        st.error("Missing OpenAI API key")
    else:
        with st.spinner("🎨 Creating your magical Ghibli storybook..."):
            try:
                # Step 1: Extract text from original PDF
                story_text = extract_text_from_pdf(original_pdf)
                if not story_text:
                    raise ValueError("Couldn't extract text from PDF")
                
                # Step 2: Analyze story structure
                st.write("Analyzing story structure...")
                analysis_result = analyze_story(story_text)
                if not analysis_result:
                    raise ValueError("Couldn't analyze story structure")
                
                # Parse JSON properly and handle the response structure
                parsed_data = json.loads(analysis_result)
                
                # Debug the structure
                st.write("API response structure:", parsed_data.keys())
                
                # Extract story data based on actual response structure
                if 'interactions' in parsed_data:
                    story_data = parsed_data['interactions']
                else:
                    # Fallback: try to find the first list in the response
                    for key, value in parsed_data.items():
                        if isinstance(value, list) and len(value) > 0:
                            story_data = value
                            break
                    else:
                        raise ValueError("Could not find animal interaction data in the API response")
                
                st.write(f"Found {len(story_data)} animal interactions")
                
                # Step 3: Process photo if provided
                photo_description = None
                user_image = None
                
                if photo:
                    user_image = Image.open(photo)
                    st.image(user_image, caption="Your Photo", width=200)
                    photo_bytes = photo.getvalue()
                    
                    # Get Ghibli-style adaptation notes
                    st.write("Analyzing photo for Ghibli-style adaptation...")
                    base64_image = base64.b64encode(photo_bytes).decode('utf-8')
                    headers = {
                        "Authorization": f"Bearer {OPENAI_API_KEY}",
                        "Content-Type": "application/json"
                    }
                    payload = {
                        "model": "gpt-4o",  # Updated from gpt-4-turbo
                        "messages": [{
                            "role": "user",
                            "content": [
                            {"type": "text", "text": "Describe the facial features in this photo that should be preserved when adapting to a Studio Ghibli art style. Focus on distinctive features."},
                                {"type": "image_url", "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }}
                            ]
                        }],
                        "max_tokens": 300
                    }
                    response = requests.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers=headers,
                        json=payload,
                        timeout=60
                    )
                    response.raise_for_status()
                    photo_description = response.json()["choices"][0]["message"]["content"]
                    st.write("Photo analysis complete!")
                
                # Step 4: Create the personalized storybook
                st.write("Generating Ghibli-style illustrations and creating storybook...")
                pdf_buffer = create_stylish_storybook(
                    name=name, 
                    gender=gender, 
                    story_data=story_data,
                    photo_description=photo_description,
                    user_image=user_image
                )
                
                # Step 5: Provide the PDF for download
                st.success("🎉 Your magical Ghibli storybook is ready!")
                st.download_button(
                    label="📕 Download Your Ghibli Storybook",
                    data=pdf_buffer,
                    file_name=f"{name}_Ghibli_Storybook.pdf",
                    mime="application/pdf"
                )
                
            except Exception as e:
                st.error(f"Error creating storybook: {str(e)}")
                import traceback
                st.error(traceback.format_exc())

# Add some helpful information and examples
st.markdown("---")
st.markdown("""
### How it works
1. Upload the original "Aanya Writes to the Zoo" story PDF
2. Enter your child's name and choose pronouns
3. Optionally upload a photo of your child to personalize the illustrations
4. Click "Create Ghibli Storybook" and wait for the magic to happen!
5. Download your personalized Ghibli-style storybook PDF

### About this app
This app transforms a classic children's story into a beautiful Studio Ghibli-style storybook with:
- Personalized character illustrations based on your child's photo
- Whimsical watercolor scenes in the iconic Ghibli art style
- Consistent character design across all pages
- Customized story text with your child's name and pronouns
- Decorative page layouts with pastel backgrounds

### Requirements
- An OpenAI API key with access to GPT-4o and DALL-E 3
- The original "Aanya Writes to the Zoo" story PDF
""")

# Add footer
st.markdown("---")
st.markdown("🎨 Created with ❤️ and the magic of AI")