# Real Time QR Code / Data Matrix Reader

## Description

This project uses OpenCV and the [zxing-cpp](https://github.com/zxing-cpp/zxing-cpp) library to detect QR codes and Data Matrix codes from an internal or USB camera on Linux or Windows.

When a compatible code is detected, the application draws a bounding box on the video frame and writes the decoded text into a CSV file.

## Prerequisites

- Python 3.11
- `uv` command available (e.g. via the [uv package](https://github.com/ForNeVeR/uv))
- A working camera device

## Setup

1. Clone the repository:

```bash
git clone https://github.com/your-repo/QRcode_DataMatrix.git
cd QRcode_DataMatrix
```

2. Initialize the project with `uv` (only once):

```bash
uv init .
```

3. Sync the dependency environment from `pyproject.toml`:

```bash
uv sync
```

> Note: `uv init .` peut créer et gérer automatiquement l’environnement virtuel, donc la création manuelle de `.venv` n’est généralement pas nécessaire.

## Run

From the project root, run the application with `uv`:

```bash
uv run Data_Matrix_Reader_2_CSV.py
```

`uv` ensures the correct Python environment is used and installs dependencies in a reproducible way.

## Output

- A live camera preview window is shown.
- Detected codes are highlighted with a bounding box.
- Decoded text is appended to a daily CSV file named `YYYY-MM-DD_Database.csv`.

## Notes

- Press `Esc` to stop the application.
- Make sure your camera is connected before running the script.
- If the camera cannot be opened, the script exits with an error message.
