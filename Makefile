run: venv
	source venv/bin/activate && uvicorn app:app --reload

venv:
	test -d venv || python3 -m venv venv
	. venv/bin/activate; pip install -Ur requirements.txt

clean:
	find . -type d -name __pycache__ -exec rm -r {} \+
