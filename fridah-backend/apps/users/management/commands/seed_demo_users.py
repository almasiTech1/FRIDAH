"""
Creates one demo account per role with known credentials, so you have something to
log in with immediately after `migrate` without registering manually.

Usage: python manage.py seed_demo_users
Safe to re-run - uses get_or_create, won't duplicate or error on existing accounts.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

DEMO_PASSWORD = "Fridah@2026"

DEMO_USERS = [
    dict(username="demo_admin", email="admin@fridah.co.ke", phone_number="+254711000001",
         role=User.Role.ADMIN, first_name="Admin", last_name="User",
         is_staff=True, is_superuser=True),
    dict(username="demo_tenant", email="tenant@fridah.co.ke", phone_number="+254711000002",
         role=User.Role.TENANT, first_name="Tenant", last_name="Demo"),
    dict(username="demo_landlord", email="landlord@fridah.co.ke", phone_number="+254711000003",
         role=User.Role.LANDLORD, first_name="Landlord", last_name="Demo"),
    dict(username="demo_provider", email="provider@fridah.co.ke", phone_number="+254711000004",
         role=User.Role.SERVICE_PROVIDER, first_name="Provider", last_name="Demo"),
    dict(username="demo_hotel", email="hotel@fridah.co.ke", phone_number="+254711000005",
         role=User.Role.HOTEL_OWNER, first_name="Hotel", last_name="Demo"),
    # Agency isn't a User.role choice - it's granted via AgencyMembership (see below) -
    # but this account still needs *some* base role, so LANDLORD is the closest fit.
    dict(username="demo_agency", email="agency@fridah.co.ke", phone_number="+254711000006",
         role=User.Role.LANDLORD, first_name="Agency", last_name="Demo"),
]

DEMO_AGENCY_NAME = "Fridah Demo Property Managers"


class Command(BaseCommand):
    help = "Seed one demo user per role (tenant, landlord, admin, service_provider, hotel_owner, agency) for local login/testing."

    def handle(self, *args, **options):
        for data in DEMO_USERS:
            user, created = User.objects.get_or_create(
                email=data["email"],
                defaults={k: v for k, v in data.items() if k != "email"},
            )
            # get_or_create only applies `defaults` when the row is first created - if this
            # account already existed for any reason (an earlier partial run, a manual
            # registration, etc), role/is_staff/is_superuser would silently be left at
            # whatever they already were, which is exactly how an "admin" account can end up
            # without real admin permissions. Force these onto every run, not just creation.
            user.role = data['role']
            user.is_staff = data.get('is_staff', False)
            user.is_superuser = data.get('is_superuser', False)
            user.first_name = data['first_name']
            user.last_name = data['last_name']
            user.set_password(DEMO_PASSWORD)
            # KYC-gate a couple of tenant-only flows (risk score, blacklist checks) rely on
            # a verified tenant, so mark the demo tenant verified out of the box.
            # (is_kyc_verified is a read-only property derived from kyc_status - setting
            # kyc_status alone is enough, and assigning the property directly raises.)
            if user.role == User.Role.TENANT:
                user.kyc_status = User.KYCStatus.VERIFIED
            user.is_phone_verified = True
            user.is_active = True
            user.save()

            status = "created" if created else "updated (role/password reset to defaults)"
            self.stdout.write(self.style.SUCCESS(f"  {status}: {user.email} ({user.role})"))

        self._seed_demo_agency()

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"All demo accounts use the password: {DEMO_PASSWORD}"))

    def _seed_demo_agency(self):
        """
        Give demo_agency an actual Agency (with its standard roles + an active
        AgencyMembership) so the agency portal has something to log into, instead of
        just landing on the empty "create an agency" bootstrap screen.
        """
        from apps.agencies.models import Agency, AgencyMembership
        from apps.agencies import services as agency_services

        agency_user = User.objects.get(email="agency@fridah.co.ke")
        agency = Agency.objects.filter(created_by=agency_user, name=DEMO_AGENCY_NAME).first()

        if agency is None:
            agency = agency_services.create_agency(
                name=DEMO_AGENCY_NAME,
                created_by=agency_user,
                email="agency@fridah.co.ke",
                phone_number="+254711000006",
                county="Nairobi",
                town="Westlands",
                default_fee_percent=5.0,
            )
            action = "created"
        else:
            action = "already exists"

        # create_agency() defaults new agencies to pending_approval (an admin normally
        # reviews/approves them) - force this one active so the demo account can use
        # every feature (assignments, statements, payouts) right away.
        if agency.status != Agency.Status.ACTIVE:
            agency.status = Agency.Status.ACTIVE
            agency.save(update_fields=["status"])

        membership = AgencyMembership.objects.filter(agency=agency, user=agency_user).first()
        if membership and membership.status != AgencyMembership.Status.ACTIVE:
            membership.status = AgencyMembership.Status.ACTIVE
            membership.save(update_fields=["status"])

        self.stdout.write(self.style.SUCCESS(f"  {action}: agency \"{agency.name}\" (active, admin: {agency_user.email})"))
