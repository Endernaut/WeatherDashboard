Weather Dashboard

GitHub username at initialization time: Endernaut

For next steps, please refer to the instructions provided by your course.

# Install uv
pip install uv

# Create virtual environment
uv venv

# Activate Virtual Environment (Windows)
source .venv/Scripts/activate

# Activate Virtual Environment (Mac/Linux)
source .venv/bin/activate

# Install requirments.txt
uv pip install -r requirements.txt

# Run Shiny
shiny run --reload --launch-browser app.py
