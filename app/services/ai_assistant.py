import os
import requests
from app.models.models import MenuItem


class CafeAIAssistant:

    def __init__(self):
        # Read the secret key from Railway environment variables
        self.api_key = os.environ.get("AI_API_KEY", "").strip()

        # Current Gemini API endpoint
        self.api_url = (
            "https://generativelanguage.googleapis.com/"
            "v1beta/models/gemini-3.8-flash:generateContent"
        )

    def _get_menu_context(self):
       

        items = MenuItem.query.filter_by(
            is_available=True,
            is_active=True
        ).all()

        menu_items = ["Current King Cafe Menu:"]

        for item in items:
            category_name = (
                item.category.name if item.category else "No Category"
            )

            food_type = (
                "Veg" if item.veg_type == "veg" else "Non-Veg"
            )

            menu_items.append(
                f"- {item.name} | Category: {category_name} | "
                f"Price: Rs. {item.price} | "
                f"Type: {food_type} | "
                f"Description: {item.description or 'Not provided'}"
            )

        return "\n".join(menu_items)

   
    def get_menu_cards(self):
        """Return real menu items for the visual menu-card UI."""

        items = MenuItem.query.filter_by(
            is_available=True,
            is_active=True
        ).all()

        menu = []

        for item in items:
            menu.append({
                "id": item.id,
                "name": item.name,
                "category": (
                    item.category.name
                    if item.category else "Other"
                ),
                "price": float(item.price),
                "description": item.description or "",
                "veg_type": item.veg_type,
                "image_path": item.image_path or ""
            })

        return menu

    def get_response(self, user_message):
        """Generate a response using the Gemini API."""

        if not self.api_key:
            return (
                "The AI Assistant is offline because its API key "
                "is missing. Please check the Railway AI_API_KEY variable."
            )

        try:
            menu_context = self._get_menu_context()

            prompt = f"""
You are the friendly AI assistant for King Cafe.

Help customers discover food, choose menu items,
understand prices, and receive recommendations.

Rules:
1. Recommend only items listed in the supplied menu.
2. Never invent food items or prices.
3. Use the actual prices given in the menu.
4. Be friendly, helpful, and concise.
5. If a requested item is unavailable, explain politely.
6. Help customers compare vegetarian and non-vegetarian options.

{menu_context}

Customer message:
{user_message}

Reply as the King Cafe AI Assistant.
"""

            response = requests.post(
                self.api_url,
                params={"key": self.api_key},
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [
                        {
                            "parts": [
                                {"text": prompt}
                            ]
                        }
                    ]
                },
                timeout=30
            )

            if response.status_code != 200:
                print(
                    "Gemini API error:",
                    response.status_code,
                    response.text[:500]
                )
                return (
                    "I'm having trouble connecting right now. "
                    "Please try again shortly."
                )

            result = response.json()

            candidates = result.get("candidates", [])

            if not candidates:
                return (
                    "I couldn't generate a response just now. "
                    "Please try asking another question."
                )

            parts = candidates[0].get(
                "content", {}
            ).get("parts", [])

            answer = " ".join(
                part["text"]
                for part in parts
                if "text" in part
            ).strip()

            return answer or (
                "I couldn't generate a response. Please try again."
            )

        except requests.Timeout:
            return (
                "The AI is taking too long to respond. "
                "Please try again."
            )

        except requests.RequestException as error:
            print("Gemini connection error:", str(error))
            return (
                "I'm unable to connect to the AI service right now. "
                "Please try again later."
            )
        except Exception as error:
            print("AI Assistant error:", str(error))
            return (
                "Something went wrong. Please try again later."
            )
