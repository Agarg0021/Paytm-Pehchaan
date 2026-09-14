# Paytm Pehchaan

Hackathon demo: give the kirana shopkeeper a memory at the payment beep.

The Soundbox still announces only the amount. The merchant-facing screen shows one cue — पहली बार, लौट आए, ख़ास ग्राहक, or रुक गए — drawn from this shop's own payment history. No name, no number, no customer app.

## Run

Python 3.12+ and Node 22+.

```powershell
# backend
cd backend
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8000

# frontend (second terminal)
cd frontend
npm install
npm run dev
```

Or from the repo root: `.\start.ps1`

Open http://localhost:5173

First backend start generates a seeded 90-day stream into DuckDB (~40s). After that, starts are instant.

## Demo keys

| Key | Action |
|---|---|
| space / click device | Next payment |
| 1 | Counter |
| 2 | Scoreboard |
| 3 | Pruning |
| 4 | Privacy (`#privacy`) |
| 5 | Close (`#close`) |
| p | Run the 3-minute pitch (Escape to stop) |
| n | Toggle presenter notes |
| a | Autoplay the 5-beat reel (backup) |
| r | Reset the live reel |

Pitch order on the counter: ordinary (no cue) → पहली बार → लौट आए → रुक गए.
