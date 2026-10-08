import os
import requests
from app.models.models import MenuItem

class CafeAIAssistant:
    def __init__(self):
        self.api_key = os.environ.get('AI_API_KEY')
        # Placeholder endpoint, assuming a generic completion API like Gemini or OpenAI
        self.api_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
        
    def _get_menu_context(self):
        """Fetches current available menu items to provide context to the AI."""
        items = MenuItem.query.filter_by(is_available=True, is_active=True).all()
        menu_text = "Current Cafe Menu:\n"
        for item in items:
            menu_text += f"- {item.name} ({item.category.name if item.category else 'No Category'}): ₹{item.price}. Description: {item.description}. Type: {'Veg' if item.veg_type == 'veg' else 'Non-Veg'}\n"
        return menu_text

    def get_response(self, user_message):
        """Gets AI response using the current menu context."""
        if not self.api_key or self.api_key == 'your_ai_api_key_here':
            return "AI Assistant is currently offline. Please set the AI_API_KEY in the environment variables."
            
        context = self._get_menu_context()
        
        system_instruction = (
            "You are 'Café AI Assistant', a helpful assistant for King Cafe. "
            "Use the provided menu to answer customer questions, recommend food, and guide them. "
            "Do NOT invent items or prices that are not on the menu. Keep answers friendly, short, and concise."
        )
        
        prompt = f"{system_instruction}\n\n{context}\n\nCustomer: {user_message}\nAI:"
        
        # Example using Gemini API structure
        try:
            headers = {'Content-Type': 'application/json'}
            params = {'key': self.api_key}
            data = {
                "contents": [{"parts":[{"text": prompt}]}]
            }
            
            response = requests.post(self.api_url, headers=headers, params=params, json=data)
            
            if response.status_code == 200:
                result = response.json()
                return result['candidates'][0]['content']['parts'][0]['text']
            else:
                return "I'm having trouble connecting to my brain right now. Please try again later!"
        except Exception as e:
            return "Oops! Something went wrong on my end. How else can I help?"
