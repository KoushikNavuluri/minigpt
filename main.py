import streamlit as st
import requests
import json
from datetime import datetime
import pandas as pd
import uuid
import io
import re
from PIL import Image
import base64


def download_chat_history():
    # Convert chat history to DataFrame
    chat_data = []
    for msg in st.session_state.messages:
        chat_data.append({
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'role': msg['role'],
            'content': msg['content']
        })
    
    df = pd.DataFrame(chat_data)
    
    
    csv = df.to_csv(index=False)
    json_str = df.to_json(orient='records', indent=2)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name=f"chat_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    
    with col2:
        st.download_button(
            label="Download JSON",
            data=json_str,
            file_name=f"chat_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )

def initiate_id():
    url = "https://duckduckgo.com/duckchat/v1/status"
    headers = {
        'accept': '*/*',
        'accept-language': 'en-US,en;q=0.8',
        'cache-control': 'no-store',
        'priority': 'u=1, i',
        'referer': 'https://duckduckgo.com/',
        'sec-ch-ua': '"Chromium";v="130", "Brave";v="130", "Not?A_Brand";v="99"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'sec-gpc': '1',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
        'x-vqd-accept': '1'
    }

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.headers.get("x-vqd-4")
    else:
        st.error(f"Error initiating session: {response.status_code}")
        return None

def reset_chat():
    # List of all session state keys to reset
    keys_to_reset = [
        'messages',
        'conversation_history',
        'show_chat',
        'user_name',
        'selected_model',
        'welcome_displayed'
    ]
    
    # Reset each key in session state
    for key in keys_to_reset:
        if key in st.session_state:
            del st.session_state[key]
    
    # Initialize fresh session state
    st.session_state.welcome_displayed = False
    st.session_state.show_chat = False
    st.session_state.messages = []
    st.session_state.conversation_history = []

    # Get a fresh VQD ID
    st.session_state.vqd_id = initiate_id()

def generate_image(prompt):
    url = "https://ai-api.magicstudio.com/api/ai-art-generator"
    anonymous_user_id = str(uuid.uuid4())
    
    payload = {
        'prompt': prompt,
        'output_format': 'bytes',
        'user_profile_id': 'null',
        'anonymous_user_id': anonymous_user_id
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:131.0) Gecko/20100101 Firefox/131.0',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Referer': 'https://magicstudio.com/ai-art-generator/',
        'Origin': 'https://magicstudio.com',
        'DNT': '1',
        'Sec-GPC': '1',
        'Connection': 'keep-alive',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-site',
        'Priority': 'u=0'
    }
    
    try:
        response = requests.post(url, headers=headers, data=payload)
        if response.status_code == 200:
            return response.content
        else:
            st.error(f"Error generating image: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Error generating image: {str(e)}")
        return None

def is_image_request(prompt):
    # List of keywords that might indicate an image generation request
    image_keywords = [
        "create image", "generate image", "draw", "create a picture",
        "make an image", "generate a picture", "create art", "generate art",
        "create a drawing", "make a picture", "visualize", "create visual",
        "make art", "design image", "create illustration", "generate illustration"
    ]
    
    prompt_lower = prompt.lower()
    return any(keyword in prompt_lower for keyword in image_keywords)

 
def send_message(prompt, conversation_history, selected_model):
    # Check if this is an image generation request
    if is_image_request(prompt):
        # Generate image
        image_data = generate_image(prompt)
        
        if image_data:
            # Store image data in session state
            if 'generated_images' not in st.session_state:
                st.session_state.generated_images = {}
            
            # Generate a unique ID for this image
            image_id = str(uuid.uuid4())
            st.session_state.generated_images[image_id] = image_data
            
            # Display the image
            display_image_message(image_data)
            
            # Return response with image ID
            response = f"""I've generated the image based on your request. 
<image_marker id="{image_id}">"""
            yield response
            return
        else:
            yield "Sorry, I wasn't able to generate the image. Please try again with a different prompt."
            return
    
    # Regular chat message handling
    url = "https://duckduckgo.com/duckchat/v1/chat"
    
    # Only add non-image messages to conversation history
    conversation_history.append({"role": "user", "content": prompt})
    
    payload = json.dumps({
        "model": selected_model,
        "messages": conversation_history
    })
    
    headers = {
        'accept': 'text/event-stream',
        'accept-language': 'en-US,en;q=0.8',
        'content-type': 'application/json',
        'cookie': 'dcm=3',
        'origin': 'https://duckduckgo.com',
        'priority': 'u=1, i',
        'referer': 'https://duckduckgo.com/',
        'sec-ch-ua': '"Chromium";v="130", "Brave";v="130", "Not?A_Brand";v="99"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'sec-gpc': '1',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
        'x-vqd-4': st.session_state.vqd_id
    }

    response = requests.post(url, headers=headers, data=payload, stream=True)

    new_vqd_id = response.headers.get("x-vqd-4")
    if new_vqd_id:
        st.session_state.vqd_id = new_vqd_id

    if response.status_code == 200:
        assistant_response = ""
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8').replace("data: ", "")
                if decoded_line == "[DONE]":
                    break

                try:
                    event_data = json.loads(decoded_line)
                    if 'message' in event_data:
                        fragment = event_data['message']
                        assistant_response += fragment
                        yield fragment
                except json.JSONDecodeError:
                    pass

        conversation_history.append({"role": "assistant", "content": assistant_response})
    else:
        st.error(f"Error: {response.status_code}")

def display_image_message(image_data):
    try:
        # Convert bytes to image
        image = Image.open(io.BytesIO(image_data))
        
        # Create columns for better layout
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            # Display the image with a nice border and shadow
            st.markdown("""
                <style>
                    .generated-image {
                        border-radius: 10px;
                        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
                        margin: 10px 0;
                    }
                </style>
            """, unsafe_allow_html=True)
            
            # Display the image
            st.image(image, use_column_width=True, caption="Generated Image")
            
            # Add download button
            buf = io.BytesIO()
            image.save(buf, format="PNG")
            byte_im = buf.getvalue()
            
            st.download_button(
                label="Download Image",
                data=byte_im,
                file_name=f"generated_image_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
                mime="image/png"
            )
    except Exception as e:
        st.error(f"Error displaying image: {str(e)}")

def render_message_with_images(message_content):
    # Check if message contains an image marker
    if '<image_marker' in message_content:
        # Extract image ID
        image_id_match = re.search(r'<image_marker id="([^"]+)">', message_content)
        if image_id_match and image_id_match.group(1) in st.session_state.generated_images:
            image_id = image_id_match.group(1)
            # Display the stored image
            display_image_message(st.session_state.generated_images[image_id])
            # Display the text part of the message
            clean_message = message_content.split('<image_marker')[0].strip()
            st.markdown(clean_message)
        else:
            st.markdown(message_content)
    else:
        st.markdown(message_content) 


def show_welcome_page():
    st.session_state.welcome_displayed = True
    
    
    st.markdown("""
    <style>         
    .gradient-border {
               
        border: 1px solid #9B7EBD;
        border-radius: 10px;
        padding: 1em;
        margin-bottom: 1em;
    }
    .support-button {
        border: 1px solid #B9E5E8;        
        display: inline-block;
        padding: 10px 20px;
        # background: linear-gradient(45deg, #FF5F6D, #FFC371);
        color: white;
        text-decoration: none;
        border-radius: 25px;
        font-weight: bold;
        text-align: center;
        margin: 10px 0;
        transition: transform 0.3s ease;
    }
    .support-button:hover {
        transform: translateY(-2px);
    }
    </style>
    """, unsafe_allow_html=True)
    
    
    left_col, right_col = st.columns([2, 1])
    
    with left_col:
        st.markdown("<h1 style='color: #1E88E5; margin-bottom: 0;'>Welcome to MiNi - GPT! ✨</h1>", unsafe_allow_html=True)
        st.markdown("""
        <div style='font-size: 1.1em; color: #666; margin-bottom: 2em;'>
            Get ready to chat with the most advanced AI models available! Share your thoughts and let the AI respond with clarity and creativity!
        </div>
        """, unsafe_allow_html=True)
        
        
        # User input form
        with st.container():
            st.markdown("""
            <style>
            .stTextInput > div > div > input {
                font-size: 1.1em;
                padding: 1em;
            }
                        
            .stSelectbox > div > div > select {
                font-size: 1.1em;
                padding: 0.5em;
            }
            </style>
            """, unsafe_allow_html=True)
            
            user_name = st.text_input("", placeholder="Enter your name to begin...", key="user_name_input" ,label_visibility="collapsed",autocomplete="off")
                
            
            model_options = {
                "GPT-4": "gpt-4o-mini",
                "Claude 3": "claude-3-haiku-20240307",
                "Meta Llama": "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
                "Mixtral":"mistralai/Mixtral-8x7B-Instruct-v0.1"
            }
            
            selected_model_name = st.selectbox(
                "",
                options=list(model_options.keys()),
                placeholder="Choose your AI companion"
            )
            
            if st.button("Start Chatting!", type="primary", use_container_width=True):
                if user_name:
                    st.session_state.user_name = user_name
                    st.session_state.selected_model = model_options[selected_model_name]
                    st.session_state.show_chat = True
                    st.rerun()
                else:
                    st.warning("Please enter your name to continue.")
    
    with right_col:
        st.markdown("### 🔥 Featured Models")
        for model, description in [
            ("ChatGPT (gpt-4o-mini)", "Your AI Companion - Dive into creative discussions and insightful Q&A!"),
    ("claude-3 (claude-3-haiku-20240307)", "The Conversationalist - Experience nuanced dialogue with a focus on understanding!"),
    ("Meta (meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo)", "The Creative Genius - Unleash your imagination with unique ideas and storytelling!"),
    ("Mixtral (mistralai/Mixtral-8x7B-Instruct-v0.1)", "The Poet - Craft elegant model to explore the beauty of concise expression!")
]:
            st.markdown(f"""
            <div class='gradient-border' style='background-color: #000;'>
                <strong>{model}</strong><br>
                <small style='color: #666;'>{description}</small>
            </div>
            """, unsafe_allow_html=True)
    
    # Bottom section
    st.markdown("---")
    col1, col2,col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        ### 🔐 Your Privacy Matters
        *We prioritize your privacy. Your interactions are secure and confidential.*
        """)
    
    with col2:
        st.markdown("""
        ### 🚀 Coming Soon
        - Web Search Integration
        - Image Generation
        - Prompt Spaces
        - And much more...! 😉
              
        """)

    with col3:
        st.markdown("""
    <div style='text-align: center; padding: 50px; color: #666; padding-left:0px'>
        <a href='https://buymeacoffee.com/koushiknavuluri' target='_blank' class='support-button'>
            ☕ Support My Work
        </a>
    </div>
    """, unsafe_allow_html=True)
            
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; padding: 10px; color: #666;'>
        Crafted with ❤️,
                <br>        
        <a href='https://github.com/koushiknavuluri' target='_blank' style='color: #1E88E5; text-decoration: none;'>
            <img src="https://w7.pngwing.com/pngs/646/324/png-transparent-github-computer-icons-github-logo-monochrome-head-thumbnail.png" 
                 style='width: 30px; height: 30px; opacity: 0.8; vertical-align: middle; 
                        border-radius: 50%; background: transparent; border: none; 
                        padding: 5px; box-shadow: 0 0 5px rgba(0, 0, 0, 0.2);'> 
           Koushik Navuluri.
        </a>     
    </div>
""", unsafe_allow_html=True)

def main():
    st.set_page_config(
        page_title="MiNi - GPT",
        page_icon="🤖",
        layout="wide"
        # initial_sidebar_state="expanded"
    )
    
    # Initialize session states
    if "welcome_displayed" not in st.session_state:
        st.session_state.welcome_displayed = False
    if "show_chat" not in st.session_state:
        st.session_state.show_chat = False
    if "user_name" not in st.session_state:
        st.session_state.user_name = None
    if "selected_model" not in st.session_state:
        st.session_state.selected_model = None
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "conversation_history" not in st.session_state:
        st.session_state.conversation_history = []
    if "vqd_id" not in st.session_state:
        st.session_state.vqd_id = initiate_id()

    
    if not st.session_state.show_chat:
        show_welcome_page()
        return

    # Main chat interface
    st.title(f"Hello, {st.session_state.user_name}! 👋")
    
    # Display model info
    model_display_name = {
        "gpt-4o-mini": "GPT-4",
        "claude-3-haiku-20240307": "Claude 3",
        "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo": "Meta Llama",
        "mistralai/Mixtral-8x7B-Instruct-v0.1": "Mixtral"
    }
    
    st.caption(f"Currently chatting with: {model_display_name.get(st.session_state.selected_model, st.session_state.selected_model)}")
    
    # Sidebar
    with st.sidebar:
        st.title("🛠️ Chat Controls")
        
        # Support section in sidebar
        st.markdown("""
        <div style='background-color: #000; padding: 1.5em; border-radius: 10px; margin-bottom: 2em;'>
            <h3>❤️ Support the Project</h3>
            <p>Help keep MiNi-GPT free and accessible! Your support enables:</p>
            <ul>
                <li>Regular updates and improvements</li>
                <li>New features and capabilities</li>
                <li>Faster response times</li>
                <li>Better AI models integration</li>
            </ul>
            <a href='https://buymeacoffee.com/koushiknavuluri' target='_blank' class='support-button'>
                ☕ Buy me a coffee
            </a>
        </div>
        """, unsafe_allow_html=True)
        
        # Add export options
        st.markdown("### 📤 Export Chat")
        if st.session_state.messages:
            download_chat_history()
        else:
            st.info("Start chatting to enable export options!")
        
        # Reset button
        st.markdown("### ⟳ Reset Chat:")
        if st.button("Reset Chat"):
            reset_chat()
            st.rerun()
    
    
    st.markdown("---")

    # Initialize generated_images in session state if not exists
    if 'generated_images' not in st.session_state:
        st.session_state.generated_images = {}

    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            render_message_with_images(message["content"])

    # User input
    if prompt := st.chat_input("What would you like to ask?"):
        # Always add to display messages
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""
            for response in send_message(prompt, st.session_state.conversation_history, st.session_state.selected_model):
                full_response += response
                message_placeholder.markdown(full_response + "▌")
            message_placeholder.markdown(full_response)
        
        # Always add to display messages
        st.session_state.messages.append({"role": "assistant", "content": full_response})
  

if __name__ == "__main__":
    main()
