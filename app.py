import json
from flask import Flask, render_template, request, jsonify
import os
import time
from openai import OpenAI
from dotenv import load_dotenv
import shutil
import requests
from database import FileIndexer

load_dotenv()

app = Flask(__name__)

organization_folders = ["Media", "Documents", "Apps", "Miscellaneous"]

# Database configuration
db_config = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'database': os.getenv('DB_NAME', 'file_organizer'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'postgres'),
    'port': int(os.getenv('DB_PORT', 5432))
}

# Initialize file indexer (will be done lazily when needed)
file_indexer = None

def get_file_indexer():
    """Get or create file indexer instance."""
    global file_indexer
    if file_indexer is None:
        try:
            file_indexer = FileIndexer(db_config)
        except Exception as e:
            print(f"Warning: Could not initialize file indexer: {e}")
            file_indexer = None
    return file_indexer

def call_ollama_model(model_name, prompt, role):
    """Call Ollama API for local model inference."""
    try:
        ollama_url = os.getenv('OLLAMA_URL', 'http://localhost:11434')
        
        # Prepare the request payload
        payload = {
            'model': model_name,
            'messages': [
                {'role': 'system', 'content': role},
                {'role': 'user', 'content': prompt}
            ],
            'stream': False,
            'format': 'json'
        }
        
        # Make request to Ollama API
        response = requests.post(f'{ollama_url}/api/chat', json=payload, timeout=60)
        response.raise_for_status()
        
        result = response.json()
        return result['message']['content']
        
    except Exception as e:
        print(f"Error calling Ollama model: {e}")
        raise ValueError(f"Failed to call Ollama model: {e}")

def call_model(model, prompt, role):
    """Call the selected model for inference."""
    
    # Check if it's an Ollama model (starts with 'ollama:')
    if model.startswith('ollama:'):
        model_name = model.replace('ollama:', '')
        return call_ollama_model(model_name, prompt, role)
    
    # Original model handling
    if model == "llama3":   
        client = OpenAI(api_key=os.getenv("PPLX_API_KEY"), base_url="https://api.perplexity.ai")
    else:
        client = OpenAI(api_key=os.getenv("API_KEY"))

    if model == "llama3":
        messages = [
            {"role": "system", "content": role},
            {"role": "user", "content": prompt}
        ]
        response = client.chat.completions.create(
            model="llama-3-70b-instruct",
            response_format={"type": "json_object"},
            messages=messages,
            temperature=1,
            max_tokens=2000
        )
        return response.choices[0].message.content
    elif model == "gpt4":
        response = client.chat.completions.create(
            model="gpt-4-1106-preview",
            messages=[
                {"role": "system", "content": role},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=1,
            max_tokens=2000
        )
        return response.choices[0].message.content
    else:
        raise ValueError("Invalid model selected")

def apply_organization(data, folder_path):
    """Apply file organization to the specified folder."""
    for item in data:
        file_name = item["file_name"]
        output_folder = item["output_folder"]

        # Construct the current path of the file
        current_path = os.path.join(folder_path, file_name)

        # Construct the new path of the file
        new_path = os.path.join(folder_path, output_folder, file_name)

        # Move the file to the new path
        shutil.move(current_path, new_path)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/preview", methods=["POST"])
def get_folder():
    folder_path = request.form["folder"].strip('"')  # Remove surrounding double quotes
    model = request.form["model"]
    use_indexing = request.form.get("use_indexing", "false") == "true"

    try:
        files = [
            f
            for f in os.listdir(folder_path)
            if os.path.isfile(os.path.join(folder_path, f))
        ]
        file_info = []
        for file in files:
            file_path = os.path.join(folder_path, file)
            stat = os.stat(file_path)
            file_info.append(
                {
                    "name": file,
                    "size": stat.st_size,
                    "last_modified": time.ctime(stat.st_mtime),
                }
            )

        # Create organization_folders if they do not exist
        for folder in organization_folders:
            in_folder_path = os.path.join(folder_path, folder)
            if not os.path.exists(in_folder_path):
                os.makedirs(in_folder_path)

        # Enhanced prompt with indexing if enabled
        if use_indexing:
            indexer = get_file_indexer()
            if indexer:
                # Index the directory first
                print(f"Indexing directory: {folder_path}")
                index_results = indexer.index_directory(folder_path)
                print(f"Indexing completed: {index_results}")
                
                # Get enhanced file information from index
                enhanced_info = []
                for file in files:
                    file_path = os.path.join(folder_path, file)
                    similar_files = indexer.search_similar_files(file, limit=3)
                    
                    enhanced_info.append({
                        "name": file,
                        "size": stat.st_size,
                        "last_modified": time.ctime(stat.st_mtime),
                        "similar_files": [f["file_name"] for f in similar_files if f["file_name"] != file],
                        "file_type": similar_files[0]["file_type"] if similar_files else "unknown"
                    })
                
                file_info = enhanced_info

        prompt = f"""
        Folders: {organization_folders}
        The selected folder path is: {folder_path}, and the files in this folder are: {file_info}
        """

        role = """You are a file organizer. I will give you the name of some folders that will be used to organize files into them. And them you will organize ALL OF THEM (dont forget any) in the best way possible and them return me ONLY A VALID LIST JSON in this manner: 
                {'files': [ {'file_name': '', 'output_folder': ''},...]}"""

        message = call_model(model, prompt, role)

        try:
            data = json.loads(message)
        except json.JSONDecodeError:
            json_start = message.find('{')
            json_end = message.rfind('}') + 1
            if json_start != -1 and json_end != -1:
                json_str = message[json_start:json_end]
                try:
                    data = json.loads(json_str)
                except json.JSONDecodeError:
                    return "Error: Unable to extract valid JSON from the response"
            else:
                return "Error: No JSON found in the response"
        
        # Ensure the extracted data has the expected structure
        if not isinstance(data, dict) or 'files' not in data or not isinstance(data['files'], list):
            return "Error: Invalid data structure in the response"
        
        # Use the extracted data instead of parsing the message again
        data = data['files']
        
        return jsonify({"preview": data, "folder_path": folder_path})

    except OSError as e:
        return f"Error: {e}"

@app.route("/apply", methods=["POST"])
def apply_organization_route():
    data = request.json["data"]
    folder_path = request.json["folder_path"]
    apply_organization(data, folder_path)
    return jsonify({"success": True})

@app.route("/search", methods=["POST"])
def search_files():
    """Search for files using vector similarity."""
    query = request.json.get("query", "")
    limit = request.json.get("limit", 10)
    
    indexer = get_file_indexer()
    if not indexer:
        return jsonify({"error": "File indexer not available"}), 500
    
    try:
        results = indexer.search_similar_files(query, limit)
        return jsonify({"results": results})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/index", methods=["POST"])
def index_directory():
    """Index a directory for file search."""
    directory_path = request.json.get("directory_path", "")
    
    if not directory_path:
        return jsonify({"error": "Directory path is required"}), 400
    
    indexer = get_file_indexer()
    if not indexer:
        return jsonify({"error": "File indexer not available"}), 500
    
    try:
        results = indexer.index_directory(directory_path)
        return jsonify({"results": results})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/stats", methods=["GET"])
def get_file_stats():
    """Get file indexing statistics."""
    indexer = get_file_indexer()
    if not indexer:
        return jsonify({"error": "File indexer not available"}), 500
    
    try:
        stats = indexer.get_file_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/ollama/models", methods=["GET"])
def get_ollama_models():
    """Get available Ollama models."""
    try:
        ollama_url = os.getenv('OLLAMA_URL', 'http://localhost:11434')
        response = requests.get(f'{ollama_url}/api/tags', timeout=10)
        response.raise_for_status()
        
        models = response.json()
        return jsonify(models)
    except Exception as e:
        return jsonify({"error": f"Failed to get Ollama models: {e}"}), 500

if __name__ == "__main__":
    app.run(debug=True)
