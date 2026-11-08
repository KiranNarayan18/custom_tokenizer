uv init
uv venv .venv
Activate with: .venv\Scripts\activate

uv add --dev ipykernel

uv run python -m ipykernel install --user --name=my-project  --display-name="Python (cTokenizer)"

uv pip install pip