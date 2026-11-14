"""Test helper: builds the website tables fresh from data/normalized into a temporary folder and packages them, so tests never depend on the
committed data/normalized/tables folder (which the publish workflow only refreshes AFTER its self-tests)."""
import os, shutil, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from ingestion import build_tables as B, package_real as PR

def fresh_tables():
    d = tempfile.mkdtemp(); B.build(outdir=d); return d

def package(out):
    """-> (version, manifest). Packages freshly built tables into `out`."""
    t = fresh_tables()
    try: return PR.main(out, tables=t)
    finally: shutil.rmtree(t, ignore_errors=True)
