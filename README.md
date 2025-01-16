# Flash Reader

A modern web-based speed reading application with phrase mode and customizable reading speeds.

## Features
- Single word or phrase mode speed reading
- Adjustable WPM (Words Per Minute) from 100-1000
- Progress tracking and saving
- PDF processing and text extraction
- Full text view option
- Keyboard shortcuts for easy control

## Quick Start

1. Clone the repository:
```bash
git clone https://github.com/yourusername/flash-reader.git
cd flash-reader
```

2. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the application:
```bash
python app.py
```

5. Open your browser and go to: `http://localhost:5000`

## Usage

1. Upload a PDF using the upload button
2. Once processed, click "Read Book"
3. Use the controls to:
   - Start/Stop/Pause reading
   - Adjust speed (WPM)
   - Toggle phrase mode
   - Navigate through text

## Keyboard Shortcuts
- `Space`: Play/Pause
- `←/→`: Previous/Next word
- `↑/↓`: Increase/Decrease speed
- `P`: Toggle phrase mode
- `[/]`: Adjust phrase size (in phrase mode)

## Requirements
- Python 3.8+
- Flask
- PyMuPDF
- Other dependencies in requirements.txt 