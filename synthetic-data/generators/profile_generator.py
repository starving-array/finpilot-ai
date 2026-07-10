import uuid
import json
from datetime import datetime, timezone
from faker import Faker

fake = Faker("en_IN")
Faker.seed(42)

BUSINESS_NAMES = [
    "TechSolutions India", "Greenfield Farms", "Urban Crafts", "SpiceRoute Exports",
    "RiverSide Mills", "CloudNine Services", "GoldenHands Constructions",
    "FreshBake Foods", "SwiftLogistics", "BlueMoon Agencies",
    "Pioneer Engineering", "Saraswati Printers", "Om Metals",
    "Shakti Trading", "Laxmi Containers", "Krishna Agro",
    "Ganesh Electronics", "Durga Textiles", "Hanuman Pharma",
    "Surya Solar", "Ramesh Enterprises", "Priya Garments",
    "Vinayak Auto Parts", "Maha Digital", "Bharat Polymers",
]

SECTORS = [
    "Manufacturing", "Retail", "Services", "Agriculture", "Construction",
    "Transport", "Food Processing", "Textiles", "Pharmaceuticals",
    "Renewable Energy", "IT Services", "NBFC", "Real Estate",
    "Auto Components", "Chemicals",
]


def generate_pan() -> str:
    pan = fake.bothify(text="?????####?", letters="ABCDEFGHIJKLMNOPQRSTUVWXYZ").upper()
    return pan


def generate_cin() -> str:
    year = fake.year()
    reg = fake.random_int(1, 999999)
    return f"U{fake.random_element('ABCDEFGH')}{fake.random_int(10,99)}MH{year}PLC{reg:06d}"


def generate_customer_profile(blank_slate: bool = False, seed: int | None = None) -> dict:
    if seed is not None:
        Faker.seed(seed)
        fake.seed_instance(seed)

    name = fake.random_element(BUSINESS_NAMES)
    pan = generate_pan()
    kyc_status = fake.random_element(["VERIFIED", "VERIFIED", "VERIFIED", "PENDING", "REJECTED"])
    sector = fake.random_element(SECTORS)
    vintage_months = fake.random_int(3, 120)

    return {
        "customer_id": str(uuid.uuid4()),
        "pan": pan,
        "cin": generate_cin() if fake.boolean(70) else None,
        "name": name,
        "kyc_status": kyc_status,
        "sector": sector,
        "vintage_months": vintage_months,
        "blank_slate": blank_slate,
    }
