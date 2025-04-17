import flask
from flask import Flask, render_template, request, jsonify
from groq import Groq, GroqError # Import GroqError
# Removed: from icrawler.builtin import GoogleImageCrawler
import os
import base64
# Removed: import shutil # No longer needed for temp directories
import logging # For better error logging
import requests # Needed for fetching images from URLs
from duckduckgo_search import DDGS # Import the DDG search library
import urllib.parse # Needed for URL encoding character names
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__, template_folder="templates", static_folder="static") # Ensure static folder is configured

# --- Configuration ---
# Ensure GROQ_API_KEY is set as an environment variable
api_key = os.getenv("GROQ_API_KEY")
client = Groq(api_key=api_key)
if not client.api_key:
    logging.warning("GROQ_API_KEY environment variable not set.")
    # Optionally exit or provide a default behavior if the key is essential
    # exit("GROQ_API_KEY is required.")

# Removed: Directory to temporarily store downloaded images
# TEMP_IMAGE_DIR = "temp_images"

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Helper Functions ---

def get_character_suggestions(user_traits):
    """
    Uses Groq LLM to suggest famous characters based on user traits.
    Returns a list of character names.
    """
    if not client.api_key:
         raise ValueError("Groq API key is not configured.")

    try:
        logging.info(f"Requesting character suggestions for traits: {user_traits[:50]}...") # Log snippet
        completion = client.chat.completions.create(
            model="llama3-70b-8192", # Using a known good model, adjust if needed
            messages=[
                {
                    "role": "system",
                    "content": "You are an assistant that suggests famous fictional characters (from Anime,movies, TV shows, books, comics, games, etc.) based on personality traits. Respond ONLY with a comma-separated list of at least 4 character names. Make sure each one of them are from different category. Include the source (like 'Light Yagami (Death Note)', 'Batman (DC Comics)'). Do not add any introductory text, explanations, or numbering. Example: Naruto Uzumaki (Naruto), Batman (DC Comics), Sherlock Holmes (Books by A. Conan Doyle), Wonder Woman (DC Comics), Lara Croft (Tomb Raider Games)."
                },
                {
                    "role": "user",
                    "content": f"Suggest at least 4 famous fictional characters based on these traits: {user_traits}"
                }
            ],
            temperature=0.8, # Slightly lower temp for more focused suggestions
            max_tokens=150, # Reduced tokens as we only need names
            top_p=1,
            stream=False, # Easier to parse non-streamed response for this
            stop=None,
        )

        raw_suggestions = completion.choices[0].message.content.strip()
        logging.info(f"Raw suggestions from LLM: {raw_suggestions}")

        # Basic parsing - split by comma and clean up whitespace/empty strings
        character_list = [name.strip() for name in raw_suggestions.split(',') if name.strip()]

        if not character_list:
            logging.warning("LLM did not return valid character names.")
            return []

        logging.info(f"Parsed characters: {character_list}")
        # Limit to a reasonable number, e.g., first 5, even if LLM gives more
        return character_list[:5]

    except Exception as e:
        logging.error(f"Error fetching character suggestions from Groq: {e}")
        raise # Re-raise the exception to be caught by the route handler


def fetch_image_ddg(query):
    """
    Fetches the first usable image result from DuckDuckGo Images for the query
    and returns it as a base64 encoded string.
    """
    logging.info(f"Searching DDG Images for: {query}")
    try:
        with DDGS(timeout=10) as ddgs: # Use context manager for cleanup
            results = list(ddgs.images(
                query,
                region="wt-wt",       # Worldwide
                safesearch="moderate",  # Or "moderate", "off"
                size=None,            # Fetch any size first
                type_image="photo",   # Prioritize photos
                layout=None,
                license_image=None,
                max_results=5         # Fetch a few results to increase chances
            ))

        if not results:
            logging.warning(f"No image results found via DDG for query: {query}")
            return None

        # Try fetching the first few images until one works
        for result in results:
            image_url = result.get("image")
            if image_url:
                logging.info(f"Attempting to fetch DDG image URL: {image_url}")
                try:
                    # Use requests to get the image data from the URL
                    img_response = requests.get(
                        image_url,
                        timeout=15,       # Timeout for the image request
                        stream=True,      # Efficient for binary data
                        headers={'User-Agent': 'Mozilla/5.0'} # Some sites require a user agent
                    )
                    img_response.raise_for_status() # Check for HTTP errors (like 404, 403)

                    # Check if the content type is actually an image
                    content_type = img_response.headers.get('content-type')
                    if content_type and 'image' in content_type.lower():
                        # Read the image content
                        image_bytes = b''
                        for chunk in img_response.iter_content(chunk_size=8192):
                            image_bytes += chunk

                        # Basic check: Ensure some data was actually downloaded
                        if len(image_bytes) > 500: # Check if size seems reasonable (adjust threshold if needed)
                            logging.info(f"Successfully fetched image from: {image_url}")
                            # Encode the bytes as base64
                            return base64.b64encode(image_bytes).decode('utf-8')
                        else:
                            logging.warning(f"Downloaded data too small from {image_url} ({len(image_bytes)} bytes), likely not a valid image.")
                    else:
                        logging.warning(f"URL did not point to a valid image content type: {content_type} from {image_url}")

                except requests.exceptions.Timeout:
                    logging.warning(f"Timeout while fetching image from {image_url}")
                except requests.exceptions.RequestException as img_err:
                    # Log other request errors (connection, status code, etc.)
                    logging.warning(f"Failed to download or access image from {image_url}: {img_err}")
                except Exception as e:
                     # Catch any other unexpected errors during image processing
                     logging.error(f"Unexpected error processing image from {image_url}: {e}")
                finally:
                    # Ensure the response stream is closed if opened
                    if 'img_response' in locals() and img_response:
                        img_response.close()

            else:
                logging.warning("DDG result item missing 'image' key.")

        # If the loop finishes without returning, no image was successfully fetched
        logging.error(f"Could not fetch a valid image from DDG results for: {query}")
        return None

    except Exception as e:
        # Catch errors during the DDG search itself
        logging.error(f"Error during DuckDuckGo image search for '{query}': {e}")
        return None


# --- Flask Routes ---

@app.route("/")
def index():
    # No temp directory cleanup needed anymore
    return render_template('index.html')

@app.route("/generate", methods=['POST'])
def generate():
    data = request.get_json()
    user_traits = data.get('prompt')

    if not user_traits:
        return jsonify({'error': 'Please describe your character traits.'}), 400

    if not client.api_key:
         # Log this server-side for debugging
         logging.error("Groq API key is missing during request processing.")
         return jsonify({'error': 'Server configuration error. Please contact the administrator.'}), 500

    try:
        # 1. Get character suggestions from LLM
        character_names = get_character_suggestions(user_traits)

        if not character_names:
            # Let user know the LLM failed or returned nothing useful
            return jsonify({'error': 'Could not generate character suggestions based on your input. Try different traits.'}), 500

        # 2. Fetch image for each character using DuckDuckGo
        results = []
        for name in character_names:
            logging.info(f"Processing character: {name}")
            # *** Use the new function here ***
            image_data = fetch_image_ddg(name)
            if image_data: # Only add if image was successfully fetched and encoded
                # URL-encode the name for safe use in paths
                character_name_url = urllib.parse.quote_plus(name)
                results.append({
                    'name': name,
                    'image_data': image_data,
                    'url_name': character_name_url # Add URL-safe name
                })
            else:
                # Optional: Add a placeholder or just skip if image fails
                logging.warning(f"Skipping character '{name}' due to missing/failed image fetch.")
                # Could add a placeholder record if desired:
                # results.append({'name': name, 'image_data': None, 'url_name': urllib.parse.quote_plus(name)})
        if not results:
             # This happens if LLM gave names, but *no* images could be found for any of them
             return jsonify({'error': 'Found character suggestions, but could not fetch images for them.'}), 500

        # 3. Return the list of characters with their images
        return jsonify({'characters': results})

    except ValueError as ve: # Specific error for API key missing (from get_character_suggestions)
        logging.error(f"Configuration error: {ve}")
        return jsonify({'error': f'Server configuration error: {str(ve)}'}), 500
    except Exception as e:
        logging.exception("An unexpected error occurred during generation.") # Log full traceback
        # Provide a generic error to the user
        return jsonify({'error': 'An unexpected error occurred on the server. Please try again later.'}), 500


@app.route("/chat/<character_name_url>")
def chat_page(character_name_url):
    """Renders the dedicated chat page for a character."""
    # Decode the character name from the URL
    character_name = urllib.parse.unquote_plus(character_name_url)
    # Pass the decoded name to the template
    return render_template('chat.html', character_name=character_name)


@app.route("/api/chat", methods=['POST'])
def api_chat():
    """Handles chat API requests, interacts with Groq."""
    # Check if Groq client is available (initialized at the top)
    # Use the 'client' variable defined in the global scope
    if not client or not client.api_key:
        logging.error("Chat API request received but Groq client is not initialized (API key missing or invalid).")
        return jsonify({'error': 'Server configuration error: Groq API key not available.'}), 500

    # Get data from request body
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid JSON request body.'}), 400

    user_message = data.get('user_message')
    character_name = data.get('character_name') # e.g., "Batman (DC Comics)"
    chat_history = data.get('chat_history', []) # Default to empty list

    # Validate required fields
    if not user_message:
        return jsonify({'error': 'Missing required field: user_message.'}), 400
    if not character_name:
        return jsonify({'error': 'Missing required field: character_name.'}), 400

    # Validate chat_history format (basic check)
    if not isinstance(chat_history, list):
         return jsonify({'error': 'Invalid format for chat_history: must be a list.'}), 400
    for item in chat_history:
        if not isinstance(item, dict) or 'role' not in item or 'content' not in item:
            return jsonify({'error': 'Invalid item format in chat_history. Each item must be a dict with "role" and "content".'}), 400

    logging.info(f"API chat request for {character_name} with message: '{user_message[:50]}...'")

    try:
        # Construct the persona prompt for the LLM
        persona_prompt = f"""You are embodying the character '{character_name}'. Respond to the user's message below in the first person, staying true to the character's known personality, voice, mannerisms, and knowledge based on their source material. Keep your response concise and conversational for a chat interface. Do not break character. Do not mention that you are an AI."""

        # Construct messages for Groq API
        messages = [
            {
                "role": "system",
                "content": persona_prompt
            }
        ]
        # Append history if provided
        messages.extend(chat_history)
        # Append the latest user message
        messages.append(
            {
                "role": "user",
                "content": user_message
            }
        )

        # Make the API call using the global 'client'
        logging.info(f"Sending {len(messages)} messages to Groq API for {character_name}...")
        completion = client.chat.completions.create(
            model="llama3-8b-8192", # Using a smaller, faster model suitable for chat
            messages=messages,
            temperature=0.8, # Slightly higher temp for more character
            max_tokens=200, # Limit response length for chat
            top_p=1,
            stream=False,
            stop=None,
        )

        assistant_response = completion.choices[0].message.content.strip()
        logging.info(f"Groq response received for {character_name}: '{assistant_response[:50]}...'")

        # Return the successful response
        return jsonify({'assistant_response': assistant_response})

    except GroqError as ge: # Make sure GroqError is imported if needed, or use generic Exception
        logging.error(f"Groq API error for {character_name}: {ge}")
        error_message = f"Groq API error: {str(ge)}"
        status_code = getattr(ge, 'status_code', 500)
        return jsonify({'error': error_message}), status_code if status_code else 500
    except Exception as e:
        logging.exception(f"An unexpected error occurred during chat API processing for {character_name}.")
        return jsonify({'error': 'An unexpected server error occurred.'}), 500

if __name__ == "__main__":
   # No need to create TEMP_IMAGE_DIR anymore
   # Run the Flask app
   # Set debug=False for production deployment
   app.run(host="0.0.0.0", port=5000, debug=True)