"""
Shared upload validators for plain FileField uploads (as opposed to ImageField,
which already gets Pillow-based "is this actually an image" validation for free
from Django).

Before this module existed, several FileFields across the platform (KYC documents,
property compliance documents, management agreements, owner statements, agency
expense receipts) accepted *any* file type/size with no server-side check at all.
Since these are stored under MEDIA_ROOT and served back to users (landlords,
tenants, agency staff) via MEDIA_URL, an unrestricted upload is a real risk:
depending on how media is served in a given deployment, an uploaded .html/.svg/
.js file can be rendered/executed in the browser context of whoever opens it
(stored XSS), and unrestricted size opens a simple disk-exhaustion DoS vector.

Usage on a model field:

    from common.validators import validate_document_extension, MaxFileSizeValidator

    file = models.FileField(
        upload_to='property_documents/%Y/%m/',
        validators=[validate_document_extension, MaxFileSizeValidator(10)],
    )

This is allow-list based deliberately (reject anything not explicitly permitted)
rather than deny-list based.
"""
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.utils.deconstruct import deconstructible

# Business documents (KYC, compliance certs, management agreements, statements,
# receipts) are expected to be PDFs, common office formats, or a photo of a
# physical document. Nothing executable, no markup formats (.html/.svg/.xml),
# no archives.
ALLOWED_DOCUMENT_EXTENSIONS = ['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png']

validate_document_extension = FileExtensionValidator(
    allowed_extensions=ALLOWED_DOCUMENT_EXTENSIONS,
    message=(
        'Unsupported file type. Allowed: ' + ', '.join(ALLOWED_DOCUMENT_EXTENSIONS)
    ),
)


@deconstructible
class MaxFileSizeValidator:
    """Rejects files over `max_mb` megabytes. Deconstructible so it survives migrations."""

    def __init__(self, max_mb: int):
        self.max_mb = max_mb
        self.max_bytes = max_mb * 1024 * 1024

    def __call__(self, value):
        size = getattr(value, 'size', None)
        if size is not None and size > self.max_bytes:
            raise ValidationError(f'File must be under {self.max_mb}MB.')

    def __eq__(self, other):
        return isinstance(other, MaxFileSizeValidator) and self.max_mb == other.max_mb
