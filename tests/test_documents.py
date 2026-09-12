from app.files.document_store import sanitize_name


def test_sanitize_name_blocks_path_components():
    assert sanitize_name("../../secret.pdf") == "secret.pdf"


def test_sanitize_name_normalizes_spaces():
    assert sanitize_name("my report.pdf") == "my_report.pdf"
