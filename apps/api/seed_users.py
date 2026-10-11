"""Create the standard development users and attach their approved GOAG roles.

This seeds application users only. It does not create passwords or Supabase Auth
accounts. Each seeded user remains invited until its email is created in Supabase
Auth. The first authenticated request with that email links the Auth subject.
"""

from sqlalchemy import select

from app.db import SessionLocal
from app.models import Company, Membership, MembershipRole, Role, User
from seed import seed

SEED_USERS = (
    {"email": "md@goag.example", "display_name": "Development Managing Director", "role": "MANAGING_DIRECTOR"},
    {"email": "production.manager@goag.example", "display_name": "Development Production Manager", "role": "PRODUCTION_MANAGER"},
    {"email": "store.manager@goag.example", "display_name": "Development Store Manager", "role": "STORE_MANAGER"},
    {"email": "sales.manager@goag.example", "display_name": "Development Sales Manager", "role": "SALES_MANAGER"},
    {"email": "technician@goag.example", "display_name": "Development Technician", "role": "TECHNICIAN"},
    {"email": "after.sales@goag.example", "display_name": "Development After-Sales Manager", "role": "AFTER_SALES_MANAGER"},
)


def seed_users() -> None:
    seed()
    with SessionLocal.begin() as db:
        company = db.scalar(select(Company).where(Company.name == "GOAG"))
        if not company:
            raise RuntimeError("GOAG company was not found after running the base seed")

        created = 0
        linked = 0
        for definition in SEED_USERS:
            user = db.scalar(select(User).where(User.email == definition["email"]))
            if not user:
                user = User(
                    email=definition["email"],
                    display_name=definition["display_name"],
                    status="invited",
                )
                db.add(user)
                db.flush()
                created += 1

            membership = db.scalar(
                select(Membership).where(
                    Membership.company_id == company.id,
                    Membership.user_id == user.id,
                )
            )
            if not membership:
                membership = Membership(company_id=company.id, user_id=user.id, status="active")
                db.add(membership)
                db.flush()

            role = db.scalar(
                select(Role).where(
                    Role.company_id == company.id,
                    Role.code == definition["role"],
                )
            )
            if not role:
                raise RuntimeError(f"Role {definition['role']} was not found after running the base seed")

            membership_role = db.scalar(
                select(MembershipRole).where(
                    MembershipRole.membership_id == membership.id,
                    MembershipRole.role_id == role.id,
                )
            )
            if not membership_role:
                db.add(MembershipRole(membership_id=membership.id, role_id=role.id))
                linked += 1

    print(f"Seeded {len(SEED_USERS)} development users ({created} users created, {linked} role links added).")


if __name__ == "__main__":
    seed_users()
