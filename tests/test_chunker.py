"""
Tests for the chunker.py module
"""

from unittest.mock import patch

from src.chunker import TextChunk, TextChunker


class TestTextChunk:
    """Tests for the TextChunk class."""

    def test_text_chunk_creation(self):
        """Test TextChunk creation."""
        chunk = TextChunk(
            content="This is a test",
            start_pos=0,
            end_pos=14,
            chunk_id=1,
            chapter_id="cap1",
            overlap_start=5,
            overlap_end=10,
        )

        assert chunk.content == "This is a test"
        assert chunk.start_pos == 0
        assert chunk.end_pos == 14
        assert chunk.chunk_id == 1
        assert chunk.chapter_id == "cap1"
        assert chunk.overlap_start == 5
        assert chunk.overlap_end == 10


class TestTextChunker:
    """Tests for the TextChunker class."""

    def test_chunker_initialization(self):
        """Test chunker initialization with default parameters."""
        chunker = TextChunker()

        assert chunker.chunk_size == 4000
        assert chunker.overlap_size == 200
        assert chunker.preserve_sentences is True
        assert chunker.preserve_paragraphs is True

    def test_chunker_custom_initialization(self):
        """Test chunker initialization with custom parameters."""
        chunker = TextChunker(
            chunk_size=1000,
            overlap_size=100,
            preserve_sentences=False,
            preserve_paragraphs=False,
        )

        assert chunker.chunk_size == 1000
        assert chunker.overlap_size == 100
        assert chunker.preserve_sentences is False
        assert chunker.preserve_paragraphs is False

    def test_chunk_empty_text(self):
        """Test fragmentation of empty text."""
        chunker = TextChunker()
        chunks = chunker.chunk_text("", "test_chapter")

        assert chunks == []

    def test_chunk_short_text(self):
        """Test fragmentation of short text (smaller than chunk_size)."""
        chunker = TextChunker(chunk_size=100)
        text = "This is a short text for testing."
        chunks = chunker.chunk_text(text, "test_chapter")

        assert len(chunks) == 1
        assert chunks[0].content == text
        assert chunks[0].start_pos == 0
        assert chunks[0].end_pos == len(text)
        assert chunks[0].chunk_id == 0
        assert chunks[0].chapter_id == "test_chapter"

    def test_chunk_long_text(self):
        """Test fragmentation of long text."""
        chunker = TextChunker(chunk_size=50, overlap_size=10)
        text = "This is a very long text that needs to be divided into multiple chunks to test the fragmentation functionality."
        chunks = chunker.chunk_text(text, "test_chapter")

        assert len(chunks) > 1

        # Verify that all chunks have the correct chapter_id
        for chunk in chunks:
            assert chunk.chapter_id == "test_chapter"

        # Verify that chunk_ids are sequential
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_id == i

    def test_chunk_with_paragraphs(self):
        """Test fragmentation respecting paragraph breaks."""
        chunker = TextChunker(chunk_size=80, overlap_size=10, preserve_paragraphs=True)

        text = """First paragraph with sufficient text.

Second paragraph also with sufficient text for testing.

Third paragraph to complete the test."""

        chunks = chunker.chunk_text(text, "test_chapter")

        # Should create multiple chunks
        assert len(chunks) >= 1

        # The first chunk should end near a paragraph break
        # (we test that the logic doesn't break the code)
        for chunk in chunks:
            assert chunk.content.strip()  # Should not have empty chunks

    def test_chunk_with_sentences(self):
        """Test fragmentation respecting sentence breaks."""
        chunker = TextChunker(
            chunk_size=60,
            overlap_size=10,
            preserve_sentences=True,
            preserve_paragraphs=False,
        )

        text = "This is the first sentence. This is the second sentence! This is the third sentence? This is the fourth sentence."

        chunks = chunker.chunk_text(text, "test_chapter")

        assert len(chunks) >= 1

        # Verify that there are no empty chunks
        for chunk in chunks:
            assert chunk.content.strip()

    def test_natural_break_finding(self):
        """Test natural break finding."""
        chunker = TextChunker(chunk_size=50, overlap_size=5)
        text = "Text with paragraph.\n\nNew paragraph here. Additional sentence."

        # Test the method directly
        break_pos = chunker._find_natural_break(text, 0, 30)

        # Should find a valid position
        assert 0 <= break_pos <= len(text)

    def test_chunk_chapters(self):
        """Test fragmentation of multiple chapters."""
        chunker = TextChunker(chunk_size=50)

        chapters = [
            {"id": "cap1", "content": "Content of chapter 1 with sufficient text."},
            {"id": "cap2", "content": "Content of chapter 2 also with text."},
            {"content": "Chapter without ID"},  # Should use default ID
        ]

        all_chunks = chunker.chunk_chapters(chapters)

        assert len(all_chunks) == 3
        assert len(all_chunks[0]) >= 1  # Cap1 should have chunks
        assert len(all_chunks[1]) >= 1  # Cap2 should have chunks
        assert len(all_chunks[2]) >= 1  # Cap3 should have chunks

        # Verify chapter IDs
        assert all_chunks[0][0].chapter_id == "cap1"
        assert all_chunks[1][0].chapter_id == "cap2"
        assert all_chunks[2][0].chapter_id == "chapter_2"  # Default ID

    def test_chunk_chapters_empty_content(self):
        """Test fragmentation of chapters with empty content."""
        chunker = TextChunker()

        chapters = [
            {"id": "cap1", "content": "Valid content"},
            {"id": "cap2", "content": ""},  # Empty
            {"id": "cap3", "content": "   "},  # Only spaces
        ]

        with patch("src.chunker.logger") as mock_logger:
            all_chunks = chunker.chunk_chapters(chapters)

        assert len(all_chunks) == 3
        assert len(all_chunks[0]) >= 1  # Cap1 has content
        assert len(all_chunks[1]) == 0  # Cap2 empty
        assert len(all_chunks[2]) == 0  # Cap3 empty

        # Verify that warning was logged for empty chapters
        mock_logger.warning.assert_called()

    def test_get_chunk_with_context(self, sample_text):
        """Test getting chunk with context."""
        chunker = TextChunker(chunk_size=100, overlap_size=20)
        chunks = chunker.chunk_text(sample_text, "test")

        if len(chunks) > 1:
            # Test with middle chunk
            context_text = chunker.get_chunk_with_context(chunks[1], sample_text)

            # Should include context (overlap)
            assert len(context_text) >= len(chunks[1].content)

    def test_estimate_tokens(self):
        """Test token estimation."""
        chunker = TextChunker()

        text = "This is a test text"
        tokens = chunker.estimate_tokens(text)

        # Should return a positive number based on text
        assert tokens > 0
        assert tokens == int(len(text) * 0.25)  # Default value

        # Test with custom ratio
        tokens_custom = chunker.estimate_tokens(text, tokens_per_char=0.5)
        assert tokens_custom == int(len(text) * 0.5)

    def test_adjust_chunk_size_for_model(self):
        """Test chunk_size adjustment for different models."""
        chunker = TextChunker(chunk_size=1000)
        original_size = chunker.chunk_size

        # Test with known model
        with patch("src.chunker.logger") as mock_logger:
            chunker.adjust_chunk_size_for_model("gpt-4")

        # Chunk size should have changed
        assert chunker.chunk_size != original_size
        mock_logger.info.assert_called()

        # Test with unknown model
        chunker2 = TextChunker(chunk_size=1000)
        chunker2.adjust_chunk_size_for_model("unknown-model")

        # Should use conservative default value
        assert chunker2.chunk_size > 0

        # Test with specific max_tokens
        chunker3 = TextChunker(chunk_size=1000)
        chunker3.adjust_chunk_size_for_model("gpt-4", max_tokens=50000)
        assert chunker3.chunk_size > 0

    def test_overlap_size_adjustment(self):
        """Test if overlap_size is adjusted proportionally."""
        chunker = TextChunker(chunk_size=1000, overlap_size=100)

        chunker.adjust_chunk_size_for_model("gpt-3.5")

        # Overlap should be at most chunk_size // 20
        assert chunker.overlap_size <= chunker.chunk_size // 20


class TestIntegration:
    """Integration tests for the chunker module."""

    def test_complete_workflow(self, sample_text):
        """Test complete fragmentation workflow."""
        chunker = TextChunker(chunk_size=200, overlap_size=30)

        # Fragment the text
        chunks = chunker.chunk_text(sample_text, "integration_test")

        # Verify all chunks are valid
        assert len(chunks) > 0

        total_length = 0
        for i, chunk in enumerate(chunks):
            # Each chunk should have content
            assert chunk.content.strip()

            # IDs should be sequential
            assert chunk.chunk_id == i

            # Chapter ID should be correct
            assert chunk.chapter_id == "integration_test"

            # Positions should make sense
            assert chunk.start_pos >= 0
            assert chunk.end_pos > chunk.start_pos
            assert chunk.end_pos <= len(sample_text)

            total_length += len(chunk.content)

        # Total text of chunks should cover the original text
        # (may be larger due to overlaps)
        assert total_length >= len(sample_text.strip())

    def test_chunker_with_real_book_structure(self):
        """Test with structure similar to a real book."""
        chapters = []

        # Simulate book chapters
        for i in range(5):
            content = f"""
            Chapter {i + 1}: Chapter Title

            This is the beginning of chapter {i + 1}. The text continues with multiple
            paragraphs to simulate real book content.

            Second paragraph of chapter {i + 1}. Here we have more text to
            ensure the chunker works correctly with realistic content.

            "Example dialogue," said the main character. "This dialogue
            should also be preserved properly."

            Final paragraph of chapter {i + 1} with adequate conclusion.
            """

            chapters.append(
                {
                    "id": f"cap_{i + 1}",
                    "title": f"Chapter {i + 1}",
                    "content": content.strip(),
                }
            )

        chunker = TextChunker(chunk_size=300, overlap_size=50)
        all_chunks = chunker.chunk_chapters(chapters)

        # Verify general structure
        assert len(all_chunks) == 5

        # Verify all chapters were processed
        total_chunks = sum(len(chapter_chunks) for chapter_chunks in all_chunks)
        assert total_chunks > 0

        # Verify consistency between chapters
        for i, chapter_chunks in enumerate(all_chunks):
            expected_chapter_id = f"cap_{i + 1}"

            for chunk in chapter_chunks:
                assert chunk.chapter_id == expected_chapter_id
                assert chunk.content.strip()  # Should not have empty chunks
