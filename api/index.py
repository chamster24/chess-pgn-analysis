from http.server import BaseHTTPRequestHandler
import json
import os
import requests

class handler(BaseHTTPRequestHandler):
	def safe_send(self, status_code, data_dict, api_key):
		# Scrubs the API key from the response body before sending.
		self.send_response(status_code)
		self.send_header('Content-type', 'application/json')
		self.send_header('Access-Control-Allow-Origin', 'https://chamster24.github.io')
		self.end_headers()
		# Convert to string and replace any occurrence of the key
		if isinstance(data_dict, (dict, list)):
			output_str = json.dumps(data_dict)
		else:
			output_str = str(data_dict)
		# Scrubbing the contents
		if api_key:
			output_str = output_str.replace(api_key, "[REDACTED]")
			
		self.wfile.write(output_str.encode('utf-8'))
		
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
		url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key={api_key}"
		
		prompt_text = (f"""
			You are a Grandmaster chess coach. The user is playing {user_color}.
			Return a JSON array of objects, no conversational filler or markdown formatting. Each object must contain:
			- "m": The move ID (e.g., "1w") provided in the input.
			- "aic": Your technical coaching insight.
			- "air": (Optional - DO NOT INCLUDE IF YOU ARE NOT OVERRIDING MOVE RATING) An integer 1-7 to override the move rating. 
			
			Rating Scale: 1:Brilliant, 2:Best, 3:Excellent, 4:Good, 5:Inaccuracy, 6:Mistake, 7:Blunder. (Use only the digit)
			
			Guidelines:
			- Focus on the "Why": If a move is bad, explain the tactical or strategic reason.
			- If the move matches 'b' (best move) and involves a sacrifice, rate it 1 (Brilliant).
			- Provide a game summary in the object where "m" is the first index.
			- ANALYZE EVERY MOVE: Do not skip index 0 or any white/black moves. Use index 0 (if in that index no-one makes a move), if there is a turn before EITHER PLAYER makes a move, to describe a overall summary
			(e.g. 'A brutal domination by black turns into a win for you due to a blunder by black.')
			- SUBJECTIVITY: If the move color matches 'playerColor', use "You/Your". If it's the opponent, use "White/Black" or "The Opponent".
			- OUTPUT: Return a new JSON with the fields m, aic, and air (optional).
	
			The 'b' field is for the best recommended move by stockfish for that side. If the user's move 
			was significantly worse than the best move ('b'), explain WHY 'b' was better, and why the user's move was bad. 

			RATING CALCULATION LOGIC:
			Calculate CP loss based on whose turn it is:
			- If White moved: Loss = p - c
			- If Black moved: Loss = c - p
			(A positive 'Loss' value means the move weakened that player's position). 
			Use this 'Loss' value to apply the 1-7 Rating Criteria.

			To understand the JSON, use this guide:
			- m: move# and side
			- s: san
			- u: uci
			- c: current centipawn
			- p: pre centipawn
			- t: timestamp (if available)
			- b: best move (recommended by engine)
			- f: fen (for every 10 moves as white)
			- cm: any prior comments
			
			Data: {json.dumps(game_data)}
		""")
		
		payload = {
			"contents": [{"parts": [{"text": prompt_text}]}],
			"generationConfig": {
				"response_mime_type": "application/json"
			}
		}

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
			# 4. Send the answer back with CORS headers and scrubbing
			self.safe_send(200, ai_text.strip(), api_key)
		except Exception as e:
			# Use safe_send to ensure any key in the error string is redacted
			error_message = {"error": str(e), "details": "Check if GEMINI_API_KEY is set and model name is correct."}
			self.safe_send(500, error_message, api_key)
