# AI File Organizer

A Flask-based web application that uses AI models to organize files in directories with smart indexing and local model support.

## Features

- **Multi-Model Support**: Choose from GPT-4 (OpenAI), Llama 3 (Perplexity), or local models via Ollama
- **Smart File Indexing**: Index files using PostgreSQL with pgvector for semantic search
- **Vector Search**: Search files by content similarity using embeddings
- **Intelligent Organization**: AI-powered file organization into predefined folders
- **Modern UI**: Clean, responsive interface with real-time statistics

## Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd organizAI
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Set Up Environment Variables

Create a `.env` file based on `.env.example`:

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```env
# OpenAI API Key (for GPT-4)
API_KEY=your_openai_api_key_here

# Perplexity API Key (for Llama 3)
PPLX_API_KEY=your_perplexity_api_key_here

# Ollama Configuration (for local models)
OLLAMA_URL=http://localhost:11434

# PostgreSQL Database Configuration (for file indexing)
DB_HOST=localhost
DB_NAME=file_organizer
DB_USER=postgres
DB_PASSWORD=postgres
DB_PORT=5432
```

### 4. Set Up PostgreSQL with pgvector

#### Option A: Using Docker (Recommended)

```bash
# Run PostgreSQL with pgvector
docker run -d \
  --name postgres-pgvector \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=file_organizer \
  -p 5432:5432 \
  pgvector/pgvector:pg16
```

#### Option B: Manual Installation

1. Install PostgreSQL and pgvector extension
2. Create a database named `file_organizer`
3. Enable the pgvector extension in your database

### 5. Initialize the Database

```bash
python setup_db.py
```

### 6. Set Up Ollama (Optional)

To use local models:

```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull a model (e.g., llama3)
ollama pull llama3

# Start Ollama server (if not already running)
ollama serve
```

### 7. Run the Application

```bash
python app.py
```

The application will be available at `http://localhost:5000`

## Usage

### File Organization

1. **Select a Model**: Choose from GPT-4, Llama 3, or local Ollama models
2. **Enter Folder Path**: Specify the directory you want to organize
3. **Enable Smart Indexing**: Toggle to use vector-based file analysis
4. **Preview Changes**: See how files will be organized
5. **Apply Changes**: Execute the organization plan

### File Search

1. **Index Files**: Use the "Index Management" section to index directories
2. **Search**: Enter search terms to find files by content similarity
3. **View Results**: Browse matched files with similarity scores

### Statistics

- View total indexed files
- See file type distribution
- Monitor indexing activity
- Track database usage

## API Endpoints

### File Organization
- `POST /preview` - Preview file organization
- `POST /apply` - Apply file organization

### File Indexing
- `POST /index` - Index a directory
- `POST /search` - Search indexed files
- `GET /stats` - Get indexing statistics

### Model Management
- `GET /ollama/models` - List available Ollama models

## Supported File Types

The application categorizes files into:

- **Documents**: PDF, DOC, DOCX, TXT, MD, RTF
- **Images**: JPG, PNG, GIF, BMP, SVG, WEBP
- **Audio**: MP3, WAV, FLAC, AAC, OGG, M4A
- **Video**: MP4, AVI, MKV, MOV, WMV, FLV, WEBM
- **Code**: PY, JS, HTML, CSS, CPP, C, JAVA, PHP
- **Archives**: ZIP, RAR, 7Z, TAR, GZ, BZ2
- **Other**: All other file types

## Architecture

### Components

1. **Flask Backend** (`app.py`): Main application server
2. **Database Layer** (`database.py`): PostgreSQL with pgvector integration
3. **AI Models**: Support for OpenAI, Perplexity, and Ollama APIs
4. **Frontend**: Modern HTML/CSS/JavaScript interface

### File Indexing Process

1. **File Scanning**: Traverse directory structure
2. **Content Analysis**: Extract text content and metadata
3. **Embedding Generation**: Create vector representations using sentence-transformers
4. **Database Storage**: Store embeddings in PostgreSQL with pgvector
5. **Search**: Use cosine similarity for file matching

## Development

### Adding New Models

To add support for additional AI models:

1. Extend the `call_model()` function in `app.py`
2. Add model options to the frontend select dropdown
3. Update the model selection logic

### Database Schema

The `file_index` table stores:
- File metadata (path, name, size, hash)
- Content preview and file type
- Vector embeddings (384-dimensional)
- Indexing timestamps and metadata

### Customization

- **Organization Folders**: Modify `organization_folders` in `app.py`
- **File Types**: Update type mapping in `database.py`
- **UI Styling**: Customize Tailwind CSS classes in `templates/index.html`

## Troubleshooting

### Common Issues

1. **Database Connection**: Ensure PostgreSQL is running and credentials are correct
2. **pgvector Extension**: Make sure pgvector is installed and enabled
3. **Ollama Models**: Verify Ollama is running and models are downloaded
4. **API Keys**: Check that API keys are valid and have sufficient credits

### Performance Tips

- Index files in smaller batches for large directories
- Use local models for faster inference
- Monitor database size and performance
- Consider using GPU acceleration for embeddings

## License

This project is licensed under the MIT License.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Support

For issues and questions, please create an issue in the GitHub repository.
