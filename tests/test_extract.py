from pathlib import Path

from screener.extract import extract_email, extract_github_usernames, extract_name, split_sections
from screener.ingest import RawResume, normalize_text


def test_github_username_from_links_and_repo_urls():
    links = ["https://github.com/octo", "https://github.com/octo/proj"]
    assert extract_github_usernames("github.com/octo", links)[0] == "octo"
    assert extract_github_usernames("see https://github.com/Pavani-A/Auto_Eval", [])[0] == "Pavani-A"
    assert extract_github_usernames("https://github.com/ and github.com/features", []) == []


def test_mailto_beats_glyph_polluted_text():
    assert extract_email("envel⌢pejainagam4@gmail.com", ["mailto:jainagam4@gmail.com"]) == "jainagam4@gmail.com"


def test_name_extraction_skips_headers_and_contact_noise():
    assert extract_name("Vaibhav WakdeEmail: v@x.com\nSkills", "v@x.com", "f.pdf") == "Vaibhav Wakde"
    assert extract_name("PROFESSIONAL SUMMARY\nAditi Kala\naditi@x.com", None, "f.pdf") == "Aditi Kala"
    assert extract_name("SHIVAM RAJ\nfoo", None, "f.pdf") == "Shivam Raj"


def test_sections_and_inline_caps_headers():
    secs = {s.name for s in split_sections("Name\nSKILLS\nPython\nPROJECTS\nA project")}
    assert {"skills", "projects"} <= secs
    flat = {s.name for s in split_sections("Kiran PROFESSIONAL SUMMARY AI engineer PROFESSIONAL EXPERIENCE did things")}
    assert {"summary", "experience"} <= flat
