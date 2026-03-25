"""
Database Seed Script
Creates sample user and checks database connectivity
"""
import sys
from database import SessionLocal, init_db
from models import User
from auth import get_password_hash


def seed_database():
    """Seed database with initial data."""
    print("=" * 60)
    print("Database Seed Script")
    print("=" * 60)
    
    # Initialize database
    print("\n1. Initializing database...")
    init_db()
    
    # Create session
    db = SessionLocal()
    
    try:
        # Check if demo user exists
        demo_user = db.query(User).filter(User.email == "demo@argo.com").first()
        
        if demo_user:
            print("\n✓ Demo user already exists")
        else:
            print("\n2. Creating demo user...")
            demo_user = User(
                name="Demo User",
                email="demo@argo.com",
                password_hash=get_password_hash("demo123")
            )
            db.add(demo_user)
            db.commit()
            print("✓ Demo user created successfully")
            print("  Email: demo@argo.com")
            print("  Password: demo123")
        
        # Check data counts
        from models import ArgoProfile, ArgoDocument
        
        profile_count = db.query(ArgoProfile).count()
        doc_count = db.query(ArgoDocument).count()
        
        print(f"\n3. Database statistics:")
        print(f"  Profiles: {profile_count}")
        print(f"  Documents: {doc_count}")
        
        if profile_count == 0:
            print("\n⚠ No ARGO data found. Run 'python ingest.py' to load data.")
        
        print("\n" + "=" * 60)
        print("Seed Complete!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
