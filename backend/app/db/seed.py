"""
Seed data for PropBase platform.
Run with: python -m app.db.seed
"""
import asyncio
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import os
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.models.user import User, UserRole
from app.models.location import Country, City, District
from app.models.project import Project, Developer, ProjectStatus, PropertyType, OwnershipType, Visibility
from app.models.unit import Unit, UnitStatus
from app.models.price import PriceVersion, PriceHistory, PriceVersionStatus
from app.models.collection import Collection, CollectionItem
from app.core.security import get_password_hash

# Database URL
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql+asyncpg://propbase:propbase123@localhost:5432/propbase"
)


async def seed_locations(session: AsyncSession):
    """Seed countries, cities and districts"""
    print("Seeding locations...")
    
    # Countries
    countries_data = [
        {"name_en": "Thailand", "name_ru": "Таиланд", "code": "TH"},
        {"name_en": "Indonesia", "name_ru": "Индонезия", "code": "ID"},
    ]
    
    countries = {}
    for data in countries_data:
        country = Country(**data)
        session.add(country)
        await session.flush()
        countries[data["code"]] = country
    
    # Cities
    cities_data = [
        {"name_en": "Phuket", "name_ru": "Пхукет", "country": "TH", "lat": 7.8804, "lng": 98.3923},
        {"name_en": "Pattaya", "name_ru": "Паттайя", "country": "TH", "lat": 12.9236, "lng": 100.8825},
        {"name_en": "Bali", "name_ru": "Бали", "country": "ID", "lat": -8.3405, "lng": 115.0920},
    ]
    
    cities = {}
    for data in cities_data:
        city = City(
            name_en=data["name_en"],
            name_ru=data["name_ru"],
            country_id=countries[data["country"]].id,
            lat=data["lat"],
            lng=data["lng"]
        )
        session.add(city)
        await session.flush()
        cities[data["name_en"]] = city
    
    # Districts for Phuket
    phuket_districts = [
        {"name_en": "Bang Tao", "name_ru": "Банг Тао", "slug": "bang-tao", "lat": 7.9654, "lng": 98.2915},
        {"name_en": "Surin Beach", "name_ru": "Сурин Бич", "slug": "surin-beach", "lat": 7.9723, "lng": 98.2795},
        {"name_en": "Kamala", "name_ru": "Камала", "slug": "kamala", "lat": 7.9544, "lng": 98.2838},
        {"name_en": "Patong", "name_ru": "Патонг", "slug": "patong", "lat": 7.8961, "lng": 98.2972},
        {"name_en": "Kata", "name_ru": "Ката", "slug": "kata", "lat": 7.8203, "lng": 98.2982},
        {"name_en": "Rawai", "name_ru": "Равай", "slug": "rawai", "lat": 7.7778, "lng": 98.3227},
        {"name_en": "Chalong", "name_ru": "Чалонг", "slug": "chalong", "lat": 7.8377, "lng": 98.3401},
        {"name_en": "Nai Harn", "name_ru": "Най Харн", "slug": "nai-harn", "lat": 7.7697, "lng": 98.3047},
        {"name_en": "Laguna", "name_ru": "Лагуна", "slug": "laguna", "lat": 7.9877, "lng": 98.2883},
        {"name_en": "Cherngtalay", "name_ru": "Чернгталай", "slug": "cherngtalay", "lat": 7.9801, "lng": 98.3145},
    ]
    
    # Districts for Pattaya
    pattaya_districts = [
        {"name_en": "Jomtien", "name_ru": "Джомтьен", "slug": "jomtien", "lat": 12.8698, "lng": 100.8754},
        {"name_en": "Pratumnak Hill", "name_ru": "Пратамнак", "slug": "pratumnak", "lat": 12.9054, "lng": 100.8637},
        {"name_en": "Central Pattaya", "name_ru": "Центр Паттайи", "slug": "central-pattaya", "lat": 12.9357, "lng": 100.8824},
        {"name_en": "Na Jomtien", "name_ru": "На Джомтьен", "slug": "na-jomtien", "lat": 12.8211, "lng": 100.8976},
        {"name_en": "Wongamat", "name_ru": "Вонгамат", "slug": "wongamat", "lat": 12.9584, "lng": 100.8751},
    ]
    
    # Districts for Bali
    bali_districts = [
        {"name_en": "Seminyak", "name_ru": "Семиньяк", "slug": "seminyak", "lat": -8.6917, "lng": 115.1615},
        {"name_en": "Canggu", "name_ru": "Чангу", "slug": "canggu", "lat": -8.6478, "lng": 115.1385},
        {"name_en": "Ubud", "name_ru": "Убуд", "slug": "ubud", "lat": -8.5069, "lng": 115.2624},
        {"name_en": "Uluwatu", "name_ru": "Улувату", "slug": "uluwatu", "lat": -8.8291, "lng": 115.0849},
        {"name_en": "Sanur", "name_ru": "Санур", "slug": "sanur", "lat": -8.6933, "lng": 115.2615},
    ]
    
    districts = {}
    for city_name, district_list in [
        ("Phuket", phuket_districts),
        ("Pattaya", pattaya_districts),
        ("Bali", bali_districts),
    ]:
        for data in district_list:
            district = District(
                name_en=data["name_en"],
                name_ru=data["name_ru"],
                slug=data["slug"],
                city_id=cities[city_name].id,
                lat=data["lat"],
                lng=data["lng"]
            )
            session.add(district)
            await session.flush()
            districts[data["slug"]] = district
    
    await session.commit()
    print(f"  Created {len(countries)} countries, {len(cities)} cities, {len(districts)} districts")
    return countries, cities, districts


async def seed_developers(session: AsyncSession):
    """Seed developers"""
    print("Seeding developers...")
    
    developers_data = [
        {
            "name_en": "Sansiri",
            "name_ru": "Сансири",
            "slug": "sansiri",
            "website": "https://www.sansiri.com",
            "description_en": "One of Thailand's largest property developers",
            "logo_url": "https://images.unsplash.com/photo-1560518883-ce09059eeffa?w=200",
        },
        {
            "name_en": "Ananda Development",
            "name_ru": "Ананда Девелопмент",
            "slug": "ananda",
            "website": "https://www.ananda.co.th",
            "description_en": "Leading Thai property developer",
        },
        {
            "name_en": "Origin Property",
            "name_ru": "Ориджин Проперти",
            "slug": "origin",
            "website": "https://www.origin.co.th",
            "description_en": "Innovative Thai developer",
        },
        {
            "name_en": "AP Thailand",
            "name_ru": "АП Таиланд",
            "slug": "ap-thailand",
            "website": "https://www.apthai.com",
        },
        {
            "name_en": "Utopia Development",
            "name_ru": "Утопия Девелопмент",
            "slug": "utopia",
            "description_en": "Phuket specialist developer",
        },
        {
            "name_en": "Bali Villas",
            "name_ru": "Бали Виллас",
            "slug": "bali-villas",
            "description_en": "Premium Bali villa developer",
        },
    ]
    
    developers = {}
    for data in developers_data:
        dev = Developer(**data)
        session.add(dev)
        await session.flush()
        developers[data["slug"]] = dev
    
    await session.commit()
    print(f"  Created {len(developers)} developers")
    return developers


async def seed_users(session: AsyncSession):
    """Seed users"""
    print("Seeding users...")
    
    users_data = [
        {
            "email": "admin@propbase.com",
            "hashed_password": get_password_hash("admin123"),
            "first_name": "Admin",
            "last_name": "User",
            "role": UserRole.ADMIN,
            "is_active": True,
            "email_verified": True,
            "preferred_language": "en",
        },
        {
            "email": "agent@propbase.com",
            "hashed_password": get_password_hash("agent123"),
            "first_name": "John",
            "last_name": "Agent",
            "role": UserRole.AGENT,
            "is_active": True,
            "email_verified": True,
            "preferred_language": "en",
            "agency_name": "Premium Realty",
        },
        {
            "email": "agent.ru@propbase.com",
            "hashed_password": get_password_hash("agent123"),
            "first_name": "Анна",
            "last_name": "Агент",
            "role": UserRole.AGENT,
            "is_active": True,
            "email_verified": True,
            "preferred_language": "ru",
            "agency_name": "РусРиелти",
        },
        {
            "email": "content@propbase.com",
            "hashed_password": get_password_hash("content123"),
            "first_name": "Content",
            "last_name": "Manager",
            "role": UserRole.CONTENT_MANAGER,
            "is_active": True,
            "email_verified": True,
        },
        {
            "email": "analyst@propbase.com",
            "hashed_password": get_password_hash("analyst123"),
            "first_name": "Data",
            "last_name": "Analyst",
            "role": UserRole.ANALYST,
            "is_active": True,
            "email_verified": True,
        },
    ]
    
    users = {}
    for data in users_data:
        user = User(**data)
        session.add(user)
        await session.flush()
        users[data["email"]] = user
    
    await session.commit()
    print(f"  Created {len(users)} users")
    return users


async def seed_projects_and_units(
    session: AsyncSession, 
    districts: dict, 
    developers: dict
):
    """Seed projects and their units"""
    print("Seeding projects and units...")
    
    # Sample property images
    property_images = [
        "https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?w=800",
        "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?w=800",
        "https://images.unsplash.com/photo-1613977257363-707ba9348227?w=800",
        "https://images.unsplash.com/photo-1512917774080-9991f1c4c750?w=800",
        "https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?w=800",
        "https://images.unsplash.com/photo-1613490493576-7fde63acd811?w=800",
    ]
    
    # Phuket projects
    phuket_projects = [
        {
            "name_en": "Ocean View Residence",
            "name_ru": "Резиденция Океан Вью",
            "slug": "ocean-view-residence",
            "district": "bang-tao",
            "developer": "sansiri",
            "status": ProjectStatus.SELLING,
            "property_types": [PropertyType.CONDO, PropertyType.APARTMENT],
            "ownership_type": OwnershipType.FREEHOLD,
            "completion_year": 2025,
            "completion_quarter": "Q2 2025",
            "description_en": "Luxury beachfront condominiums with stunning ocean views. Resort-style living with world-class amenities.",
            "description_ru": "Роскошные кондоминиумы на берегу моря с потрясающим видом на океан. Курортный стиль жизни с инфраструктурой мирового класса.",
            "amenities": ["Swimming Pool", "Fitness Center", "Beach Access", "Restaurant", "Spa", "Parking"],
            "lat": 7.9654,
            "lng": 98.2915,
            "min_price_usd": 150000,
            "max_price_usd": 850000,
            "total_units": 120,
            "available_units": 45,
        },
        {
            "name_en": "Surin Heights",
            "name_ru": "Сурин Хайтс",
            "slug": "surin-heights",
            "district": "surin-beach",
            "developer": "utopia",
            "status": ProjectStatus.SELLING,
            "property_types": [PropertyType.VILLA],
            "ownership_type": OwnershipType.LEASEHOLD,
            "leasehold_years": 30,
            "completion_year": 2024,
            "completion_quarter": "Q4 2024",
            "description_en": "Exclusive hillside villas with panoramic sea views. Private pools and premium finishes.",
            "description_ru": "Эксклюзивные виллы на склоне холма с панорамным видом на море. Собственные бассейны и премиальная отделка.",
            "amenities": ["Private Pool", "Garden", "Sea View", "Security", "Concierge"],
            "lat": 7.9723,
            "lng": 98.2795,
            "min_price_usd": 450000,
            "max_price_usd": 1500000,
            "total_units": 24,
            "available_units": 8,
        },
        {
            "name_en": "Kamala Bay Villas",
            "name_ru": "Виллы Камала Бэй",
            "slug": "kamala-bay-villas",
            "district": "kamala",
            "developer": "origin",
            "status": ProjectStatus.CONSTRUCTION,
            "property_types": [PropertyType.VILLA, PropertyType.TOWNHOUSE],
            "ownership_type": OwnershipType.FREEHOLD,
            "completion_year": 2026,
            "completion_quarter": "Q1 2026",
            "description_en": "Modern tropical villas in quiet Kamala area. Close to beach with stunning mountain backdrop.",
            "description_ru": "Современные тропические виллы в тихом районе Камала. Близко к пляжу с захватывающим видом на горы.",
            "amenities": ["Swimming Pool", "Garden", "Parking", "Security", "Club House"],
            "lat": 7.9544,
            "lng": 98.2838,
            "min_price_usd": 380000,
            "max_price_usd": 950000,
            "total_units": 36,
            "available_units": 28,
            "construction_progress": 35,
        },
        {
            "name_en": "Laguna Living",
            "name_ru": "Лагуна Ливинг",
            "slug": "laguna-living",
            "district": "laguna",
            "developer": "ananda",
            "status": ProjectStatus.SELLING,
            "property_types": [PropertyType.CONDO],
            "ownership_type": OwnershipType.FREEHOLD,
            "completion_year": 2024,
            "completion_quarter": "Q3 2024",
            "description_en": "Premium condos in the heart of Laguna area with golf course access.",
            "description_ru": "Премиум кондо в самом сердце района Лагуна с доступом к гольф-полю.",
            "amenities": ["Swimming Pool", "Gym", "Golf Access", "Restaurant", "Kids Club"],
            "lat": 7.9877,
            "lng": 98.2883,
            "min_price_usd": 180000,
            "max_price_usd": 650000,
            "total_units": 200,
            "available_units": 62,
        },
    ]
    
    # Pattaya projects
    pattaya_projects = [
        {
            "name_en": "Jomtien Beach Tower",
            "name_ru": "Джомтьен Бич Тауэр",
            "slug": "jomtien-beach-tower",
            "district": "jomtien",
            "developer": "ap-thailand",
            "status": ProjectStatus.SELLING,
            "property_types": [PropertyType.CONDO],
            "ownership_type": OwnershipType.FREEHOLD,
            "completion_year": 2025,
            "completion_quarter": "Q2 2025",
            "description_en": "High-rise beachfront condos with stunning views of Jomtien beach.",
            "description_ru": "Высотные кондо на берегу моря с потрясающим видом на пляж Джомтьен.",
            "amenities": ["Infinity Pool", "Gym", "Sky Lounge", "Beach Club", "Parking"],
            "lat": 12.8698,
            "lng": 100.8754,
            "min_price_usd": 85000,
            "max_price_usd": 450000,
            "total_units": 350,
            "available_units": 180,
        },
        {
            "name_en": "Pratumnak Luxury",
            "name_ru": "Пратумнак Люкс",
            "slug": "pratumnak-luxury",
            "district": "pratumnak",
            "developer": "origin",
            "status": ProjectStatus.COMPLETED,
            "property_types": [PropertyType.CONDO, PropertyType.PENTHOUSE],
            "ownership_type": OwnershipType.FREEHOLD,
            "completion_year": 2023,
            "completion_quarter": "Q2 2023",
            "description_en": "Boutique luxury condos on prestigious Pratumnak Hill.",
            "description_ru": "Бутиковые роскошные кондо на престижном холме Пратамнак.",
            "amenities": ["Pool", "Gym", "Sauna", "Garden", "24h Security"],
            "lat": 12.9054,
            "lng": 100.8637,
            "min_price_usd": 120000,
            "max_price_usd": 580000,
            "total_units": 80,
            "available_units": 15,
        },
    ]
    
    # Bali projects
    bali_projects = [
        {
            "name_en": "Canggu Beach Villas",
            "name_ru": "Виллы Чангу Бич",
            "slug": "canggu-beach-villas",
            "district": "canggu",
            "developer": "bali-villas",
            "status": ProjectStatus.SELLING,
            "property_types": [PropertyType.VILLA],
            "ownership_type": OwnershipType.LEASEHOLD,
            "leasehold_years": 25,
            "completion_year": 2024,
            "completion_quarter": "Q4 2024",
            "description_en": "Stunning Balinese villas near Echo Beach with tropical gardens.",
            "description_ru": "Потрясающие балийские виллы рядом с пляжем Эхо с тропическими садами.",
            "amenities": ["Private Pool", "Tropical Garden", "Open Living", "Staff Quarters"],
            "lat": -8.6478,
            "lng": 115.1385,
            "min_price_usd": 280000,
            "max_price_usd": 720000,
            "total_units": 18,
            "available_units": 6,
        },
        {
            "name_en": "Ubud Sanctuary",
            "name_ru": "Убуд Санктуари",
            "slug": "ubud-sanctuary",
            "district": "ubud",
            "developer": "bali-villas",
            "status": ProjectStatus.CONSTRUCTION,
            "property_types": [PropertyType.VILLA],
            "ownership_type": OwnershipType.LEASEHOLD,
            "leasehold_years": 30,
            "completion_year": 2025,
            "completion_quarter": "Q3 2025",
            "description_en": "Eco-friendly villas surrounded by rice terraces and jungle.",
            "description_ru": "Экологичные виллы в окружении рисовых террас и джунглей.",
            "amenities": ["Infinity Pool", "Yoga Pavilion", "Organic Garden", "Meditation Space"],
            "lat": -8.5069,
            "lng": 115.2624,
            "min_price_usd": 320000,
            "max_price_usd": 550000,
            "total_units": 12,
            "available_units": 10,
            "construction_progress": 45,
        },
    ]
    
    all_projects = phuket_projects + pattaya_projects + bali_projects
    projects = {}
    total_units_created = 0
    
    for idx, data in enumerate(all_projects):
        district = districts[data.pop("district")]
        developer = developers[data.pop("developer")]
        
        # Create project
        project = Project(
            **data,
            district_id=district.id,
            developer_id=developer.id,
            cover_image_url=property_images[idx % len(property_images)],
            gallery=[property_images[(idx + i) % len(property_images)] for i in range(4)],
            visibility=Visibility.PUBLIC,
            is_active=True,
            is_featured=idx < 3,
            min_price_per_sqm_usd=data.get("min_price_usd", 150000) / 50,
        )
        session.add(project)
        await session.flush()
        projects[data["slug"]] = project
        
        # Create units for this project
        unit_configs = generate_unit_configs(project)
        for unit_data in unit_configs:
            unit = Unit(
                project_id=project.id,
                **unit_data
            )
            session.add(unit)
            total_units_created += 1
        
        await session.flush()
    
    await session.commit()
    print(f"  Created {len(projects)} projects and {total_units_created} units")
    return projects


def generate_unit_configs(project):
    """Generate realistic unit configurations for a project"""
    units = []
    
    base_price = project.min_price_usd or 150000
    price_range = (project.max_price_usd or 500000) - base_price
    total_units = project.total_units or 50
    available = project.available_units or int(total_units * 0.4)
    
    # Determine unit types based on property types
    property_types = project.property_types or [PropertyType.CONDO]
    
    if PropertyType.VILLA in property_types:
        # Villa configurations
        configs = [
            {"bedrooms": 2, "area_range": (120, 180), "count": int(total_units * 0.3)},
            {"bedrooms": 3, "area_range": (180, 280), "count": int(total_units * 0.5)},
            {"bedrooms": 4, "area_range": (280, 400), "count": int(total_units * 0.2)},
        ]
    else:
        # Condo configurations
        configs = [
            {"bedrooms": 0, "area_range": (28, 35), "count": int(total_units * 0.15)},  # Studio
            {"bedrooms": 1, "area_range": (35, 55), "count": int(total_units * 0.35)},
            {"bedrooms": 2, "area_range": (55, 90), "count": int(total_units * 0.35)},
            {"bedrooms": 3, "area_range": (90, 150), "count": int(total_units * 0.15)},
        ]
    
    view_types = ["Pool View", "Garden View", "Sea View", "Mountain View", "City View"]
    unit_num = 1
    available_count = 0
    
    for config in configs:
        for i in range(config["count"]):
            area = config["area_range"][0] + (config["area_range"][1] - config["area_range"][0]) * (i / max(config["count"], 1))
            floor = (i % 20) + 1 if PropertyType.CONDO in property_types else 1
            
            # Price based on area and floor
            price_multiplier = 1 + (floor - 1) * 0.02 + config["bedrooms"] * 0.15
            unit_price = base_price + (price_range * price_multiplier * (area / 100))
            
            # Determine status
            if available_count < available and i % 3 != 0:
                status = UnitStatus.AVAILABLE
                available_count += 1
            elif i % 5 == 0:
                status = UnitStatus.RESERVED
            else:
                status = UnitStatus.SOLD
            
            units.append({
                "unit_number": f"{floor:02d}{(i % 10) + 1:02d}" if PropertyType.CONDO in property_types else f"V{unit_num:03d}",
                "bedrooms": config["bedrooms"],
                "bathrooms": max(1, config["bedrooms"]),
                "area_sqm": round(area, 1),
                "floor": floor,
                "view_type": view_types[i % len(view_types)],
                "price_usd": round(unit_price, -3),
                "price_original": round(unit_price * 35.5, -3) if project.original_currency == "THB" else round(unit_price, -3),
                "original_currency": "THB" if "phuket" in project.slug or "pattaya" in project.slug else "USD",
                "price_per_sqm_usd": round(unit_price / area, 0),
                "status": status,
                "layout_type": f"{config['bedrooms']}BR-{chr(65 + (i % 3))}",
                "is_active": True,
            })
            unit_num += 1
    
    return units[:total_units]


async def seed_collections(session: AsyncSession, users: dict, projects: dict):
    """Seed sample collections"""
    print("Seeding collections...")
    
    agent = users.get("agent@propbase.com")
    if not agent:
        print("  No agent user found, skipping collections")
        return {}
    
    # Get some project and unit IDs
    result = await session.execute(
        text("SELECT id FROM units WHERE status = 'available' LIMIT 10")
    )
    unit_ids = [row[0] for row in result.fetchall()]
    
    collections_data = [
        {
            "name": "Beach Properties for Mr. Smith",
            "description": "Curated selection of beachfront properties",
            "is_public": True,
            "client_name": "John Smith",
            "client_email": "john.smith@example.com",
            "client_phone": "+1 555 123 4567",
        },
        {
            "name": "Investment Opportunities",
            "description": "High ROI properties for investors",
            "is_public": True,
            "client_name": "Investment Corp",
        },
        {
            "name": "Family Villas Selection",
            "description": "Spacious villas suitable for families",
            "is_public": False,
        },
    ]
    
    collections = {}
    for data in collections_data:
        import secrets
        collection = Collection(
            **data,
            user_id=agent.id,
            share_token=secrets.token_urlsafe(16),
        )
        session.add(collection)
        await session.flush()
        
        # Add some items to collections
        for i, unit_id in enumerate(unit_ids[:3]):
            item = CollectionItem(
                collection_id=collection.id,
                unit_id=unit_id,
                sort_order=i,
            )
            session.add(item)
        
        collections[data["name"]] = collection
    
    await session.commit()
    print(f"  Created {len(collections)} collections")
    return collections


async def main():
    """Main seed function"""
    print("=" * 50)
    print("PropBase Database Seeding")
    print("=" * 50)
    
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        try:
            # Seed in order (due to foreign key dependencies)
            countries, cities, districts = await seed_locations(session)
            developers = await seed_developers(session)
            users = await seed_users(session)
            projects = await seed_projects_and_units(session, districts, developers)
            collections = await seed_collections(session, users, projects)
            
            print("=" * 50)
            print("Seeding completed successfully!")
            print("=" * 50)
            print("\nDefault credentials:")
            print("  Admin: admin@propbase.com / admin123")
            print("  Agent: agent@propbase.com / agent123")
            print("  Agent RU: agent.ru@propbase.com / agent123")
            
        except Exception as e:
            print(f"Error seeding database: {e}")
            await session.rollback()
            raise
        finally:
            await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
