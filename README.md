Folder Organizer

This project is a Flask-based web application that uses OpenAI's GPT-4 model to organize files in a directory into predefined folders. The application takes a directory path as input and organizes the files in the directory into folders such as "Media", "Documents", "Apps", and "Miscellaneous".
Setup

Clone the repository to your local machine.

Install the required Python packages. You can do this by running the following command in your terminal:

```
pip install -r requirements.txt
```

You need to set up your OpenAI API key. This project uses the dotenv package to manage environment variables. Create a .env file in the root directory of the project and add your OpenAI API key like so:

```
API_KEY=your_openai_api_key
```

Run the application. You can do this by running the following command in your terminal:

```
python app.py
```

The application will start running on your local machine, and you can access it by navigating to http://localhost:5000 in your web browser.
Usage

Navigate to the home page of the application.

Enter the path of the folder you want to organize in the input field.

Click the "Submit" button. The application will organize the files in the specified folder and return a JSON response with the details of the file organization.

Please note that the application currently only supports organizing files into the predefined folders ("Media", "Documents", "Apps", and "Miscellaneous"). If you want to add more folders, you can do so by modifying the organization_folders list in app.py.