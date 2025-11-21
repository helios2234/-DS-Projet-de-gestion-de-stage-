# 🎓 Système de Gestion des Stages - Cameroun

## 📋 Table des Matières
- [Vue d'ensemble](#vue-densemble)
- [Architecture](#architecture)
- [Prérequis](#prérequis)
- [Installation](#installation)
- [Configuration](#configuration)
- [Démarrage Rapide](#démarrage-rapide)
- [Services Disponibles](#services-disponibles)
- [Développement](#développement)
- [Tests](#tests)
- [Déploiement](#déploiement)
- [Documentation API](#documentation-api)
- [Contribution](#contribution)

---

## 🌟 Vue d'ensemble

Système complet de gestion des stages pour les étudiants au Cameroun. Cette plateforme permet de :

- **Étudiants** : Créer un profil, rechercher des offres, postuler, suivre leurs stages
- **Entreprises** : Publier des offres, gérer les candidatures, évaluer les stagiaires
- **Universités** : Superviser les stages, valider les rapports, générer les attestations

### Fonctionnalités Principales

✅ Gestion complète des profils (étudiants, entreprises, universités)  
✅ Publication et recherche d'offres de stage  
✅ Système de candidature avec workflow de validation  
✅ Suivi en temps réel des stages actifs  
✅ Dépôt et validation des rapports de stage  
✅ Génération automatique d'attestations et certificats  
✅ Système de notifications multi-canal (email, push, in-app)  
✅ Dashboard analytics pour toutes les parties prenantes  
✅ API RESTful documentée (OpenAPI/Swagger)  

---

## 🏗️ Architecture

### Stack Technologique

**Backend:**
- Python 3.11+ avec FastAPI
- PostgreSQL 15 (base de données principale)
- Redis (cache et sessions)
- RabbitMQ (message broker)
- MinIO (stockage S3-compatible)

**Frontend:**
- React 18 + TypeScript
- Redux Toolkit (state management)
- Material-UI (composants UI)
- Vite (build tool)

**Infrastructure:**
- Docker & Docker Compose
- Kubernetes (production)
- Kong/Traefik (API Gateway)
- Prometheus + Grafana (monitoring)
- ELK Stack (logging)

### Microservices

1. **Auth Service** (8001) - Authentification et autorisation
2. **Student Service** (8002) - Gestion des étudiants
3. **Enterprise Service** (8003) - Gestion des entreprises
4. **University Service** (8004) - Gestion des universités
5. **Offers Service** (8005) - Gestion des offres de stage
6. **Applications Service** (8006) - Gestion des candidatures
7. **Internships Service** (8007) - Suivi des stages
8. **Documents Service** (8008) - Stockage et génération de documents
9. **Notifications Service** (8009) - Notifications multi-canal

---

## 📦 Prérequis

### Développement Local

- **Docker** >= 20.10
- **Docker Compose** >= 2.0
- **Git** >= 2.30
- **Node.js** >= 18.0 (pour le frontend)
- **Python** >= 3.11 (optionnel, si développement sans Docker)

### Production

- **Kubernetes** >= 1.25
- **Helm** >= 3.10
- **kubectl** configuré
- Accès à un registry Docker (DockerHub, AWS ECR, etc.)

---

## 🚀 Installation

### 1. Cloner le Repository

```bash
git clone https://github.com/votre-org/internship-management-system.git
cd internship-management-system
```

### 2. Configuration des Variables d'Environnement

```bash
# Copier le fichier d'exemple
cp infrastructure/docker/.env.example infrastructure/docker/.env

# Éditer les variables
nano infrastructure/docker/.env
```

**Variables Critiques à Configurer:**

```env
# Database
POSTGRES_PASSWORD=your_secure_password_here

# JWT
JWT_SECRET_KEY=your_super_secret_jwt_key_minimum_32_chars

# Email
SMTP_HOST=smtp.gmail.com
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password
EMAIL_FROM=noreply@internship-system.cm

# MinIO
MINIO_ROOT_PASSWORD=secure_minio_password

# Redis
REDIS_PASSWORD=secure_redis_password

# RabbitMQ
RABBITMQ_PASS=secure_rabbitmq_password
```

### 3. Initialiser la Base de Données

```bash
# Créer les schémas et tables
docker-compose -f infrastructure/docker/docker-compose.yml up -d postgres
sleep 10  # Attendre que PostgreSQL démarre
docker exec -i internship-postgres psql -U postgres -d internship_db < scripts/init-db.sql
```

---

## ⚡ Démarrage Rapide

### Mode Développement (avec Docker Compose)

```bash
# Démarrer tous les services
cd infrastructure/docker
docker-compose up -d

# Vérifier les logs
docker-compose logs -f

# Accéder aux services:
# - Frontend: http://localhost:3000
# - API Gateway: http://localhost:8000
# - Auth Service: http://localhost:8001
# - Docs API: http://localhost:8001/docs
# - RabbitMQ Management: http://localhost:15672
# - MinIO Console: http://localhost:9001
# - Grafana: http://localhost:3001
```

### Mode Développement (sans Docker)

**Backend (exemple avec Auth Service):**

```bash
cd backend/services/auth-service

# Créer un environnement virtuel
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Installer les dépendances
pip install -r requirements.txt

# Configurer les variables
cp .env.example .env
nano .env

# Démarrer le service
uvicorn app.main:app --reload --port 8001
```

**Frontend:**

```bash
cd frontend

# Installer les dépendances
npm install

# Démarrer le serveur de développement
npm run dev
```

---

## 🔧 Configuration

### Configuration des Services

Chaque service a sa propre configuration dans `app/core/config.py`:

```python
class Settings(BaseSettings):
    API_V1_PREFIX: str = "/api/v1"
    DATABASE_URL: str
    REDIS_URL: str
    SECRET_KEY: str
    # ... autres configs
    
    class Config:
        env_file = ".env"
```

### Configuration du Gateway API

Le fichier `backend/api-gateway/kong.yml` définit les routes:

```yaml
services:
  - name: auth-service
    url: http://auth-service:8001
    routes:
      - name: auth-routes
        paths:
          - /api/v1/auth
```

### Configuration Redis (Cache)

Structure de cache par service:

- DB 0: Auth Service (sessions)
- DB 1: Student Service
- DB 2: Enterprise Service
- DB 3: University Service
- DB 4: Offers Service
- DB 5: Applications Service
- DB 6: Internships Service
- DB 7: Documents Service
- DB 8: Notifications Service

---

## 📚 Services Disponibles

### Auth Service (Port 8001)

**Endpoints:**
- `POST /api/v1/auth/register` - Inscription
- `POST /api/v1/auth/login` - Connexion
- `GET /api/v1/auth/me` - Profil utilisateur
- `POST /api/v1/auth/refresh` - Rafraîchir le token
- `POST /api/v1/auth/logout` - Déconnexion

**Documentation:** http://localhost:8001/docs

### Student Service (Port 8002)

**Endpoints:**
- `GET /api/v1/students` - Liste des étudiants
- `GET /api/v1/students/{id}` - Détails étudiant
- `PUT /api/v1/students/{id}` - Mise à jour profil
- `POST /api/v1/students/{id}/skills` - Ajouter compétences
- `GET /api/v1/students/{id}/applications` - Candidatures

**Documentation:** http://localhost:8002/docs

### Offers Service (Port 8005)

**Endpoints:**
- `GET /api/v1/offers` - Liste des offres
- `POST /api/v1/offers` - Créer une offre
- `GET /api/v1/offers/{id}` - Détails offre
- `GET /api/v1/offers/search` - Rechercher offres
- `GET /api/v1/offers/recommendations/{student_id}` - Recommandations

**Documentation:** http://localhost:8005/docs

*(Voir la documentation complète pour tous les services)*

---

## 💻 Développement

### Structure du Code

```
service-name/
├── app/
│   ├── api/          # Endpoints API
│   ├── core/         # Configuration et sécurité
│   ├── models/       # Modèles SQLAlchemy
│   ├── schemas/      # Schémas Pydantic
│   ├── services/     # Logique métier
│   ├── repositories/ # Accès données
│   └── main.py       # Point d'entrée
├── tests/
│   ├── unit/
│   └── integration/
└── requirements.txt
```

### Conventions de Code

**Python (Backend):**
- PEP 8 pour le style
- Type hints obligatoires
- Docstrings pour toutes les fonctions publiques
- Tests unitaires pour la logique métier
- Async/await pour les opérations I/O

**TypeScript (Frontend):**
- ESLint + Prettier
- Functional components avec hooks
- Redux Toolkit pour state management
- Material-UI pour l'UI

### Workflow Git

```bash
# Créer une branche feature
git checkout -b feature/nom-de-la-feature

# Faire vos modifications
git add .
git commit -m "feat: description de la feature"

# Pousser et créer une Pull Request
git push origin feature/nom-de-la-feature
```

**Convention de commits:**
- `feat:` - Nouvelle fonctionnalité
- `fix:` - Correction de bug
- `docs:` - Documentation
- `style:` - Formatage
- `refactor:` - Refactoring
- `test:` - Tests
- `chore:` - Maintenance

---

## 🧪 Tests

### Tests Backend

```bash
# Tous les tests
cd backend/services/auth-service
pytest

# Tests unitaires uniquement
pytest tests/unit/

# Tests avec couverture
pytest --cov=app --cov-report=html

# Tests d'intégration
pytest tests/integration/
```

### Tests Frontend

```bash
cd frontend

# Tests unitaires
npm test

# Tests e2e (Cypress)
npm run test:e2e

# Coverage
npm run test:coverage
```

### Tests de Charge

```bash
# Avec Locust
cd tests/load
locust -f locustfile.py --host=http://localhost:8000
```

---

## 🚢 Déploiement

### Déploiement Docker Compose (Staging)

```bash
# Build des images
docker-compose -f infrastructure/docker/docker-compose.prod.yml build

# Démarrer
docker-compose -f infrastructure/docker/docker-compose.prod.yml up -d

# Migrations
docker exec auth-service alembic upgrade head
```

### Déploiement Kubernetes (Production)

```bash
# Créer le namespace
kubectl create namespace internship-system

# Appliquer les configs
kubectl apply -f infrastructure/kubernetes/namespaces/
kubectl apply -f infrastructure/kubernetes/configmaps/
kubectl apply -f infrastructure/kubernetes/secrets/

# Déployer avec Helm
helm install internship-system infrastructure/kubernetes/helm/internship-system \
  --namespace internship-system \
  --values infrastructure/kubernetes/helm/internship-system/values.prod.yaml

# Vérifier le déploiement
kubectl get pods -n internship-system
kubectl get services -n internship-system
```

### CI/CD Pipeline

Le projet utilise GitHub Actions / GitLab CI:

1. **Test Stage**: Tests unitaires et d'intégration
2. **Build Stage**: Construction des images Docker
3. **Security Stage**: Scan de vulnérabilités (Trivy)
4. **Deploy Stage**: Déploiement automatique

---

## 📖 Documentation API

### Swagger/OpenAPI

Chaque service expose sa documentation interactive:

- Auth Service: http://localhost:8001/docs
- Student Service: http://localhost:8002/docs
- Offers Service: http://localhost:8005/docs
- (etc.)

### Postman Collection

Importer la collection: `docs/postman/internship-system.postman_collection.json`

### Exemples d'Utilisation

**Inscription d'un étudiant:**

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "etudiant@example.com",
    "password": "SecurePass123!",
    "role": "STUDENT"
  }'
```

**Connexion:**

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "etudiant@example.com",
    "password": "SecurePass123!"
  }'
```

**Rechercher des offres:**

```bash
curl -X GET "http://localhost:8000/api/v1/offers/search?q=developpement&city=Douala" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

## 🐛 Dépannage

### Problèmes Courants

**1. Les services ne démarrent pas:**
```bash
# Vérifier les logs
docker-compose logs service-name

# Redémarrer un service
docker-compose restart service-name
```

**2. Erreur de connexion à la base de données:**
```bash
# Vérifier que PostgreSQL est prêt
docker-compose ps postgres

# Tester la connexion
docker exec -it internship-postgres psql -U postgres -d internship_db
```

**3. Problème de permissions:**
```bash
# Réinitialiser les permissions
sudo chown -R $USER:$USER .
```

---

## 🤝 Contribution

Nous accueillons les contributions ! Voir [CONTRIBUTING.md](CONTRIBUTING.md) pour les guidelines.

### Process de Contribution

1. Fork le projet
2. Créer une branche feature (`git checkout -b feature/AmazingFeature`)
3. Commit vos changements (`git commit -m 'feat: Add AmazingFeature'`)
4. Push vers la branche (`git push origin feature/AmazingFeature`)
5. Ouvrir une Pull Request

---

## 📝 License

Ce projet est sous licence MIT. Voir [LICENSE](LICENSE) pour plus de détails.

---

## 👥 Équipe

- **Chef de Projet** - [Nom]
- **Lead Backend** - [Nom]
- **Lead Frontend** - [Nom]
- **DevOps** - [Nom]

---

## 📞 Contact

Pour toute question ou support:
- Email: support@internship-system.cm
- Documentation: https://docs.internship-system.cm
- Issues: https://github.com/votre-org/internship-management-system/issues

---

## 🗺️ Roadmap

### Phase 1 (En cours)
- ✅ Architecture microservices
- ✅ Services de base (Auth, Student, Enterprise)
- 🔄 Frontend React
- 🔄 Documentation API

### Phase 2 (Q1 2025)
- ⏳ Système de matching IA
- ⏳ Application mobile (React Native)
- ⏳ Analytics avancés
- ⏳ Intégrations tierces (LinkedIn, Google Calendar)

### Phase 3 (Q2 2025)
- ⏳ Blockchain pour certificats
- ⏳ Marketplace de compétences
- ⏳ Video interviews
- ⏳ Chatbot IA

---

Made with ❤️ for Cameroonian students