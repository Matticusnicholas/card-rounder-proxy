# MTG Proxy Card Cutter

A web application for processing Magic: The Gathering proxy card sheets for cutting with a Silhouette Portrait 4.

## Features

- **Image Upload**: Drag-and-drop or click to upload card sheet images
- **Auto Card Detection**: Automatically detects card boundaries using edge detection
- **Manual Grid Mode**: Specify grid dimensions if auto-detection fails
- **Corner Rounding**: Applies MTG-standard 3mm rounded corners to each card
- **SVG Cut File Generation**: Creates cut files with Silhouette registration marks
- **Print-Ready Output**: Generates PNG images ready for printing

## MTG Card Specifications

- **Card Size**: 63mm × 88mm (2.5" × 3.5")
- **Corner Radius**: 3mm

## Project Structure

```
card-rounder-proxy/
├── backend/
│   ├── main.py              # FastAPI application
│   ├── card_processor.py    # Card detection and corner rounding
│   ├── svg_generator.py     # SVG cut file generation
│   └── requirements.txt     # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── App.tsx          # Main React component
│   │   ├── main.tsx         # React entry point
│   │   └── index.css        # Tailwind CSS styles
│   ├── package.json         # Node dependencies
│   └── vite.config.ts       # Vite configuration
└── README.md
```

## Installation

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Frontend Setup

```bash
cd frontend
npm install
```

## Running the Application

### Start Backend (Terminal 1)

```bash
cd backend
source venv/bin/activate  # On Windows: venv\Scripts\activate
python main.py
```

The API will be available at `http://localhost:8000`

### Start Frontend (Terminal 2)

```bash
cd frontend
npm run dev
```

The web app will be available at `http://localhost:5173`

## Usage

1. **Upload Image**: Drag and drop your card sheet image (e.g., 3×3 grid of proxies)
2. **Preview Detection**: Click "Preview Detection" to see detected card boundaries
3. **Adjust Settings**:
   - Toggle auto-detect on/off
   - Set grid dimensions manually if needed
   - Choose print DPI (300 recommended)
4. **Process**: Click "Process & Generate Cut File"
5. **Download**:
   - **PNG**: Print-ready image with rounded corners
   - **SVG**: Cut file for Silhouette Studio

## Silhouette Studio Workflow

1. Print the PNG image on cardstock
2. Open Silhouette Studio
3. Import the SVG cut file
4. Place the printed sheet on the cutting mat
5. Use the "Print and Cut" workflow
6. Enable registration mark detection
7. Cut!

## API Endpoints

- `GET /` - Health check
- `POST /api/process` - Process card sheet and generate outputs
- `POST /api/preview` - Preview card detection without processing

### Process Endpoint Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| file | File | required | The card sheet image |
| grid_cols | int | 3 | Number of columns |
| grid_rows | int | 3 | Number of rows |
| auto_detect | bool | true | Auto-detect card edges |
| dpi | int | 300 | Print resolution |

## Technical Details

### Card Detection

The application uses OpenCV for card detection:
1. Convert to grayscale
2. Apply Gaussian blur
3. Canny edge detection
4. Contour detection and filtering
5. Aspect ratio validation (MTG cards are ~0.72 ratio)

### Corner Rounding

Uses PIL (Pillow) to:
1. Create rounded rectangle masks
2. Apply masks to each detected card region
3. Support alpha channel for transparent corners

### SVG Generation

Generates Silhouette-compatible SVG with:
- L-shaped registration marks
- Rounded rectangle cut paths
- Proper mm units for accurate sizing

## License

MIT
