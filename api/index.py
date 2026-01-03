from http.server import BaseHTTPRequestHandler
import json
import os
import requests

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        # Allow Github thing
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', 'https://chamster24.github.io')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        # 1. Grab your secret key from Vercel's environment
        api_key = os.environ.get("GEMINI_API_KEY")
		
        # 2. Read the chess data sent from your JS
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        raw_data = json.loads(post_data)
        game_data = raw_data.get("gameData",[])

        user_color_raw = raw_data.get("playerColor", "unknown")

        if user_color_raw == "w":
            user_color = "white"
        elif user_color_raw == "b":
            user_color = "black"
        else:
            user_color = "an unknown side (analyze both)"
        
        # 3. Setup the Gemini Request
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
        
        prompt_text = (f"""
            You are a Grandmaster chess coach. The user is playing {user_color}.
            Return the EXACT SAME JSON array I send you. Do not include any conversational filler.
            Update the 'c' object for all moves. You may NOT use markdown formatting. 
            Structure for 'c' must be: 
            {{ 'AIRATE': [Number 1-7], 'AICOMM': 'Technical explanation of the move', 'COMM': 'Leave existing text including blanks - this field is for previous move comments by other people or programs' }}. 
            AIRATE: 1 (Brilliant), 2 (Best), 3 (Good), 4 (OK), 5 (Inaccuracy), 6 (Mistake), 7 (Blunder). 
            Use only the digit, no quotes. 
            In 'AICOMM', occasionally refer to the user as 'you', and occasionally 
            refer to them as '{user_color}' to keep the analysis feeling professional yet personal. 
            Do NOT explicitly state 'This is a mistake' or 'This is a blunder' at the end of your text, as the user will see the color-coded icon. Instead, focus on the 'Why'.
            The BM field is for the best recommended move by stockfish for that side. If the user's move 
            was significantly worse than the best move ('bm'), explain WHY 'bm' was better, and why the user's move was bad. 

            STRICT RATING CRITERIA (you are permitted to deviate from this criteria when necessary):
            1. BRILLIANT (1): ONLY if move == 'bm' AND the move involves a piece sacrifice OR a difficult tactical find that improves the evaluation significantly. 
            2. BEST (2): ONLY if move == 'bm'. Do not call a move brilliant if it is just a simple recapture or obvious development.
            3. EXCELLENT (3): If move != 'bm' but the CP loss (pcp - cp) is less than 20.
            4. GOOD (4): If move != 'bm' but CP loss is 20-50.
            5. INACCURACY (5): CP loss is 50-100.
            6. MISTAKE (6): CP loss is 100-300. (e.g., missing a fork).
            7. BLUNDER (7): CP loss is > 300. (e.g., hanging a piece).
            
            TONE AND RULES:
            - ANALYZE EVERY MOVE: Do not skip index 0 or any white/black moves. Use index 0 (if in that index no-one makes a move), if there is a turn before EITHER PLAYER makes a move, to describe a overall summary
            (e.g. 'A brutal domination by black turns into a win for you due to a blunder by black.')
            - SUBJECTIVITY: If the move color matches 'playerColor', use "You/Your". If it's the opponent, use "White/Black" or "The Opponent".
            - CRITIQUE: If a player misses a tactic (like a fork), you strongly should label it a Mistake or Blunder. Do not be "friendly"; be objectively accurate.
            - OUTPUT: Return the EXACT same JSON structure, filling in 'AIRATE' (1-7) and 'AICOMM' (a short, insightful comment).

			RATING CALCULATION LOGIC:
			Calculate CP loss based on whose turn it is:
			- If White moved: Loss = pcp - cp
			- If Black moved: Loss = cp - pcp
			(A positive 'Loss' value means the move weakened that player's position). 
			Use this 'Loss' value to apply the 1-7 Rating Criteria.
			
            Data: {json.dumps(game_data)}
            """
        )
        
        payload = {"contents": [{"parts": [{"text": prompt_text}]}]}

        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()

            # Strips response to just text
			gemini_response = response.json()
            ai_text = gemini_response['candidates'][0]['content']['parts'][0]['text']
            # Strips markdown
            if "```" in ai_text:
                parts = ai_text.split("```")
                for part in parts:
                    # Look for the part that actually looks like a JSON array
                    if part.strip().startswith("[") or part.strip().startswith("json\n["):
                        ai_text = part.replace("json", "", 1).strip()
                        break
            # 4. Send the answer back with CORS headers
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', 'https://chamster24.github.io') # Allows GitHub Pages to see the result
            self.end_headers()
            self.wfile.write(ai_text.strip().encode('utf-8'))
        except Exception as e:
			self.send_response(500)
			self.send_header('Access-Control-Allow-Origin', 'https://chamster24.github.io')
			self.send_header('Content-type', 'application/json')
			self.end_headers()
			
			error_message = {"error": str(e), "details": "Check if GEMINI_API_KEY is set and model name is correct."}
			self.wfile.write(json.dumps(error_message).encode('utf-8'))
