import os
import psycopg2
from psycopg2.extras import RealDictCursor
try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None
import numpy as np
from datetime import datetime
import json
import hashlib
from typing import List, Dict, Optional, Tuple

class FileIndexer:
    def __init__(self, db_config: Dict[str, str]):
        """
        Initialize the FileIndexer with database configuration.
        
        Args:
            db_config: Dictionary containing database connection parameters
        """
        self.db_config = db_config
        
        # Initialize the sentence transformer model
        if SentenceTransformer is None:
            raise ImportError("sentence-transformers is required. Install with: pip install sentence-transformers")
        
        self.model = SentenceTransformer('all-MiniLM-L6-v2')  # Lightweight model for embeddings
        self.embedding_dim = 384  # Dimension for all-MiniLM-L6-v2
        self.connection = self._create_connection()
        self._setup_database()
    
    def _create_connection(self):
        """Create database connection."""
        try:
            return psycopg2.connect(**self.db_config)
        except Exception as e:
            print(f"Error connecting to database: {e}")
            raise
    
    def _ensure_connection(self):
        """Ensure database connection is active."""
        if self.connection is None or self.connection.closed:
            self.connection = self._create_connection()
    
    def _setup_database(self):
        """Setup database tables and pgvector extension."""
        try:
            with self.connection.cursor() as cursor:
                # Enable pgvector extension
                cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                
                # Create files table with vector column
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS file_index (
                        id SERIAL PRIMARY KEY,
                        file_path TEXT UNIQUE NOT NULL,
                        file_name TEXT NOT NULL,
                        file_size BIGINT NOT NULL,
                        file_hash TEXT NOT NULL,
                        last_modified TIMESTAMP NOT NULL,
                        content_preview TEXT,
                        file_type TEXT,
                        embedding vector(384),
                        indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        metadata JSONB
                    );
                """)
                
                # Create index on embedding column for fast similarity search
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS file_index_embedding_idx 
                    ON file_index USING ivfflat (embedding vector_cosine_ops)
                    WITH (lists = 100);
                """)
                
                # Create index on file_path for fast lookups
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS file_index_path_idx 
                    ON file_index (file_path);
                """)
                
                self.connection.commit()
                print("Database setup completed successfully")
        except Exception as e:
            print(f"Error setting up database: {e}")
            self.connection.rollback()
    
    def _get_file_hash(self, file_path: str) -> str:
        """Generate SHA-256 hash of file content."""
        hash_sha256 = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
        except Exception as e:
            print(f"Error hashing file {file_path}: {e}")
            return ""
        return hash_sha256.hexdigest()
    
    def _get_file_preview(self, file_path: str, max_chars: int = 1000) -> str:
        """Get preview of file content if it's a text file."""
        try:
            # Check if it's a text file
            text_extensions = {'.txt', '.md', '.py', '.js', '.html', '.css', '.json', '.xml', '.csv'}
            file_ext = os.path.splitext(file_path)[1].lower()
            
            if file_ext in text_extensions:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read(max_chars)
                    return content
            else:
                return f"Binary file: {file_ext}"
        except Exception as e:
            return f"Error reading file: {str(e)}"
    
    def _get_file_type(self, file_path: str) -> str:
        """Determine file type based on extension."""
        file_ext = os.path.splitext(file_path)[1].lower()
        
        type_mapping = {
            # Documents
            '.pdf': 'document', '.doc': 'document', '.docx': 'document', 
            '.txt': 'document', '.md': 'document', '.rtf': 'document',
            
            # Images
            '.jpg': 'image', '.jpeg': 'image', '.png': 'image', '.gif': 'image',
            '.bmp': 'image', '.svg': 'image', '.webp': 'image',
            
            # Audio
            '.mp3': 'audio', '.wav': 'audio', '.flac': 'audio', '.aac': 'audio',
            '.ogg': 'audio', '.m4a': 'audio',
            
            # Video
            '.mp4': 'video', '.avi': 'video', '.mkv': 'video', '.mov': 'video',
            '.wmv': 'video', '.flv': 'video', '.webm': 'video',
            
            # Code
            '.py': 'code', '.js': 'code', '.html': 'code', '.css': 'code',
            '.cpp': 'code', '.c': 'code', '.java': 'code', '.php': 'code',
            
            # Archive
            '.zip': 'archive', '.rar': 'archive', '.7z': 'archive', '.tar': 'archive',
            '.gz': 'archive', '.bz2': 'archive'
        }
        
        return type_mapping.get(file_ext, 'other')
    
    def index_file(self, file_path: str) -> bool:
        """Index a single file."""
        try:
            if not os.path.exists(file_path):
                print(f"File not found: {file_path}")
                return False
            
            # Get file metadata
            stat = os.stat(file_path)
            file_name = os.path.basename(file_path)
            file_size = stat.st_size
            last_modified = datetime.fromtimestamp(stat.st_mtime)
            file_hash = self._get_file_hash(file_path)
            content_preview = self._get_file_preview(file_path)
            file_type = self._get_file_type(file_path)
            
            # Check if file already exists and hasn't changed
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT file_hash, last_modified 
                    FROM file_index 
                    WHERE file_path = %s
                """, (file_path,))
                
                existing = cursor.fetchone()
                if existing and existing['file_hash'] == file_hash:
                    print(f"File {file_name} already indexed and unchanged")
                    return True
            
            # Create embedding from file name and content preview
            text_to_embed = f"{file_name} {content_preview}"
            embedding = self.model.encode(text_to_embed)
            
            # Insert or update file in database
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO file_index 
                    (file_path, file_name, file_size, file_hash, last_modified, 
                     content_preview, file_type, embedding, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (file_path) 
                    DO UPDATE SET
                        file_name = EXCLUDED.file_name,
                        file_size = EXCLUDED.file_size,
                        file_hash = EXCLUDED.file_hash,
                        last_modified = EXCLUDED.last_modified,
                        content_preview = EXCLUDED.content_preview,
                        file_type = EXCLUDED.file_type,
                        embedding = EXCLUDED.embedding,
                        metadata = EXCLUDED.metadata,
                        indexed_at = CURRENT_TIMESTAMP
                """, (
                    file_path, file_name, file_size, file_hash, last_modified,
                    content_preview, file_type, embedding.tolist(), 
                    json.dumps({"extension": os.path.splitext(file_path)[1]})
                ))
            
            self.connection.commit()
            print(f"Successfully indexed: {file_name}")
            return True
            
        except Exception as e:
            print(f"Error indexing file {file_path}: {e}")
            self.connection.rollback()
            return False
    
    def index_directory(self, directory_path: str) -> Dict[str, int]:
        """Index all files in a directory."""
        if not os.path.exists(directory_path):
            print(f"Directory not found: {directory_path}")
            return {"success": 0, "failed": 0}
        
        success_count = 0
        failed_count = 0
        
        for root, dirs, files in os.walk(directory_path):
            for file in files:
                file_path = os.path.join(root, file)
                if self.index_file(file_path):
                    success_count += 1
                else:
                    failed_count += 1
        
        return {"success": success_count, "failed": failed_count}
    
    def search_similar_files(self, query: str, limit: int = 10) -> List[Dict]:
        """Search for files similar to the query."""
        try:
            # Create embedding for the query
            query_embedding = self.model.encode(query)
            
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT file_path, file_name, file_type, content_preview,
                           file_size, last_modified, metadata,
                           (embedding <=> %s) as similarity_score
                    FROM file_index
                    ORDER BY embedding <=> %s
                    LIMIT %s
                """, (query_embedding.tolist(), query_embedding.tolist(), limit))
                
                results = cursor.fetchall()
                
                # Convert to list of dictionaries
                return [dict(row) for row in results]
                
        except Exception as e:
            print(f"Error searching files: {e}")
            return []
    
    def get_file_stats(self) -> Dict:
        """Get statistics about indexed files."""
        try:
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_files,
                        COUNT(DISTINCT file_type) as unique_types,
                        SUM(file_size) as total_size,
                        MAX(indexed_at) as last_indexed
                    FROM file_index
                """)
                
                stats = cursor.fetchone()
                
                # Get file type distribution
                cursor.execute("""
                    SELECT file_type, COUNT(*) as count
                    FROM file_index
                    GROUP BY file_type
                    ORDER BY count DESC
                """)
                
                type_distribution = cursor.fetchall()
                
                return {
                    "total_files": stats['total_files'],
                    "unique_types": stats['unique_types'],
                    "total_size": stats['total_size'],
                    "last_indexed": stats['last_indexed'],
                    "type_distribution": [dict(row) for row in type_distribution]
                }
                
        except Exception as e:
            print(f"Error getting file stats: {e}")
            return {}
    
    def close(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()
            self.connection = None