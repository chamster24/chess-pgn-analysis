from http.server import BaseHTTPRequestHandler
import json
import os
import requests

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        # 1. Grab the secret key
        api_key = os.environ.get("GEMINI_API_KEY")
        
        # 2. Read the chess data sent from JS
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        game_data = json.loads(post_data)

        model = "gemini-2.5-flash"
        # 3. Setup the Gemini Request
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        
        # The "System Instruction" and Prompt
        prompt_text = (
            "You are a Grandmaster chess coach. Analyze this game JSON. "
            "Identify major blunders where the 'cp' (centipawn) score drops significantly "
            "from the 'pcp' (previous score). Explain the tactical mistake simply. "
            f"Data: {json.dumps(game_data)}"
        )
        
        payload = {
            "contents": [{"parts": [{"text": prompt_text}]}]
        }

        # 4. Call Gemini and send the result back to your JS
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(response.text.encode('utf-8'))
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
