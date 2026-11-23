"""The README's evaluation numbers are reproducible from the CSV."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("uat_summary", ROOT / "scripts" / "uat_summary.py")
uat_summary = importlib.util.module_from_spec(spec)
spec.loader.exec_module(uat_summary)


def test_summary_matches_readme():
    s = uat_summary.summarise(uat_summary.load(uat_summary.CSV_PATH))
    assert s["n"] == 10
    assert {k: round(v, 2) for k, v in s["statements"].items()} == {
        "ui1": 4.9, "ui2": 4.9, "ui3": 4.9,
        "func1": 4.9, "func2": 4.8, "func3": 4.7,
        "ux1": 4.9, "ux2": 4.9, "ux3": 4.9,
    }
    assert {k: round(v, 2) for k, v in s["sections"].items()} == {
        "User interface": 4.9, "Functionality": 4.8, "User experience": 4.9,
    }
    assert round(s["overall"], 2) == 4.87


def test_every_rating_in_readme_table_appears_in_script_output(capsys):
    uat_summary.print_markdown(uat_summary.summarise(uat_summary.load(uat_summary.CSV_PATH)))
    table = capsys.readouterr().out
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for line in table.splitlines():
        if line.startswith("|"):
            assert line in readme, f"README table is out of date: {line}"
