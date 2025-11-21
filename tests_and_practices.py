# ============================================
# auth-service/tests/conftest.py
# ============================================
import pytest
import asyncio
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from httpx import AsyncClient

from app.main import app
from app.db.database import Base
from app.db.session import get_db
from app.core.config import settings

# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create test database session"""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        yield session
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()

@pytest.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test client"""
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()

# ============================================
# auth-service/tests/unit/test_security.py
# ============================================
import pytest
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token
)
from jose import jwt
from app.core.config import settings

def test_password_hashing():
    """Test password hashing and verification"""
    password = "testpassword123"
    hashed = get_password_hash(password)
    
    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("wrongpassword", hashed) is False

def test_access_token_creation():
    """Test JWT access token creation"""
    data = {"sub": "test-user-id", "role": "STUDENT"}
    token = create_access_token(data)
    
    assert token is not None
    
    # Decode token
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    assert payload["sub"] == "test-user-id"
    assert payload["type"] == "access"

def test_refresh_token_creation():
    """Test JWT refresh token creation"""
    data = {"sub": "test-user-id"}
    token = create_refresh_token(data)
    
    assert token is not None
    
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    assert payload["sub"] == "test-user-id"
    assert payload["type"] == "refresh"

# ============================================
# auth-service/tests/integration/test_auth_endpoints.py
# ============================================
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.core.security import get_password_hash

@pytest.mark.asyncio
async def test_register_user(client: AsyncClient):
    """Test user registration endpoint"""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "password": "testpassword123",
            "role": "STUDENT"
        }
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["role"] == "STUDENT"
    assert "id" in data

@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient, db_session: AsyncSession):
    """Test registration with duplicate email"""
    # Create existing user
    user = User(
        email="existing@example.com",
        password_hash=get_password_hash("password123"),
        role=UserRole.STUDENT
    )
    db_session.add(user)
    await db_session.commit()
    
    # Try to register with same email
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "existing@example.com",
            "password": "testpassword123",
            "role": "STUDENT"
        }
    )
    
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"]

@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, db_session: AsyncSession):
    """Test successful login"""
    # Create user
    user = User(
        email="login@example.com",
        password_hash=get_password_hash("password123"),
        role=UserRole.STUDENT,
        is_active=True
    )
    db_session.add(user)
    await db_session.commit()
    
    # Login
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "login@example.com",
            "password": "password123"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "login@example.com"

@pytest.mark.asyncio
async def test_login_invalid_credentials(client: AsyncClient):
    """Test login with invalid credentials"""
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "nonexistent@example.com",
            "password": "wrongpassword"
        }
    )
    
    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["detail"]

@pytest.mark.asyncio
async def test_get_current_user(client: AsyncClient, db_session: AsyncSession):
    """Test getting current user info"""
    # Create user and get token
    user = User(
        email="current@example.com",
        password_hash=get_password_hash("password123"),
        role=UserRole.STUDENT,
        is_active=True
    )
    db_session.add(user)
    await db_session.commit()
    
    # Login to get token
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "current@example.com",
            "password": "password123"
        }
    )
    token = login_response.json()["access_token"]
    
    # Get current user
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "current@example.com"

# ============================================
# BONNES PRATIQUES DE SÉCURITÉ
# ============================================

"""
SÉCURITÉ - BEST PRACTICES

1. AUTHENTIFICATION
   ✓ Utiliser OAuth2 avec JWT
   ✓ Tokens d'accès de courte durée (15 min)
   ✓ Refresh tokens avec rotation
   ✓ Hash des mots de passe avec bcrypt
   ✓ Validation stricte des entrées (Pydantic)

2. AUTORISATION
   ✓ RBAC (Role-Based Access Control)
   ✓ Vérifier les permissions sur chaque endpoint
   ✓ Principe du moindre privilège
   ✓ Séparer les contextes (étudiant, entreprise, université)

3. API SECURITY
   ✓ Rate limiting (Redis)
   ✓ CORS configuré strictement
   ✓ HTTPS obligatoire en production
   ✓ Validation des entrées (Pydantic models)
   ✓ Protection CSRF pour les formulaires
   ✓ Headers de sécurité (helmet.js équivalent)

4. BASE DE DONNÉES
   ✓ Utiliser ORM (SQLAlchemy) contre SQL injection
   ✓ Prepared statements uniquement
   ✓ Encryption at rest
   ✓ Séparation des schémas par service
   ✓ Audit logs pour actions sensibles
   ✓ Backup réguliers automatisés

5. DONNÉES SENSIBLES
   ✓ Ne jamais logger les mots de passe
   ✓ Masquer les PII dans les logs
   ✓ Chiffrer les données sensibles
   ✓ Utiliser des variables d'environnement
   ✓ Rotation des secrets régulière

6. COMMUNICATION INTER-SERVICES
   ✓ mTLS entre microservices
   ✓ Service mesh (Istio) en production
   ✓ Validation des tokens entre services
   ✓ Network policies Kubernetes

7. STOCKAGE DE FICHIERS
   ✓ Scanner antivirus sur upload
   ✓ Vérifier les types MIME
   ✓ Limiter la taille des fichiers
   ✓ Isoler le stockage (MinIO/S3)
   ✓ Signed URLs pour l'accès
   ✓ CDN pour les fichiers publics

8. MONITORING ET LOGGING
   ✓ Centraliser les logs (ELK)
   ✓ Alertes sur comportements anormaux
   ✓ Audit trail complet
   ✓ SIEM pour analyse de sécurité
   ✓ Metrics de sécurité (Prometheus)

9. COMPLIANCE
   ✓ RGPD/GDPR compliance
   ✓ Consentement utilisateur
   ✓ Droit à l'oubli
   ✓ Export des données personnelles
   ✓ Politique de confidentialité claire

10. TESTS DE SÉCURITÉ
    ✓ Tests d'injection (SQL, XSS, etc.)
    ✓ Scan de vulnérabilités (Trivy, OWASP ZAP)
    ✓ Tests de penetration réguliers
    ✓ Dependency scanning
    ✓ Security code review
"""

# ============================================
# EXEMPLE: Middleware de sécurité
# ============================================
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import time
from typing import Dict
from collections import defaultdict

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware using Redis"""
    
    def __init__(self, app, redis_client, requests_per_minute: int = 60):
        super().__init__(app)
        self.redis = redis_client
        self.requests_per_minute = requests_per_minute
    
    async def dispatch(self, request: Request, call_next):
        # Get client IP
        client_ip = request.client.host
        
        # Create Redis key
        key = f"rate_limit:{client_ip}"
        
        # Check rate limit
        current = await self.redis.get(key)
        
        if current and int(current) >= self.requests_per_minute:
            raise HTTPException(
                status_code=429,
                detail="Too many requests. Please try again later."
            )
        
        # Increment counter
        pipe = self.redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, 60)  # 60 seconds
        await pipe.execute()
        
        response = await call_next(request)
        return response

# ============================================
# EXEMPLE: Validation stricte des entrées
# ============================================
from pydantic import BaseModel, Field, validator
import re

class SecureUserInput(BaseModel):
    """Secure user input validation"""
    
    email: str = Field(..., max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    
    @validator('email')
    def validate_email(cls, v):
        # Email validation
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, v):
            raise ValueError('Invalid email format')
        return v.lower()
    
    @validator('password')
    def validate_password(cls, v):
        # Password strength validation
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain at least one special character')
        return v

# ============================================
# EXEMPLE: Audit logging
# ============================================
from datetime import datetime
import json

class AuditLogger:
    """Audit logging for sensitive operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def log_action(
        self,
        user_id: str,
        action: str,
        resource_type: str,
        resource_id: str,
        details: dict = None,
        ip_address: str = None
    ):
        """Log an audit event"""
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "details": details,
            "ip_address": ip_address
        }
        
        # Log to database
        # Implementation depends on audit_logs table structure
        
        # Also log to external system (ELK)
        logger.info(f"AUDIT: {json.dumps(audit_entry)}")

# ============================================
# CHECKLIST DÉPLOIEMENT PRODUCTION
# ============================================
"""
PRÉ-DÉPLOIEMENT:
□ Tous les tests passent (unit, integration, e2e)
□ Code review complété
□ Scan de sécurité effectué (Trivy, OWASP)
□ Variables d'environnement configurées
□ Secrets stockés dans vault (HashiCorp Vault, AWS Secrets Manager)
□ SSL/TLS certificates configurés
□ Backup strategy en place
□ Disaster recovery plan documenté
□ Monitoring et alertes configurés
□ Documentation API à jour
□ Load testing effectué
□ Security headers configurés
□ Rate limiting activé
□ CORS policies configurées
□ Database migrations testées
□ Rollback plan défini
□ Health checks configurés
□ Log aggregation configurée
□ Metrics collection activée
□ Tracing configuré (Jaeger)
□ Auto-scaling configuré (HPA)
□ Network policies définies
□ RBAC Kubernetes configuré
"""