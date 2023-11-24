import json
from flask import Flask, render_template, request
import os
import time
from openai import OpenAI
from dotenv import load_dotenv
import shutil

load_dotenv()

app = Flask(__name__)

organization_folders = ["Media", "Documents", "Apps", "Miscellaneous"]

client = OpenAI(api_key=os.getenv("API_KEY"))

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/getfolder", methods=["POST"])
def get_folder():
    folder_path = request.form["folder"].strip('"')  # Remove surrounding double quotes
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
        print(prompt)

        role = """You are a file organizer. I will give you the name of some folders that will be used to organize files into them. And them you will organize ALL OF THEM (dont forget any) in the best way possible and them return me ONLY A VALID LIST JSON in this manner: 
                {'files': [ {'file_name': '', 'output_folder': ''},...]}"""

        response = client.chat.completions.create(
            model="gpt-4-1106-preview",
            messages= [
                {
                "role": "system",
                "content": role,
                },
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},            temperature=1,
            max_tokens=2000,

        )
        
        message = response.choices[0].message.content
        print(message)

        data = json.loads(message)["files"]

        for item in data:
            file_name = item["file_name"]
            output_folder = item["output_folder"]

            # Construct the current path of the file
            current_path = os.path.join(folder_path, file_name)

            # Construct the new path of the file
            new_path = os.path.join(folder_path, output_folder, file_name)

            # Move the file to the new path
            shutil.move(current_path, new_path)
        
        return data

    except OSError as e:
        return f"Error: {e}"


if __name__ == "__main__":
    app.run(debug=True)
