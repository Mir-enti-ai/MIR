# MIR Chatbot 🤖

MIR is an innovative AI-powered WhatsApp chatbot designed to empower Egyptian women through intelligent conversation and support. By combining advanced AI technology with culturally-aware Egyptian Arabic dialect, MIR provides a safe, accessible platform for women to seek information, guidance, and support. This project leverages the power of LangChain, OpenAI, and modern web technologies to create an engaging and supportive conversational experience that understands and respects Egyptian cultural context.

## 🌟 Features

- **Natural Language Processing**: Powered by LangChain and OpenAI for intelligent conversation
- **Egyptian Arabic Support**: Specialized in understanding and responding in Egyptian dialect
- **Real-time Communication**: WebSocket-based real-time messaging
- **Modern Web Interface**: Built with React and Material-UI
- **Scalable Backend**: FastAPI-based backend for high performance
- **Web Search Integration**: Powered by Tavily for up-to-date information

## 🛠️ Tech Stack

### Backend
- Python 3.x
- FastAPI
- LangChain
- OpenAI
- WebSockets
- Tavily Search API

### Frontend
- React 
- Material-UI
- WebSocket Client
- Modern React Hooks

## 🚀 Getting Started

### Prerequisites
- Python 
- Node.js and npm
- OpenAI API key
- Tavily API key

### Backend Setup
1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create a virtual environment and activate it:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file with your API keys:
   ```
   OPENAI_API_KEY=your_openai_api_key
   TAVILY_API_KEY=your_tavily_api_key
   ```

5. Start the backend server:
   ```bash
   uvicorn app:app --reload
   ```

### Frontend Setup
1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the development server:
   ```bash
   npm start
   ```

## 📱 Usage

1. Open the web interface at `http://localhost:3000`
3. Start chatting with the bot!

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.


