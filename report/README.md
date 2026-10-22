# FYP-1 mid report

LaTeX source in the FAST-NUCES template (`fast-nuces-bs.cls`). Compiled by the
`Report` workflow on every change (the PDF is an artifact of the run), or
locally with any TeX Live:

```bash
cd report
pdflatex main && bibtex main && pdflatex main && pdflatex main
```

Items the team must complete from their own records are marked in red in
the PDF (`\todo{...}` in the source): roll numbers, supervisor, the
proposal-feedback register, the meeting log, and the PR run results.
