import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile

from common.validators import validate_document_extension, MaxFileSizeValidator


class TestDocumentExtensionValidator:
    def test_allows_pdf(self):
        f = SimpleUploadedFile('lease.pdf', b'%PDF-1.4 fake pdf bytes')
        validate_document_extension(f)  # should not raise

    def test_allows_jpg(self):
        f = SimpleUploadedFile('id_photo.jpg', b'fake jpg bytes')
        validate_document_extension(f)

    def test_rejects_html(self):
        """The core regression case: before this validator existed, a file
        literally named exploit.html could be uploaded as a KYC/property document."""
        f = SimpleUploadedFile('exploit.html', b'<script>alert(1)</script>')
        with pytest.raises(ValidationError):
            validate_document_extension(f)

    def test_rejects_svg(self):
        f = SimpleUploadedFile('exploit.svg', b'<svg onload=alert(1)>')
        with pytest.raises(ValidationError):
            validate_document_extension(f)

    def test_rejects_executable(self):
        f = SimpleUploadedFile('payload.exe', b'MZ\x90\x00')
        with pytest.raises(ValidationError):
            validate_document_extension(f)

    def test_rejects_no_extension(self):
        f = SimpleUploadedFile('noextension', b'some bytes')
        with pytest.raises(ValidationError):
            validate_document_extension(f)


class TestMaxFileSizeValidator:
    def test_allows_file_under_limit(self):
        validator = MaxFileSizeValidator(max_mb=1)
        f = SimpleUploadedFile('small.pdf', b'x' * 1000)
        validator(f)  # should not raise

    def test_rejects_file_over_limit(self):
        validator = MaxFileSizeValidator(max_mb=1)
        f = SimpleUploadedFile('big.pdf', b'x' * (2 * 1024 * 1024))
        with pytest.raises(ValidationError):
            validator(f)

    def test_equality_for_migrations(self):
        """MaxFileSizeValidator must be deconstructible/comparable so Django doesn't
        generate a spurious new migration every time makemigrations is run."""
        assert MaxFileSizeValidator(5) == MaxFileSizeValidator(5)
        assert MaxFileSizeValidator(5) != MaxFileSizeValidator(10)
