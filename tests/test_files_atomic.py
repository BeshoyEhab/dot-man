import pytest
from pathlib import Path
from dot_man.files import atomic_write_text, smart_save_file
from dot_man.secrets import SecretMatch, SecretGuard

def test_atomic_write_text(tmp_path):
    dest = tmp_path / "atomic.txt"
    content = "Atomic Content\nLine 2"
    
    atomic_write_text(dest, content)
    
    assert dest.exists()
    assert dest.read_text(encoding="utf-8") == content
    
    # Check no temp file remains
    assert not (tmp_path / "atomic.txt.tmp").exists()

def test_atomic_write_text_overwrite(tmp_path):
    dest = tmp_path / "overwrite.txt"
    dest.write_text("Old Content", encoding="utf-8")
    
    new_content = "New Content"
    atomic_write_text(dest, new_content)
    
    assert dest.read_text(encoding="utf-8") == new_content

def test_smart_save_file_identical(tmp_path):
    src = tmp_path / "src.txt"
    dest = tmp_path / "dest.txt"
    content = "Identical Content"
    
    src.write_text(content, encoding="utf-8")
    dest.write_text(content, encoding="utf-8")
    
    # Copy permissions
    dest.chmod(src.stat().st_mode)
    
    saved, secrets = smart_save_file(src, dest)
    
    assert not saved
    assert not secrets

def test_smart_save_file_modified_content(tmp_path):
    src = tmp_path / "src_mod.txt"
    dest = tmp_path / "dest_mod.txt"
    
    src.write_text("New Content", encoding="utf-8")
    dest.write_text("Old Content", encoding="utf-8")
    
    saved, secrets = smart_save_file(src, dest)
    
    assert saved
    assert dest.read_text(encoding="utf-8") == "New Content"

def test_smart_save_file_new_dest(tmp_path):
    src = tmp_path / "src_new.txt"
    dest = tmp_path / "dest_new.txt"
    
    src.write_text("Content", encoding="utf-8")
    
    saved, secrets = smart_save_file(src, dest)
    
    assert saved
    assert dest.exists()
    assert dest.read_text(encoding="utf-8") == "Content"

def test_smart_save_file_secrets(tmp_path):
    src = tmp_path / "src_secret.txt"
    dest = tmp_path / "dest_secret.txt"
    
    # "password = '123'" triggers "Password Assignment" pattern (HIGH severity)
    content = """config = 1
password = 'super_secret'
"""
    src.write_text(content, encoding="utf-8")
    
    saved, secrets = smart_save_file(src, dest, check_secrets=True)
    
    assert saved
    assert len(secrets) == 1
    assert secrets[0].matched_text == "password = 'super_secret'"
    
    # Check it was redacted in destination
    dest_content = dest.read_text(encoding="utf-8")
    assert "***REDACTED***" in dest_content
    # But source remains untouched? (smart_save doesn't touch source)
    assert src.read_text(encoding="utf-8") == content

def test_smart_save_file_secrets_handler_keep(tmp_path):
    src = tmp_path / "src_keep.txt"
    dest = tmp_path / "dest_keep.txt"
    
    content = "password = 'keep_me'"
    src.write_text(content, encoding="utf-8")
    
    def handler(match):
        return "KEEP"
        
    saved, secrets = smart_save_file(src, dest, secret_handler=handler)
    
    # Even if we kept it, smart_save_file considers it "saved" if we wrote it.
    # But compare: filtered content == content. So if dest doesn't exist, we save.
    # If dest DOES exist and matches content, we don't save.
    
    assert saved
    dest_content = dest.read_text(encoding="utf-8")
    assert "password = 'keep_me'" in dest_content
    
    # Run again - should be False now
    saved_again, secrets_again = smart_save_file(src, dest, secret_handler=handler)
    assert not saved_again

def test_smart_save_file_ignored_secret(tmp_path):
    src = tmp_path / "src_ignored.txt"
    dest = tmp_path / "dest_ignored.txt"
    
    content = "password = 'ignore_this_secret'\n"
    src.write_text(content, encoding="utf-8")
    
    def handler(match):
        return "IGNORE"
        
    saved, secrets = smart_save_file(src, dest, secret_handler=handler)
    
    assert saved
    assert len(secrets) == 0
    
    dest_content = dest.read_text(encoding="utf-8")
    assert "password = 'ignore_this_secret'" in dest_content
    assert "***REDACTED***" not in dest_content


