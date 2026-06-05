"""Multi-tenant organization system for SilverTrade AI.

Provides organization-scoped data isolation, role-based access control,
and subscription tier management. Every entity (users, API keys, strategies,
orders, positions) is scoped to an organization.

Usage:
    from database.organization_db import (
        Organization, OrganizationMember, Role, Permission,
        create_organization, get_organization, add_member,
        get_organization_tier, is_feature_allowed
    )
"""

import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer, String, Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, declarative_base

from database.db_config import get_db_engine

# ---------------------------------------------------------------------------
# Database Setup
# ---------------------------------------------------------------------------

engine = get_db_engine("DATABASE_URL", "sqlite:///db/silvertrade.db")
Base = declarative_base()


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class Organization(Base):
    """Multi-tenant organization — the top-level entity in the system.

    Every user, API key, strategy, and order belongs to an organization.
    Organizations have a subscription tier that controls feature access.
    """
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True)
    uuid = Column(String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    tier = Column(String(50), default="free", index=True)  # free, pro, enterprise
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Billing (Stripe/LemonSqueezy)
    stripe_customer_id = Column(String(255), unique=True, nullable=True)
    subscription_id = Column(String(255), unique=True, nullable=True)
    subscription_status = Column(String(50), default="inactive")  # active, past_due, canceled, unpaid, inactive
    
    # Feature limits
    max_users = Column(Integer, default=1)
    max_api_keys = Column(Integer, default=5)
    max_brokers = Column(Integer, default=1)
    max_strategies = Column(Integer, default=3)
    max_flows = Column(Integer, default=3)
    rate_limit_per_second = Column(Integer, default=10)
    
    # Relationships
    members = relationship("OrganizationMember", back_populates="organization", cascade="all, delete-orphan")
    roles = relationship("Role", back_populates="organization", cascade="all, delete-orphan")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.uuid,
            "name": self.name,
            "slug": self.slug,
            "tier": self.tier,
            "is_active": self.is_active,
            "subscription_status": self.subscription_status,
            "max_users": self.max_users,
            "max_api_keys": self.max_api_keys,
            "max_brokers": self.max_brokers,
            "max_strategies": self.max_strategies,
            "max_flows": self.max_flows,
            "rate_limit_per_second": self.rate_limit_per_second,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class OrganizationMember(Base):
    """Links a user to an organization with a specific role."""
    __tablename__ = "organization_members"
    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", name="uq_org_member"),
    )

    id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(255), nullable=False, index=True)
    role_name = Column(String(50), nullable=False, default="member")  # admin, trader, viewer
    invited_by = Column(String(255), nullable=True)
    invited_at = Column(DateTime, default=datetime.utcnow)
    joined_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    organization = relationship("Organization", back_populates="members")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "organization_id": self.organization.uuid if self.organization else None,
            "user_id": self.user_id,
            "role": self.role_name,
            "invited_by": self.invited_by,
            "invited_at": self.invited_at.isoformat() if self.invited_at else None,
            "joined_at": self.joined_at.isoformat() if self.joined_at else None,
            "is_active": self.is_active,
        }


class Role(Base):
    """Custom roles within an organization with associated permissions."""
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    is_system_role = Column(Boolean, default=False)  # System roles cannot be modified
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    organization = relationship("Organization", back_populates="roles")
    permissions = relationship("Permission", back_populates="role", cascade="all, delete-orphan")


class Permission(Base):
    """Granular permissions assigned to roles."""
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True)
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)
    resource = Column(String(100), nullable=False)  # e.g. "orders", "strategies", "api_keys"
    action = Column(String(50), nullable=False)     # e.g. "create", "read", "update", "delete", "*"
    
    # Relationships
    role = relationship("Role", back_populates="permissions")


# ---------------------------------------------------------------------------
# Default Roles & Permissions
# ---------------------------------------------------------------------------

# System roles that every organization gets
SYSTEM_ROLES = {
    "admin": {
        "description": "Full access to all organization resources and settings",
        "permissions": "*",  # Wildcard — all resources, all actions
    },
    "trader": {
        "description": "Can trade, view positions, use tools, and manage strategies",
        "permissions": {
            "orders": ["create", "read", "update", "delete"],
            "positions": ["read"],
            "strategies": ["create", "read", "update", "delete"],
            "tools": ["read"],
            "api_keys": ["read"],
        },
    },
    "viewer": {
        "description": "Read-only access to dashboards and positions",
        "permissions": {
            "positions": ["read"],
            "orders": ["read"],
            "strategies": ["read"],
            "tools": ["read"],
        },
    },
    "api": {
        "description": "Programmatic access via API keys only",
        "permissions": {
            "orders": ["create", "read"],
            "positions": ["read"],
            "funds": ["read"],
        },
    },
}


# ---------------------------------------------------------------------------
# Tier-Based Feature Toggles
# ---------------------------------------------------------------------------

TIER_CONFIGS = {
    "free": {
        "max_users": 1,
        "max_api_keys": 5,
        "max_brokers": 1,
        "max_strategies": 3,
        "max_flows": 3,
        "rate_limit_per_second": 10,
        "features": {
            "ai_strategies": False,
            "telegram_bot": False,
            "webhook_access": True,
            "historical_data": "30_days",
            "api_access": True,
            "support": "community",
        },
    },
    "pro": {
        "max_users": 5,
        "max_api_keys": 25,
        "max_brokers": 5,
        "max_strategies": 50,
        "max_flows": 20,
        "rate_limit_per_second": 50,
        "features": {
            "ai_strategies": True,
            "telegram_bot": True,
            "webhook_access": True,
            "historical_data": "5_years",
            "api_access": True,
            "support": "email",
        },
    },
    "enterprise": {
        "max_users": 1000,
        "max_api_keys": 500,
        "max_brokers": 50,
        "max_strategies": -1,  # unlimited
        "max_flows": -1,
        "rate_limit_per_second": 500,
        "features": {
            "ai_strategies": True,
            "telegram_bot": True,
            "webhook_access": True,
            "historical_data": "all",
            "api_access": True,
            "support": "priority",
            "white_label": True,
            "custom_sla": True,
            "dedicated_infrastructure": True,
        },
    },
}


# ---------------------------------------------------------------------------
# CRUD Operations
# ---------------------------------------------------------------------------

def create_organization(
    name: str,
    slug: str,
    tier: str = "free",
) -> Organization:
    """Create a new organization with default roles.

    Args:
        name: Display name for the organization.
        slug: URL-friendly unique identifier.
        tier: Subscription tier (free, pro, enterprise).

    Returns:
        The created Organization instance.
    """
    # Import session
    from sqlalchemy.orm import scoped_session, sessionmaker
    from database.db_config import get_db_engine
    
    engine = get_db_engine()
    Session = scoped_session(sessionmaker(bind=engine))
    session = Session()
    
    try:
        org = Organization(
            name=name,
            slug=slug,
            tier=tier,
        )
        
        # Set tier limits
        config = TIER_CONFIGS.get(tier, TIER_CONFIGS["free"])
        org.max_users = config["max_users"]
        org.max_api_keys = config["max_api_keys"]
        org.max_brokers = config["max_brokers"]
        org.max_strategies = config["max_strategies"]
        org.max_flows = config["max_flows"]
        org.rate_limit_per_second = config["rate_limit_per_second"]
        
        session.add(org)
        session.flush()  # Get the ID
        
        # Create system roles
        for role_name, role_config in SYSTEM_ROLES.items():
            role = Role(
                organization_id=org.id,
                name=role_name,
                description=role_config["description"],
                is_system_role=True,
            )
            session.add(role)
            session.flush()
            
            # Create permissions
            if role_config["permissions"] == "*":
                # Wildcard: create a single permission with "*" action
                perm = Permission(
                    role_id=role.id,
                    resource="*",
                    action="*",
                )
                session.add(perm)
            else:
                for resource, actions in role_config["permissions"].items():
                    for action in actions:
                        perm = Permission(
                            role_id=role.id,
                            resource=resource,
                            action=action,
                        )
                        session.add(perm)
        
        session.commit()
        return org
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_organization(org_id: str) -> Optional[Organization]:
    """Get an organization by its UUID.

    Args:
        org_id: The organization UUID string.

    Returns:
        Organization instance or None.
    """
    from sqlalchemy.orm import scoped_session, sessionmaker
    
    engine = get_db_engine()
    Session = scoped_session(sessionmaker(bind=engine))
    session = Session()
    
    try:
        return session.query(Organization).filter(
            Organization.uuid == org_id,
            Organization.is_active == True,
        ).first()
    finally:
        session.close()


def add_member(
    organization_id: str,
    user_id: str,
    role: str = "member",
    invited_by: Optional[str] = None,
) -> OrganizationMember:
    """Add a user to an organization.

    Args:
        organization_id: The organization UUID.
        user_id: The user's unique identifier.
        role: Role name (admin, trader, viewer).
        invited_by: User ID of the person who sent the invitation.

    Returns:
        The created OrganizationMember instance.
    """
    from sqlalchemy.orm import scoped_session, sessionmaker
    
    engine = get_db_engine()
    Session = scoped_session(sessionmaker(bind=engine))
    session = Session()
    
    try:
        org = session.query(Organization).filter(Organization.uuid == organization_id).first()
        if not org:
            raise ValueError(f"Organization {organization_id} not found")
        
        # Check member limit
        current_members = session.query(OrganizationMember).filter(
            OrganizationMember.organization_id == org.id,
            OrganizationMember.is_active == True,
        ).count()
        
        if current_members >= org.max_users:
            raise ValueError(
                f"Organization has reached its member limit ({org.max_users}). "
                f"Upgrade your plan to add more members."
            )
        
        member = OrganizationMember(
            organization_id=org.id,
            user_id=user_id,
            role_name=role,
            invited_by=invited_by,
            joined_at=datetime.utcnow(),
        )
        session.add(member)
        session.commit()
        return member
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_organization_tier(org_id: str) -> str:
    """Get the subscription tier of an organization.

    Args:
        org_id: The organization UUID.

    Returns:
        The tier name (free, pro, enterprise).
    """
    org = get_organization(org_id)
    if not org:
        return "free"
    return org.tier


def is_feature_allowed(org_id: str, feature: str) -> bool:
    """Check if a feature is allowed for the organization's tier.

    Args:
        org_id: The organization UUID.
        feature: The feature name to check (e.g. "ai_strategies", "telegram_bot").

    Returns:
        True if the feature is allowed, False otherwise.
    """
    org = get_organization(org_id)
    if not org:
        return False
    
    config = TIER_CONFIGS.get(org.tier, TIER_CONFIGS["free"])
    features = config.get("features", {})
    
    # Check if the feature is explicitly set
    if feature in features:
        return bool(features[feature])
    
    # Unknown features are not allowed by default
    return False


# ---------------------------------------------------------------------------
# Database Initialization
# ---------------------------------------------------------------------------

def init_db():
    """Create all organization-related tables."""
    Base.metadata.create_all(bind=engine)


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------

def delete_organization(org_id: str) -> bool:
    """Soft-delete an organization by marking it inactive.

    Args:
        org_id: The organization UUID.

    Returns:
        True if successful, False if organization not found.
    """
    from sqlalchemy.orm import scoped_session, sessionmaker
    
    engine = get_db_engine()
    Session = scoped_session(sessionmaker(bind=engine))
    session = Session()
    
    try:
        org = session.query(Organization).filter(Organization.uuid == org_id).first()
        if not org:
            return False
        
        org.is_active = False
        org.updated_at = datetime.utcnow()
        session.commit()
        return True
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
