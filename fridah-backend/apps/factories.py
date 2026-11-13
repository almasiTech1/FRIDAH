import factory
from factory.django import DjangoModelFactory
from apps.users.models import User
from apps.properties.models import Property, Unit
from apps.rentals.models import Lease, Invoice
from apps.bookings.models import Listing, RoomType, Booking


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.Sequence(lambda n: f"user{n}@example.com")
    phone_number = factory.Sequence(lambda n: f"+25471234{n:04d}")
    role = User.Role.TENANT
    first_name = "Test"
    last_name = "User"

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        self.set_password(extracted or "TestPass123!")
        if create:
            self.save()


class LandlordFactory(UserFactory):
    role = User.Role.LANDLORD


class PropertyFactory(DjangoModelFactory):
    class Meta:
        model = Property

    landlord = factory.SubFactory(LandlordFactory)
    name = factory.Sequence(lambda n: f"Property {n}")
    property_type = Property.PropertyType.APARTMENT
    county = "Nairobi"
    town = "Westlands"
    status = Property.Status.ACTIVE


class UnitFactory(DjangoModelFactory):
    class Meta:
        model = Unit

    property = factory.SubFactory(PropertyFactory)
    unit_number = factory.Sequence(lambda n: f"A{n}")
    rent_amount = 25000
    deposit_amount = 25000


class LeaseFactory(DjangoModelFactory):
    class Meta:
        model = Lease

    tenant = factory.SubFactory(UserFactory)
    unit = factory.SubFactory(UnitFactory)
    landlord = factory.LazyAttribute(lambda o: o.unit.property.landlord)
    start_date = "2026-01-01"
    rent_amount = 25000
    status = Lease.Status.ACTIVE


class ListingFactory(DjangoModelFactory):
    class Meta:
        model = Listing

    host = factory.SubFactory(UserFactory, role=User.Role.HOTEL_OWNER)
    name = factory.Sequence(lambda n: f"Listing {n}")
    listing_type = Listing.ListingType.BNB
    county = "Nairobi"
    town = "Kilimani"
    status = Listing.Status.ACTIVE


class RoomTypeFactory(DjangoModelFactory):
    class Meta:
        model = RoomType

    listing = factory.SubFactory(ListingFactory)
    name = "Standard Room"
    price_per_night = 3500
    total_rooms = 5
