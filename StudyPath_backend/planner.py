# -*- coding: utf-8 -*-
import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

class StudyPlanner:
    def __init__(self):
        # API Key secure tareeke se uthana
        api_key = os.getenv("GEMINI_KEY")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    def create_plan(self, subject, grade, group, months=1):
        """Student ke liye AI roadmap generate karna"""
        
        template = f"""
        You are Sir Ahmed, an expert Academic Planner for Pakistan Boards (BISE).
        Create a high-level study plan for a Class {grade} ({group}) student 
        who wants to finish {subject} in {months} month(s).
        
        STRUCTURE:
        - Week 1 to Week 4 breakdown.
        - Important board topics (Sindh/Punjab/FBISE) ko priority dein.
        
        TONE:
        - Mix of Simple English and Roman Urdu (Hinglish).
        - Very encouraging and friendly teacher style.
        - Use bullet points.
        """
        
        try:
            response = self.model.generate_content(template)
            return response.text
        except Exception as e:
            print(f"Planner Error: {e}")
            return "Beta, plan banane mein thori mushkil ho rahi hai. Dobara koshish karein."

# Test karne ke liye (Optional)
if __name__ == "__main__":
    planner = StudyPlanner()
    print(planner.create_plan("Physics", "11th", "Engineering", 1))