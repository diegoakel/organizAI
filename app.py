import json
from flask import Flask, render_template, request, jsonify
import os
import time
from openai import OpenAI
from dotenv import load_dotenv
import shutil

load_dotenv()

app = Flask(__name__)

organization_folders = ["Media", "Documents", "Apps", "Miscellaneous"]




def call_model(model, prompt, role):

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

if __name__ == "__main__":
    app.run(debug=True)
