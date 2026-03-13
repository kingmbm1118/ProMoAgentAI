# ProMoAgentAI

ProMoAgentAI is a business process modeling application that transforms
natural language descriptions into BPMN 2.0 XML diagrams using a
multi-agent architecture.

⚠️ **Note:**\
This repository contains **an initial version of the codebase intended
for research and demonstration purposes**. The complete implementation
includes additional components that are part of a commercial project and
therefore cannot be fully released at this stage.

The work behind this project was conducted in collaboration with **STC
(Saudi Telecom Company)** as part of research and development efforts in
AI-driven business process modeling.

To support the research community:

-   A **sample dataset** is provided in the `dataset/` folder for
    **scientific and academic use**.
-   **Generated results and outputs** from initial experiments are
    available in the `results/` folder.
-   The **full implementation, extended experiments, and additional
    modules** may be released in a future update when permitted.

------------------------------------------------------------------------

# Features

-   Convert business process descriptions to BPMN 2.0 models
-   Multi-agent system for generation, validation, and optimization
-   Direct deployment to Camunda BPM Platform
-   Interactive diagram visualization
-   Export BPMN files for external use

------------------------------------------------------------------------

# Repository Scope

This repository currently provides:

-   Initial prototype code
-   Core architectural structure
-   Example datasets for experimentation
-   Sample generated BPMN results

The repository **does not yet include the full production system**,
extended optimization modules, or all experimental pipelines due to
intellectual property and commercial restrictions.

------------------------------------------------------------------------

# Prerequisites

-   Python 3.8+
-   OpenAI API key
-   Docker (optional for Camunda)

------------------------------------------------------------------------

# Installation

## 1. Clone the repository

``` bash
git clone https://github.com/yourusername/promoagentai.git
cd promoagentai
```

## 2. Install dependencies

``` bash
pip install -r requirements.txt
```

## 3. Configure environment

Create a `.env` file based on `.env.example`:

``` env
MODEL_NAME="sonnet-4.5"

ANTHROPIC_API_KEY="your_anthropic_api_key_here"
OPENAI_API_KEY="your_openai_api_key_here"
GOOGLE_API_KEY="your_google_api_key_here"

CAMUNDA_URL="http://localhost:8080"
CAMUNDA_USERNAME="demo"
CAMUNDA_PASSWORD="demo"
```

------------------------------------------------------------------------

# Model Selection

ProMoAgentAI supports multiple LLMs for BPMN generation.

  Model           Quality Score   Valid BPMN   Avg Iterations
  --------------- --------------- ------------ ----------------
  Gemini          0.97            100%         1.7
  Claude Sonnet   0.95            100%         1.8
  GPT             0.94            100%         1.9

To switch models, modify the `MODEL_NAME` in the `.env` file.

------------------------------------------------------------------------

# Usage

Start the application:

``` bash
streamlit run app.py
```

Steps:

1.  Enter your business process description in natural language
2.  Click **Generate BPMN Process**
3.  View the generated diagram
4.  Download the BPMN file

------------------------------------------------------------------------

# Project Structure

    promoagentai/
    ├── app.py
    ├── orchestrator.py
    ├── agents.py
    ├── session_memory.py
    ├── bpmn_viewer.py
    ├── config.py
    ├── dataset/        # Research datasets provided for academic use
    ├── results/        # Generated experiment outputs and BPMN results
    ├── requirements.txt
    └── .env

------------------------------------------------------------------------

# Example Process Description

**Customer Order Process**

"A customer places an order online. The system confirms the payment. If
the payment fails, the customer is notified and the process ends.
Otherwise, the order is sent to the warehouse. A staff member packs the
items and hands them to the courier. Once delivered, the system updates
the status and sends a confirmation email to the customer."

------------------------------------------------------------------------

# Future Work

Planned updates include:

-   Release of extended experimental pipelines
-   Additional BPMN validation agents
-   More datasets for process modeling
-   Improved evaluation benchmarks
-   Expanded documentation and tutorials

Subject to licensing and commercial constraints, parts of the **full
system and experiments will be made available in future releases.**

------------------------------------------------------------------------

# Authors

- [Mahmoud Boghdady](https://www.linkedin.com/in/mahmoud-boghdady-msc-pmp%C2%AE-6b694033/)
- [Dr. Sherif Mazen](https://www.linkedin.com/in/dr-sherif-mazen-9a349222/)
- [Iman Helal](https://www.linkedin.com/in/iman-helal-1819b813/)

------------------------------------------------------------------------

# License

MIT License

Copyright (c) 2026 ProMoAgentAI
