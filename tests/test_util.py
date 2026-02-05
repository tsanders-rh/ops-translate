"""
Tests for utility modules.
"""

from ops_translate.util.files import ensure_dir, write_text
from ops_translate.util.hashing import sha256_file, sha256_string


class TestHashing:
    """Tests for hashing utilities."""

    def test_sha256_string_basic(self):
        """Test hashing a simple string."""
        result = sha256_string("hello")

        # Known SHA256 hash of "hello"
        expected = "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
        assert result == expected

    def test_sha256_string_empty(self):
        """Test hashing empty string."""
        result = sha256_string("")

        # Known SHA256 hash of empty string
        expected = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        assert result == expected

    def test_sha256_string_unicode(self):
        """Test hashing unicode string."""
        result = sha256_string("Hello 世界 🌍")

        # Should produce consistent hash
        assert len(result) == 64
        assert result.isalnum()
        assert result.islower()

    def test_sha256_file_basic(self, tmp_path):
        """Test hashing a file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello")

        result = sha256_file(test_file)

        # Should match string hash
        expected = "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
        assert result == expected

    def test_sha256_file_empty(self, tmp_path):
        """Test hashing empty file."""
        test_file = tmp_path / "empty.txt"
        test_file.write_text("")

        result = sha256_file(test_file)

        # Should match empty string hash
        expected = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        assert result == expected

    def test_sha256_file_large(self, tmp_path):
        """Test hashing large file."""
        test_file = tmp_path / "large.txt"
        test_file.write_text("x" * 10000)

        result = sha256_file(test_file)

        # Should produce valid hash
        assert len(result) == 64
        assert result.isalnum()

    def test_sha256_file_binary(self, tmp_path):
        """Test hashing binary file."""
        test_file = tmp_path / "binary.bin"
        test_file.write_bytes(b"\x00\x01\x02\x03\x04")

        result = sha256_file(test_file)

        # Should produce valid hash
        assert len(result) == 64
        assert result.isalnum()

    def test_sha256_file_consistency(self, tmp_path):
        """Test that same content produces same hash."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"

        content = "test content"
        file1.write_text(content)
        file2.write_text(content)

        hash1 = sha256_file(file1)
        hash2 = sha256_file(file2)

        assert hash1 == hash2


class TestFiles:
    """Tests for file utilities."""

    def test_ensure_dir_creates_directory(self, tmp_path):
        """Test creating new directory."""
        new_dir = tmp_path / "new" / "nested" / "dir"

        ensure_dir(new_dir)

        assert new_dir.exists()
        assert new_dir.is_dir()

    def test_ensure_dir_existing_directory(self, tmp_path):
        """Test with existing directory."""
        existing = tmp_path / "existing"
        existing.mkdir()

        # Should not raise error
        ensure_dir(existing)

        assert existing.exists()

    def test_ensure_dir_with_parents(self, tmp_path):
        """Test creating nested directories."""
        nested = tmp_path / "a" / "b" / "c" / "d"

        ensure_dir(nested)

        assert nested.exists()
        assert (tmp_path / "a").exists()
        assert (tmp_path / "a" / "b").exists()
        assert (tmp_path / "a" / "b" / "c").exists()

    def test_write_text_basic(self, tmp_path):
        """Test writing text to file."""
        test_file = tmp_path / "test.txt"
        content = "Hello, World!"

        write_text(test_file, content)

        assert test_file.exists()
        assert test_file.read_text() == content

    def test_write_text_creates_parent_dirs(self, tmp_path):
        """Test that parent directories are created."""
        nested_file = tmp_path / "a" / "b" / "c" / "file.txt"

        write_text(nested_file, "content")

        assert nested_file.exists()
        assert nested_file.read_text() == "content"

    def test_write_text_overwrites_existing(self, tmp_path):
        """Test overwriting existing file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("old content")

        write_text(test_file, "new content")

        assert test_file.read_text() == "new content"

    def test_write_text_unicode(self, tmp_path):
        """Test writing unicode content."""
        test_file = tmp_path / "unicode.txt"
        content = "Hello 世界 🌍"

        write_text(test_file, content)

        assert test_file.read_text() == content

    def test_write_text_multiline(self, tmp_path):
        """Test writing multiline content."""
        test_file = tmp_path / "multiline.txt"
        content = "Line 1\nLine 2\nLine 3"

        write_text(test_file, content)

        assert test_file.read_text() == content
        assert test_file.read_text().count("\n") == 2
