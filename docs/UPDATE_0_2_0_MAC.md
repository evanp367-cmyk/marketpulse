# Applying MarketPulse 0.2.0 on macOS

This is a source update, not an installer. Keep your original folder as a backup; the archive intentionally omits `.env`, local databases, `.venv`, and `node_modules`.

1. Stop backend and frontend terminals with `Control+C`.
2. In a terminal, make a one-time backup (choose a different suffix if it already exists):

   ```bash
   cp -R ~/Downloads/marketpulse ~/Downloads/marketpulse-v1-backup-20261011
   ```

3. Download `marketpulse-v0.2.0.zip` to `~/Downloads` and overlay the source files:

   ```bash
   unzip -o ~/Downloads/marketpulse-v0.2.0.zip -d ~/Downloads/marketpulse
   ```

4. Backend terminal:

   ```bash
   cd ~/Downloads/marketpulse
   source .venv/bin/activate
   python -m pip install -r requirements.txt
   python -m pytest -q
   python -m uvicorn backend.app.main:app --reload
   ```

5. Frontend terminal:

   ```bash
   cd ~/Downloads/marketpulse/frontend
   npm install
   npm run build
   npm run dev
   ```

6. Open `http://localhost:5173`, choose **Валюты**, and switch between **Мировые курсы** and **Курс ЦБ РФ**.

If `npm run build` fails, do not publish. Copy the complete error output for diagnosis. The backend tests can run without either upstream rate provider being reachable, but live provider access must be tested on the Mac. Neither provider supplies real-time executable Forex quotes; review commercial terms before public redistribution.
