from sqlalchemy import select

from app.db import SessionLocal
from app.models import (
    Company,
    ComponentCatalog,
    DroneModel,
    Permission,
    Role,
    RolePermission,
)

MVP_COMPONENTS = [
    {"code": "TRIANGLE-BEAM", "name": "Triangle Beam", "category": "Frame", "minimum_stock": 5, "storage_location": "Rack A -> Shelf 1", "remarks": "Main arm frame beam"},
    {"code": "A-CONNECTOR", "name": "A Connector", "category": "Connectors", "minimum_stock": 10, "storage_location": "Rack A -> Shelf 2", "remarks": "Arm connector type A"},
    {"code": "B-CONNECTOR", "name": "B Connector", "category": "Connectors", "minimum_stock": 10, "storage_location": "Rack A -> Shelf 2", "remarks": "Arm connector type B"},
    {"code": "C-CONNECTOR", "name": "C Connector", "category": "Connectors", "minimum_stock": 10, "storage_location": "Rack A -> Shelf 2", "remarks": "Arm connector type C"},
    {"code": "AB-INSERTS", "name": "AB Inserts", "category": "Fasteners", "minimum_stock": 15, "storage_location": "Rack B -> Box 01", "remarks": "Rubber inserts for AB joints"},
    {"code": "HUB-PLATE", "name": "Hub Plate", "category": "Frame", "minimum_stock": 4, "storage_location": "Rack A -> Shelf 3", "remarks": "Central hub mounting plate"},
    {"code": "IBOLT", "name": "IBolt", "category": "Fasteners", "minimum_stock": 20, "storage_location": "Rack B -> Box 02", "remarks": "M6 Eye bolt"},
    {"code": "FREE-BOLT", "name": "Free Bolt", "category": "Fasteners", "minimum_stock": 20, "storage_location": "Rack B -> Box 02", "remarks": "Free swivel bolt"},
    {"code": "THREAD-BOLT", "name": "Thread Bolt", "category": "Fasteners", "minimum_stock": 20, "storage_location": "Rack B -> Box 03", "remarks": "Thread locking bolt"},
    {"code": "ARM-PIPE", "name": "Arm Pipe", "category": "Frame", "minimum_stock": 8, "storage_location": "Rack A -> Shelf 1", "remarks": "Carbon fiber arm pipe"},
    {"code": "HUB-STRIP", "name": "Hub Strip", "category": "Mechanical", "minimum_stock": 6, "storage_location": "Rack A -> Shelf 3", "remarks": "Hub locking strip"},
    {"code": "HUB-CONNECTOR", "name": "Hub Connector", "category": "Connectors", "minimum_stock": 8, "storage_location": "Rack A -> Shelf 2", "remarks": "Main central hub connector"},
    {"code": "TANK-CONNECTOR", "name": "Tank Connector", "category": "Tank / Spraying", "minimum_stock": 6, "storage_location": "Rack C -> Shelf 1", "remarks": "Spray tank quick connector"},
    {"code": "LANDING-GEAR", "name": "Landing Gear", "category": "Frame", "minimum_stock": 4, "storage_location": "Rack A -> Floor", "remarks": "Base landing gear assembly"},
    {"code": "BASE-RUBBER", "name": "Base Rubber", "category": "Mechanical", "minimum_stock": 12, "storage_location": "Rack B -> Box 04", "remarks": "Vibration dampening rubber"},
    {"code": "WATER-TANK", "name": "Water Tank", "category": "Tank / Spraying", "minimum_stock": 2, "storage_location": "Rack C -> Floor", "remarks": "10L spray payload tank"},
    {"code": "MOTORS", "name": "Motors", "category": "Propulsion", "minimum_stock": 10, "storage_location": "Rack B -> Shelf 1", "remarks": "High torque brushless motor"},
    {"code": "PROPELLERS", "name": "Propellers", "category": "Propulsion", "minimum_stock": 16, "storage_location": "Rack B -> Shelf 2", "remarks": "30 inch folding propellers"},
    {"code": "GPS-STAND", "name": "GPS Stand", "category": "Electronics", "minimum_stock": 5, "storage_location": "Rack B -> Box 05", "remarks": "Foldable GPS mast stand"},
    {"code": "ELECTRONICS-BOX", "name": "Electronics Box", "category": "Electronics", "minimum_stock": 4, "storage_location": "Rack B -> Shelf 3", "remarks": "Waterproof FC electronics housing"},
]

ROLE_DEFINITIONS = {
    "MANAGING_DIRECTOR": ("Managing Director", True),
    "PRODUCTION_MANAGER": ("Production Manager", True),
    "STORE_MANAGER": ("Store Manager", True),
    "SALES_MANAGER": ("Sales Manager", True),
    "TECHNICIAN": ("Technician", True),
    "AFTER_SALES_MANAGER": ("After-Sales Manager", True),
}

PERMISSIONS = {
    "members.read": "View company members",
    "members.manage": "Create and manage company members and roles",
    "attendance.check_in": "Check in and check out",
    "attendance.read_all": "View company attendance",
    "attendance.correct": "Correct attendance with reason",
    "drone.read": "View drones and production history",
    "drone.create": "Create drones and assign serial numbers",
    "assignment.manage": "Assign technicians to drones",
    "assignment.update_own": "Update production tasks assigned to you",
    "completion.confirm": "Confirm or reopen drone completion",
    "inventory.read": "View inventory and component history",
    "inventory.catalog.manage": "Create and manage the component catalog",
    "inventory.receive": "Receive stock into the store",
    "inventory.issue": "Approve and issue components",
    "inventory.substitute": "Approve component substitutions",
    "inventory.return_receive": "Receive returned components",
    "inventory.damage": "Classify or record damaged stock",
    "component.install": "Install, remove, or replace components on drones",
    "request.create": "Create component requests",
    "request.read_all": "View company component requests",
    "supplier.manage": "Manage suppliers and replenishment requests",
    "sales.manage": "Manage customers, quotations, orders, and sales",
    "mailbox.read": "View the shared GOAG mailbox",
    "mailbox.send": "Compose and send messages from the shared GOAG mailbox",
    "mailbox.manage": "Connect and manage the shared GOAG mailbox",
}

ROLE_PERMISSIONS = {
    "MANAGING_DIRECTOR": set(PERMISSIONS),
    "PRODUCTION_MANAGER": {"attendance.check_in", "attendance.read_all", "attendance.correct", "drone.read", "drone.create", "assignment.manage", "completion.confirm", "inventory.read", "component.install", "request.create"},
    "STORE_MANAGER": {"attendance.check_in", "attendance.read_all", "attendance.correct", "inventory.read", "inventory.catalog.manage", "inventory.receive", "inventory.issue", "inventory.substitute", "inventory.return_receive", "inventory.damage", "request.read_all", "supplier.manage", "mailbox.read", "mailbox.send"},
    "SALES_MANAGER": {"attendance.check_in", "attendance.read_all", "attendance.correct", "drone.read", "sales.manage"},
    "TECHNICIAN": {"attendance.check_in", "drone.read", "inventory.read", "request.create", "component.install", "assignment.update_own"},
    "AFTER_SALES_MANAGER": set(),
}


def seed() -> None:
    with SessionLocal.begin() as db:
        company = db.scalar(select(Company).where(Company.name == "GOAG"))
        if not company:
            company = Company(name="GOAG", timezone="Asia/Kolkata", status="active")
            db.add(company)
            db.flush()
        for code, description in PERMISSIONS.items():
            if not db.get(Permission, code):
                db.add(Permission(code=code, description=description))
        roles: dict[str, Role] = {}
        for code, (name, protected) in ROLE_DEFINITIONS.items():
            role = db.scalar(select(Role).where(Role.company_id == company.id, Role.code == code))
            if not role:
                role = Role(company_id=company.id, code=code, name=name, protected=protected)
                db.add(role)
                db.flush()
            roles[code] = role
            for permission_code in ROLE_PERMISSIONS[code]:
                exists = db.scalar(select(RolePermission).where(RolePermission.role_id == role.id, RolePermission.permission_code == permission_code))
                if not exists:
                    db.add(RolePermission(role_id=role.id, permission_code=permission_code))

        components: dict[str, ComponentCatalog] = {}
        for definition in MVP_COMPONENTS:
            component = db.scalar(
                select(ComponentCatalog).where(
                    ComponentCatalog.company_id == company.id,
                    ComponentCatalog.code == definition["code"],
                )
            )
            if not component:
                component = ComponentCatalog(company_id=company.id, **definition)
                db.add(component)
                db.flush()
            else:
                for field, value in definition.items():
                    setattr(component, field, value)
            components[definition["code"]] = component

        drone_model = db.scalar(
            select(DroneModel).where(DroneModel.company_id == company.id, DroneModel.code == "10X")
        )
        if not drone_model:
            drone_model = DroneModel(company_id=company.id, code="10X", name="10X", status="active")
            db.add(drone_model)
            db.flush()

        print(f"Seeded company {company.name} ({company.id}), {len(roles)} roles, {len(components)} components, and 10X drone model")


if __name__ == "__main__":
    seed()
