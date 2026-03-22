# -*- coding: utf-8 -*-
import os
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VECTOR_DB_DIR = os.path.join(BASE_DIR, "data", "vector_db")

def get_all_chapters(subject, grade):
    """Extract all chapters from indexed books"""
    try:
        if not os.path.exists(VECTOR_DB_DIR):
            print(f"Vector DB not found at: {VECTOR_DB_DIR}")
            return []
        
        embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        vector_db = Chroma(persist_directory=VECTOR_DB_DIR, embedding_function=embeddings)
        
        # Search for chapter listings
        queries = [
            f"{grade}th class {subject} chapters",
            f"{subject} {grade} syllabus",
            f"{subject} table of contents",
            "chapter list"
        ]
        
        all_docs = []
        for query in queries:
            docs = vector_db.similarity_search(query, k=10)
            all_docs.extend(docs)
        
        # Extract unique chapters
        chapters = set()
        for doc in all_docs:
            content = doc.page_content
            # Look for chapter patterns
            lines = content.split('\n')
            for line in lines:
                line = line.strip()
                if 'chapter' in line.lower() or 'unit' in line.lower():
                    chapters.add(line)
        
        return list(chapters)[:15]  # Return max 15 chapters
        
    except Exception as e:
        print(f"Error extracting chapters: {e}")
        return []

if __name__ == "__main__":
    # Test
    chapters = get_all_chapters("Physics", "11")
    print(f"\nFound {len(chapters)} chapters:")
    for i, ch in enumerate(chapters, 1):
        print(f"{i}. {ch}")
