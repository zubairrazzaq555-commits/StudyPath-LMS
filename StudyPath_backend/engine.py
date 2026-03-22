# engine.py ko replace karo is code se:

# -*- coding: utf-8 -*-
import os
from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEmbeddings 
from langchain_community.vectorstores import Chroma
from groq import Groq

load_dotenv()

# Groq API Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

# Vector DB Path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VECTOR_DB_DIR = os.path.join(BASE_DIR, "data", "vector_db")

def get_context_from_db(query, subject=None, k=3):
    """Local books se context retrieve karna"""
    try:
        if not os.path.exists(VECTOR_DB_DIR):
            print("⚠️ Vector DB folder nahi mila!")
            return ""

        # Wahi model jo indexer mein hai
        embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

        # Database load karein
        vector_db = Chroma(persist_directory=VECTOR_DB_DIR, embedding_function=embeddings)

        # Filter logic
        metadata_filter = {}
        if subject: 
            metadata_filter["subject"] = subject

        docs = vector_db.similarity_search(query, k=k, filter=metadata_filter)
        
        if docs:
            print(f"✅ {len(docs)} chunks mile from books")
            return "\n\n---\n\n".join([doc.page_content for doc in docs])
        else:
            print("⚠️ Koi relevant context nahi mila")
            return ""
            
    except Exception as e:
        print(f"Retrieval Error: {e}")
        return ""

def get_ai_response(query, subject=None):
    """Groq AI + Local Context"""
    if not client:
        return "Groq API key nahi mili! .env file mein GROQ_API_KEY daalo."
    
    try:
        # Pehle local books se context lao
        context = get_context_from_db(query, subject)
        
        # Groq ko prompt bhejo
        if context:
            prompt = f"""You are Sir Ahmed, a teacher for Sindh Board students. 
Use the textbook context below to answer the student's question.

TEXTBOOK CONTEXT:
{context}

STUDENT QUESTION: {query}

INSTRUCTIONS:
1. Answer in Urdu/Roman Urdu mix (Hinglish)
2. Be friendly and encouraging
3. If answer is in context, explain from books
4. If not in context, use your knowledge but mention "Books mein nahi hai, lekin..."

ANSWER:"""
        else:
            prompt = f"""You are Sir Ahmed, a teacher for Sindh Board students.
Student question: {query}

Answer in simple Urdu/Hinglish. Be friendly and helpful."""

        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama3-8b-8192",
            temperature=0.5,
            max_tokens=1024,
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        print(f"Groq AI Error: {e}")
        return f"Sorry, error aa gaya: {str(e)}"


def generate_roadmap(topic, subject=None):
    """AI se structured roadmap generate karna"""
    if not client:
        raise Exception("Groq API not configured")
    
    try:
        context = get_context_from_db(f"syllabus and topics for {topic}", subject, k=5)
        
        prompt = f"""You are an expert curriculum designer for Sindh Board.

TOPIC: {topic}
SUBJECT: {subject or 'General'}

TEXTBOOK CONTEXT:
{context if context else 'No specific context available'}

Create a detailed learning roadmap in JSON format with this structure:
{{
  "title": "Topic name",
  "duration": "Estimated weeks",
  "modules": [
    {{
      "module_number": 1,
      "title": "Module title",
      "topics": ["Topic 1", "Topic 2"],
      "duration": "Days/Weeks",
      "difficulty": "Easy/Medium/Hard"
    }}
  ],
  "assessments": ["Quiz 1", "Assignment 1"],
  "resources": ["Book chapters", "Practice problems"]
}}

Return ONLY valid JSON, no extra text."""

        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama3-8b-8192",
            temperature=0.3,
            max_tokens=2048,
        )
        
        import json
        roadmap_text = response.choices[0].message.content
        
        # Extract JSON from response
        start = roadmap_text.find('{')
        end = roadmap_text.rfind('}') + 1
        if start != -1 and end > start:
            roadmap_json = json.loads(roadmap_text[start:end])
            return roadmap_json
        else:
            raise Exception("Invalid JSON response from AI")
            
    except Exception as e:
        print(f"Roadmap Generation Error: {e}")
        raise Exception(f"AI roadmap generation failed: {str(e)}")


def generate_quiz(topic, subject=None, num_questions=10):
    """AI se quiz questions generate karna"""
    if not client:
        return {"error": "Groq API not configured"}
    
    try:
        context = get_context_from_db(topic, subject, k=5)
        
        prompt = f"""You are a quiz creator for Sindh Board students.

TOPIC: {topic}
SUBJECT: {subject or 'General'}
NUMBER OF QUESTIONS: {num_questions}

TEXTBOOK CONTEXT:
{context if context else 'Use general knowledge'}

Create {num_questions} multiple choice questions in JSON format:
{{
  "questions": [
    {{
      "question": "Question text in Urdu/English",
      "options": ["A) Option 1", "B) Option 2", "C) Option 3", "D) Option 4"],
      "correct_answer": "A",
      "explanation": "Why this is correct (Urdu/Hinglish)"
    }}
  ]
}}

Return ONLY valid JSON."""

        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama3-8b-8192",
            temperature=0.4,
            max_tokens=2048,
        )
        
        import json
        quiz_text = response.choices[0].message.content
        
        start = quiz_text.find('{')
        end = quiz_text.rfind('}') + 1
        if start != -1 and end > start:
            quiz_json = json.loads(quiz_text[start:end])
            return quiz_json
        else:
            return {"error": "Invalid JSON response", "raw": quiz_text}
            
    except Exception as e:
        print(f"Quiz Generation Error: {e}")
        return {"error": str(e)}

# Test ke liye
if __name__ == "__main__":
    print("Testing AI Response...")
    response = get_ai_response("atoms kya hote hain?", subject="Chemistry")
    print("\n" + "="*50)
    print(response)