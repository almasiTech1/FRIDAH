"""Private uploads are never public: random names, signed short-lived links, nginx blocks their folders."""
import re
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.rentals.models import Invoice
from common.private_files import is_private, make_token, private_url, read_token

DOWNLOAD = '/api/v1/files/private/'


@pytest.fixture(autouse=True)
def tmp_media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    yield


@pytest.fixture
def invoice_with_receipt(lease, tenant):
    inv = Invoice.objects.create(lease=lease, tenant=tenant, invoice_type='rent', amount=Decimal('1000'),
                                 period_start=date(2026, 1, 1), period_end=date(2026, 1, 31), due_date=date(2026, 1, 5))
    inv.pdf_receipt.save('John-Doe-receipt.pdf', ContentFile(b'%PDF-1.4 receipt'))
    return inv


@pytest.mark.django_db
class TestPrivateFiles:
    def test_uploaded_names_are_random_and_do_not_leak_the_original(self, tenant):
        tenant.kyc_document = SimpleUploadedFile('Jane-Wanjiru-National-ID-12345678.jpg', b'x', content_type='image/jpeg')
        tenant.save()
        assert tenant.kyc_document.name.startswith('kyc_documents/')
        assert 'Jane' not in tenant.kyc_document.name and '12345678' not in tenant.kyc_document.name
        assert re.fullmatch(r'kyc_documents/[0-9a-f]{32}\.jpg', tenant.kyc_document.name)

    def test_api_returns_a_signed_link_not_a_media_url(self, api_client, tenant, invoice_with_receipt):
        api_client.force_authenticate(user=tenant)
        resp = api_client.get(f'/api/v1/invoices/{invoice_with_receipt.id}/')
        body = resp.data.get('data', resp.data)
        link = body['pdf_receipt']
        assert '/media/' not in link and '/api/v1/files/private/?t=' in link

    def test_the_signed_link_downloads_the_file_and_is_locked_down(self, api_client, invoice_with_receipt):
        r = api_client.get(DOWNLOAD, {'t': make_token(invoice_with_receipt.pdf_receipt.name)})
        assert r.status_code == 200
        assert b''.join(r.streaming_content) == b'%PDF-1.4 receipt'
        assert r['Cache-Control'] == 'private, no-store' and r['X-Content-Type-Options'] == 'nosniff' and 'sandbox' in r['Content-Security-Policy']

    def test_tampered_missing_and_guessed_links_are_refused(self, api_client, invoice_with_receipt):
        name = invoice_with_receipt.pdf_receipt.name
        good = make_token(name)
        assert api_client.get(DOWNLOAD, {'t': good[:-3] + 'abc'}).status_code == 404
        assert api_client.get(DOWNLOAD).status_code == 404
        assert api_client.get(DOWNLOAD, {'t': name}).status_code == 404                      # a plain file path is not a token
        assert api_client.get(DOWNLOAD, {'t': make_token('property_images/x.jpg')}).status_code == 404   # public folders are not served here

    def test_links_expire(self, api_client, invoice_with_receipt, settings):
        token = make_token(invoice_with_receipt.pdf_receipt.name)
        settings.PRIVATE_FILE_URL_TTL = -1
        assert api_client.get(DOWNLOAD, {'t': token}).status_code == 404

    def test_path_tricks_are_rejected(self):
        for bad in ('kyc_documents/../../etc/passwd', '/etc/passwd', 'kyc_documents/../settings.py'):
            assert read_token(make_token(bad)) is None

    def test_public_images_keep_their_normal_media_url(self, api_client, landlord, property_):
        from apps.properties.models import PropertyImage
        img = PropertyImage.objects.create(property=property_, image=SimpleUploadedFile('front.jpg', b'x', content_type='image/jpeg'))
        assert not is_private(img.image.name)
        api_client.force_authenticate(user=landlord)
        data = api_client.get(f'/api/v1/properties/{property_.id}/').data
        text = str(data)
        assert '/media/property_images/' in text and 'files/private' not in text


def test_nginx_only_serves_public_image_folders():
    conf = (Path(__file__).resolve().parent.parent / 'nginx' / 'nginx.conf').read_text()
    assert 'alias /app/media/' not in conf                      # the old, serve-everything rule is gone
    public = re.search(r'location ~ \^/media/\(([^)]*)\)/', conf)
    assert public and set(public.group(1).split('|')) == {'agency_logos', 'profile_photos', 'property_images', 'unit_images', 'listing_images'}
    assert re.search(r'location /media/ \{\s*return 404;', conf)
    for private in ('kyc_documents', 'management_agreements', 'owner_statements', 'invoices', 'property_documents'):
        assert private not in public.group(1)
