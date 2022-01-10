link: install
	jprq http 8000 -s=vyapari

run:
	source venv/bin/activate
	uvicorn app:app

install: requirements.txt
	test -d venv || virtualenv venv
	. venv/bin/activate; pip install -Ur requirements.txt
	touch venv/touchfile

clean:
	find . -type d -name __pycache__ -exec rm -r {} \+
