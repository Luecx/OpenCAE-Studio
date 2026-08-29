# OpenCAE Studio 0.15.2

OpenCAE Studio is a Qt/PyVista-based CAE pre- and post-processing application.
This is a project which relies heavily on the usage of LLMs.

## Installation

```bash
python -m pip install --upgrade pip
python -m pip install -e .
```

## Run

```bash
python main.py
```

## Tests

```bash
python -m pytest -q
```

Native Qt/PyVista interaction requires the packages in `requirements.txt` and a
graphical environment.
