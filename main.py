import streamlit as st
import os
import requests
import base64
import tempfile
import PyPDF2
import json
from PIL import Image
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
st.title("🎨 Ghibli-Style Storybook Generator")

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
            "model": "gpt-4-turbo",
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

def generate_ghibli_scene(child_description, animal_data, photo_description=None):
    """Generate Ghibli-style image of child with animal"""
    try:
        full_prompt = (
            f"Full-body Studio Ghibli-style watercolor illustration of {child_description} "
            f"interacting with a {animal_data['animal']}. {animal_data['interaction']}. "
            f"Soft colors, delicate features, dreamy atmosphere, detailed background, "
            f"whimsical details. Beautiful watercolor textures with visible brush strokes. "
            f"Full-body characters in dynamic poses showing the interaction clearly."
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
        st.error(f"Image generation failed: {str(e)}")
        return None

def create_storybook(name, gender, story_data, photo_description=None, user_image=None):
    """Create personalized Ghibli-style storybook from analyzed data"""
    pronouns = {
        'she/her': {'subject': 'she', 'object': 'her'},
        'he/him': {'subject': 'he', 'object': 'him'},
        'they/them': {'subject': 'they', 'object': 'them'}
    }
    
    # Debug: Print story data to verify we have multiple animals
    st.write(f"Creating storybook with {len(story_data)} animal interactions")
    
    # Create PDF buffer
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    
    # Cover Page with User Photo
    c.setFont("Helvetica-Bold", 24)
    c.drawCentredString(300, 750, f"{name}'s Ghibli Zoo Adventure")
    c.setFont("Helvetica", 16)
    c.drawCentredString(300, 700, "A magical Studio Ghibli-style story")
    
    if user_image:
        try:
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
                user_image.save(tmp.name, format='JPEG')
                tmp_path = tmp.name
            
            c.drawImage(tmp_path, 200, 400, width=200, height=200)
            os.unlink(tmp_path)
        except Exception as e:
            st.error(f"Error adding user photo: {str(e)}")
    
    c.showPage()
    
    # Story Pages
    child_description = f"{name}, a {gender.split('/')[0]} child" if name else "a child"
    
    # Add intro page
    c.setFont("Helvetica", 18)
    c.drawCentredString(300, 750, f"Once upon a time, {name} wrote to the zoo")
    c.drawCentredString(300, 720, "to send them a pet.")
    c.drawCentredString(300, 690, "And so the zoo began to send animals...")
    c.showPage()
    
    # Generate a page for each animal
    for i, animal_data in enumerate(story_data):
        st.write(f"Processing animal {i+1}/{len(story_data)}: {animal_data['animal']}")
        
        img_data = generate_ghibli_scene(
            child_description=child_description,
            animal_data=animal_data,
            photo_description=photo_description
        )
        
        # Text for this animal page
        c.setFont("Helvetica", 18)
        c.drawString(100, 750, f"They sent {name} a {animal_data['animal']}...")
        c.drawString(100, 720, f"but it was {animal_data['description']}!")
        c.drawString(100, 690, animal_data['interaction'])
        
        if img_data:
            try:
                img = Image.open(BytesIO(base64.b64decode(img_data)))
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                    img.save(tmp.name, format='PNG')
                    tmp_path = tmp.name
                
                c.drawImage(tmp_path, 100, 250, width=400, height=400)
                os.unlink(tmp_path)
            except Exception as e:
                st.error(f"Error adding illustration for {animal_data['animal']}: {str(e)}")
                c.drawString(300, 400, f"[Illustration not available]")
        else:
            c.drawString(300, 400, f"[Illustration not available]")
        
        c.showPage()  # Create a new page for the next animal
    
    # Final page
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(300, 700, "The End")
    c.setFont("Helvetica", 16)
    c.drawCentredString(300, 650, f"Hope you enjoyed your Ghibli adventure, {name}!")
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
                        "model": "gpt-4-turbo",
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
                        timeout=30
                    )
                    response.raise_for_status()
                    photo_description = response.json()["choices"][0]["message"]["content"]
                
                # Step 4: Create storybook
                st.write("Generating Ghibli-style illustrations and creating storybook...")
                pdf_buffer = create_storybook(
                    name if name else "Aanya",
                    gender,
                    story_data,
                    photo_description,
                    user_image
                )
                
                st.success("🎉 Your magical Ghibli storybook is ready!")
                st.download_button(
                    "⬇️ Download Storybook",
                    data=pdf_buffer,
                    file_name=f"{name or 'Aanya'}_ghibli_zoo_adventure.pdf",
                    mime="application/pdf"
                )
                
            except Exception as e:
                st.error(f"Error creating storybook: {str(e)}")
                st.exception(e)  # This will show the full traceback for debugging

st.markdown("""
### Features:
1. **Original Story Preservation**: Keeps the text from "Aanya Writes to the Zoo" intact
2. **Ghibli-Style Illustrations**: Full-body interactions in Studio Ghibli's beautiful watercolor style
3. **Personalization**: Option to change names and add your photo
4. **Dynamic Scenes**: Each animal interaction is illustrated with the child

Example output will show:
- The child clearly interacting with each animal
- Full-body characters in dynamic poses
- Dreamy Ghibli backgrounds and atmosphere
- Original story text with enhanced visuals
""")