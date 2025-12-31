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
        game_data = json.loads(post_data)

        # 3. Setup the Gemini Request
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
        
        prompt_text = (
            "You are a Grandmaster chess coach. Analyze this game JSON. "
            "Identify major blunders where the 'cp' score drops significantly "
            "from the 'pcp'. Explain the tactical mistake simply. "
            f"Data: {json.dumps(game_data)}"
        )
        
        payload = {"contents": [{"parts": [{"text": prompt_text}]}]}

        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            
            # 4. Send the answer back with CORS headers
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', 'https://chamster24.github.io') # Allows GitHub Pages to see the result
            self.end_headers()
            self.wfile.write(response.text.encode('utf-8'))
        except Exception as e:
            self.send_response(500)
            self.send_header('Access-Control-Allow-Origin', 'https://chamster24.github.io')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
