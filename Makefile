release-%:
	hatch version $*
	git add src/pdfpress/__init__.py
	git commit -m "chore: release $$(hatch version)"
	git push
