# FastAPI RAG Chatbot 2.0 🤖

An advanced Retrieval-Augmented Generation (RAG) chatbot powered by FastAPI and LangChain, featuring document processing, vector search, and intelligent conversation capabilities.

![Python Version](https://img.shields.io/badge/python-3.11-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109.2-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

## 🌟 Features

### Core Capabilities
- **Document Processing**: Support for PDF, DOCX, and HTML files
- **Vector Search**: Pinecone integration for efficient similarity search
- **Cloud Storage**: AWS S3 for document management
- **Metadata Storage**: Supabase for document metadata and chat history
- **Real-time Chat**: Interactive Streamlit interface
- **API Documentation**: Auto-generated Swagger/OpenAPI docs

### Technical Features
- Async/await pattern for high performance
- Batched document processing
- Error handling and logging
- AWS Lambda deployment ready
- CORS middleware configuration
- Secure API endpoints

## 🛠️ Architecture

```plaintext
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Streamlit  │────▶│   FastAPI   │────▶│   OpenAI    │
│  Frontend   │◀────│   Backend   │◀────│    API      │
└─────────────┘     └─────────────┘     └─────────────┘
                          │
                          ▼
        ┌─────────────────┬─────────────────┐
        ▼                 ▼                 ▼
┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│   Pinecone  │   │    AWS S3   │   │  Supabase   │
│   Vector DB │   │   Storage   │   │  Database   │
└─────────────┘   └─────────────┘   └─────────────┘
```

## 📋 Prerequisites

- Python 3.11+
- AWS Account with S3 access
- Pinecone API key
- OpenAI API key
- Supabase account


## 🚀 Quick Start

1. **Clone the Repository**
```bash
git clone https://github.com/yourusername/FastAPI-RAG-Chatbot.git
cd FastAPI-RAG-Chatbot
```

2. **Set Up Virtual Environment**
```bash
python -m venv venv
.\venv\Scripts\activate
```

3. **Install Dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure Environment Variables**
```bash
# Create .env file in /api directory
copy .env.example .env
```

Add your API keys to the `.env` file:
```plaintext
OPENAI_API_KEY=your_openai_key
PINECONE_API_KEY=your_pinecone_key
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
CUSTOM_AWS_ACCESS_KEY=your_aws_access_key
CUSTOM_AWS_SECRET_KEY=your_aws_secret_key
CUSTOM_AWS_REGION=us-east-1
AWS_BUCKET_NAME=fastapi-rag-chatbot
```

## 💻 Local Development

1. **Start Backend Server**
```bash
cd api
uvicorn main:app --reload
```

2. **Launch Streamlit Frontend**
```bash
cd streamlit_app
streamlit run app.py
```

## 🌩️ AWS Deployment

1. **Install AWS SAM CLI**
```bash
winget install Amazon.SAM-CLI
```

2. **Build and Deploy**
```bash
cd api
sam build --use-container
sam deploy --guided
```

## 📚 API Documentation

Access the Swagger UI at: `http://localhost:8000/docs`

### Key Endpoints

| Endpoint | Method | Description |
|----------|---------|-------------|
| `/upload-doc` | POST | Upload and process documents |
| `/chat` | POST | Send messages to the chatbot |
| `/list-docs` | GET | List all documents |
| `/delete-doc/{id}` | DELETE | Delete a document |

## 🔧 Configuration

### Pinecone Setup
```python
INDEX_NAME = "pinecone-index"
DIMENSION = 1536  # OpenAI embedding dimension
METRIC = "cosine"
```

### AWS S3 Configuration
```python
BUCKET_NAME = "document-bucket"
REGION = "us-east-1"
```


## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- FastAPI for the web framework
- LangChain for RAG implementation
- Pinecone for vector database
- OpenAI for language models
- Streamlit for the UI framework
- AWS for cloud infrastructure

## 📧 Contact

Your Name - [@ZeeshanML](https://github.com/ZeeshanML)

Project Link: [https://github.com/ZeeshanML/FastAPI-RAG-Chatbot](https://github.com/ZeeshanML/FastAPI-RAG-Chatbot)