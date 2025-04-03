# Project Setup

## Backend Setup

1. Navigate to the `backend` folder:
   ```sh
   cd backend
   ```

2. Create and activate a virtual environment:
   ```sh
   python -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   ```

3. Install required Python dependencies:
   ```sh
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the `backend` folder and add the Gemini API key:
   ```sh
   echo "GEMINI_API_KEY=your_api_key_here" > .env
   ```

## Frontend Setup (Next.js)

1. Navigate to the frontend folder:
   ```sh
   cd frontend
   ```

2. Install dependencies:
   ```sh
   npm install
   ```

3. Start the Next.js development server:
   ```sh
   npm run dev
   ```

Your backend and frontend should now be set up and ready to run! 🎉

