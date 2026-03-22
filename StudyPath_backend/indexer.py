# -*- coding: utf-8 -*-
import os
import time
import shutil  # Purana kachra saaf karne ke liye
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings 
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
import pdfplumber

# Paths configuration
base_dir = os.path.dirname(os.path.abspath(__file__))
BOOKS_ROOT = os.path.join(base_dir, "data", "textbooks")
VECTOR_DB_DIR = os.path.join(base_dir, "data", "vector_db")

def smart_indexer():
    print("🚀 StudyPath AI Local Indexing shuru ho rahi hai (No API Needed)...")
    
    # --- STEP 1: Dimension Error Fix (Automatic Folder Cleanup) ---
    if os.path.exists(VECTOR_DB_DIR):
        print("🧹 Purana vector data mil gaya. Dimension mismatch se bachne ke liye ise delete kar raha hoon...")
        try:
            shutil.rmtree(VECTOR_DB_DIR)
            print("✅ Purana data saaf ho gaya.")
        except Exception as e:
            print(f"⚠️ Error cleaning folder: {e}. Agar ye file open hai toh delete nahi hogi.")

    all_chunks = []
    
    if not os.path.exists(BOOKS_ROOT):
        os.makedirs(BOOKS_ROOT, exist_ok=True)
        print(f"💡 Action: PDFs ko yahan rakhein: {BOOKS_ROOT}")
        return

    # --- STEP 2: PDF Scanning & Extraction ---
    for root, dirs, files in os.walk(BOOKS_ROOT):
        for file in files:
            if file.endswith(".pdf"):
                file_path = os.path.join(root, file)
                path_parts = os.path.normpath(root).split(os.sep)
                board = path_parts[-2] if len(path_parts) >= 2 else "Sindh Board"
                year = path_parts[-1] if len(path_parts) >= 1 else "Year"
                subject = file.replace(".pdf", "")

                print(f"📖 Loading: {subject}...")
                
                try:
                    text_content = ""
                    with pdfplumber.open(file_path) as pdf:
                        for i, page in enumerate(pdf.pages):
                            # Trace dikhane ke liye taake Physics par atak na jaye
                            if (i + 1) % 10 == 0: 
                                print(f"   📄 Processing page {i+1}...")
                                
                            extracted_text = page.extract_text()
                            if extracted_text:
                                text_content += extracted_text + "\n"

                    if text_content.strip():
                        docs = [Document(page_content=text_content, metadata={
                            "board": board, "year": year, "subject": subject, "source": file
                        })]

                        splitter = RecursiveCharacterTextSplitter(
                            chunk_size=500, # Chota size taake search behtar ho
                            chunk_overlap=50
                        )
                        chunks = splitter.split_documents(docs)
                        all_chunks.extend(chunks)
                        print(f"✅ {len(chunks)} chunks created for {subject}")

                except Exception as e:
                    print(f"❌ Error reading {file}: {str(e)}")

    if not all_chunks:
        print("❌ Error: Koi bhi text nahi mila. Folder check karein.")
        return

    # --- STEP 3: Local Embeddings (384 Dimensions) ---
    print(f"📀 Total {len(all_chunks)} chunks ko local memory mein save kar raha hoon...")
    
    try:
        # Fixed Model: Ye 384 dimensions banata hai
        embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

        vector_db = Chroma.from_documents(
            documents=all_chunks,
            embedding=embeddings,
            persist_directory=VECTOR_DB_DIR
        )
        
        print(f"🎉 MUKAMMAL! Database '{VECTOR_DB_DIR}' mein save ho gaya.")
        print("💡 Ab aap Gemini API ke baghair search kar sakte hain.")
        
    except Exception as e:
        print(f"❌ Error during Embedding: {e}")

if __name__ == "__main__":
    smart_indexer()