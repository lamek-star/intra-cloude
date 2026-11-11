"""
The app runner (ADR-0020): the only part of an IntraForge installation that talks to Docker. It runs as its
own service with the Docker socket mounted, accepts a fixed, token-checked set of operations from the
backend, and builds every hosted server app's container to one locked recipe (recipe.py). Standard library
only, and no Django: it never holds IntraForge's database credentials or secrets.
"""
