#!/bin/bash

echo "ProMoAgentAI Setup"
echo "=================="
echo ""

# Check for conda
if command -v conda &> /dev/null; then
    echo "Conda found. Setting up conda environment..."
    conda env create -f environment.yml
    if [ $? -eq 0 ]; then
        echo "Conda environment created successfully."
    else
        echo "Failed to create conda environment."
        exit 1
    fi
    echo ""
    echo "Activate with: conda activate promoagentai"
else
    echo "Conda not found. Using pip..."

    # Check if python3 is available
    if ! command -v python3 &> /dev/null; then
        echo "Python 3 is required but not installed."
        exit 1
    fi

    # Check if pip is available
    if ! command -v pip3 &> /dev/null; then
        echo "pip3 is required but not installed."
        exit 1
    fi

    echo "Python 3 and pip3 found."

    # Install requirements
    echo "Installing Python dependencies..."
    pip3 install -r requirements.txt

    if [ $? -eq 0 ]; then
        echo "Dependencies installed successfully."
    else
        echo "Failed to install dependencies."
        exit 1
    fi
fi

# Copy .env.example to .env if not exists
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "Created .env file from template."
    else
        echo "Warning: .env.example not found."
    fi
else
    echo ".env file already exists."
fi

echo ""
echo "Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Add at least one API key to .env:"
echo "     - ANTHROPIC_API_KEY (for Claude)"
echo "     - OPENAI_API_KEY (for GPT)"
echo "     - GOOGLE_API_KEY (for Gemini)"
echo "  2. Start Camunda (optional):"
echo "     docker run -d --name camunda -p 8080:8080 camunda/camunda-bpm-platform:latest"
echo "  3. Run the app:"
echo "     streamlit run app.py"
