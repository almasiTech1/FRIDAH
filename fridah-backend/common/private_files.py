"""
Private uploads: National ID scans, agreements, statements, receipts, property documents, maintenance photos.

* They are stored under random names (no names or ID numbers in the file name).
* nginx never serves their folders. The API hands out a short-lived signed link instead, and it only does that
  while rendering a record the signed-in person is already allowed to see, so the existing access rules apply.
* Public images (listings, property photos, logos) keep their normal /media/ URLs.
"""
import os
import uuid

from django.conf import settings
from django.core import signing
from django.urls import reverse
from django.utils import timezone
from rest_framework import serializers

SALT = 'fridah.private-file'

# Folders that must never be reachable by a plain /media/ URL.
PRIVATE_PREFIXES = (
    'kyc_documents/', 'management_agreements/', 'owner_statements/', 'agency_expenses/', 'invoices/',
    'property_documents/', 'service_invoices/', 'maintenance_images/', 'utility_readings/',
)


def is_private(name: str) -> bool:
    return bool(name) and name.startswith(PRIVATE_PREFIXES)


def _random_name(folder: str, filename: str, dated: bool = False) -> str:
    ext = os.path.splitext(filename or '')[1].lower()[:10]
    sub = timezone.now().strftime('%Y/%m/') if dated else ''
    return f'{folder}/{sub}{uuid.uuid4().hex}{ext}'


# One top-level function per field (migrations must be able to import them by name).
def kyc_document_path(instance, filename): return _random_name('kyc_documents', filename)
def agreement_path(instance, filename): return _random_name('management_agreements', filename)
def statement_path(instance, filename): return _random_name('owner_statements', filename)
def expense_receipt_path(instance, filename): return _random_name('agency_expenses', filename)
def invoice_receipt_path(instance, filename): return _random_name('invoices', filename)
def property_document_path(instance, filename): return _random_name('property_documents', filename, dated=True)
def service_invoice_path(instance, filename): return _random_name('service_invoices', filename)
def maintenance_image_path(instance, filename): return _random_name('maintenance_images', filename)
def utility_photo_path(instance, filename): return _random_name('utility_readings', filename, dated=True)


def make_token(name: str) -> str:
    return signing.dumps(name, salt=SALT)


def read_token(token: str):
    """The stored file name if the link is genuine and still fresh, else None."""
    try:
        name = signing.loads(token, salt=SALT, max_age=getattr(settings, 'PRIVATE_FILE_URL_TTL', 300))
    except signing.BadSignature:
        return None
    if not isinstance(name, str) or '..' in name or name.startswith('/') or not is_private(name):
        return None
    return name


def private_url(name: str, request=None) -> str:
    url = f"{reverse('private-file')}?t={make_token(name)}"
    return request.build_absolute_uri(url) if request else url


class _PrivateMixin:
    def to_representation(self, value):
        if not value:
            return None
        if is_private(value.name):
            return private_url(value.name, self.context.get('request'))
        return super().to_representation(value)       # public image: normal /media/ URL


class PrivateFileField(_PrivateMixin, serializers.FileField):
    pass


class PrivateImageField(_PrivateMixin, serializers.ImageField):
    pass


def install():
    """Make every ModelSerializer use the private-aware fields for model FileField / ImageField."""
    from django.db import models
    mapping = serializers.ModelSerializer.serializer_field_mapping
    mapping[models.FileField] = PrivateFileField
    mapping[models.ImageField] = PrivateImageField
