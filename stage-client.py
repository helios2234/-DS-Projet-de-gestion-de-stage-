# stage_client.py
"""
Client de gestion des stages pour les universités et entreprises au Cameroun
Permet la gestion complète des stages: création, suivi, rapports, évaluations
"""

import threading
import socket
import time
import json
import uuid
import os
import sqlite3
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field
import hashlib
import logging

from stage_protocols import (
    StageStatus, ReportType, UserRole, Region,
    CAMEROON_UNIVERSITIES, CAMEROON_MAJOR_CITIES
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class LocalStageRecord:
    """Enregistrement local d'un stage"""
    stage_id: str
    stage_title: str
    student_name: str
    company_name: str
    status: str
    progress: float
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class PendingReport:
    """Rapport en attente de soumission"""
    report_id: str
    stage_id: str
    title: str
    report_type: str
    file_path: str
    status: str = "EN_ATTENTE"

class LocalDataManager:
    """Gestionnaire de données locales pour le client"""
    
    def __init__(self, institution_id: str, storage_path: str = None):
        self.institution_id = institution_id
        self.storage_path = Path(storage_path) if storage_path else Path(f"./local_{institution_id}")
        self.storage_path.mkdir(exist_ok=True)
        
        self.reports_path = self.storage_path / "reports"
        self.documents_path = self.storage_path / "documents"
        self.cache_path = self.storage_path / "cache"
        
        self.reports_path.mkdir(exist_ok=True)
        self.documents_path.mkdir(exist_ok=True)
        self.cache_path.mkdir(exist_ok=True)
        
        self.db_path = self.storage_path / "local_data.db"
        self._init_database()
    
    def _init_database(self):
        """Initialiser la base de données locale"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Cache des stages
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stage_cache (
                stage_id TEXT PRIMARY KEY,
                stage_data TEXT NOT NULL,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Rapports en attente
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pending_reports (
                report_id TEXT PRIMARY KEY,
                stage_id TEXT NOT NULL,
                title TEXT NOT NULL,
                report_type TEXT NOT NULL,
                file_path TEXT,
                status TEXT DEFAULT 'EN_ATTENTE',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Notifications locales
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notifications (
                notification_id TEXT PRIMARY KEY,
                notification_type TEXT NOT NULL,
                message TEXT NOT NULL,
                is_read INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def cache_stage(self, stage_id: str, stage_data: dict):
        """Mettre en cache un stage"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO stage_cache (stage_id, stage_data, last_updated)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        ''', (stage_id, json.dumps(stage_data)))
        conn.commit()
        conn.close()
    
    def get_cached_stage(self, stage_id: str) -> Optional[dict]:
        """Récupérer un stage du cache"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT stage_data FROM stage_cache WHERE stage_id = ?', (stage_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return json.loads(row[0])
        return None
    
    def add_pending_report(self, report_data: dict) -> str:
        """Ajouter un rapport en attente"""
        report_id = str(uuid.uuid4())
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO pending_reports (report_id, stage_id, title, report_type, file_path)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            report_id,
            report_data['stage_id'],
            report_data['title'],
            report_data['report_type'],
            report_data.get('file_path', '')
        ))
        conn.commit()
        conn.close()
        return report_id
    
    def get_pending_reports(self) -> List[dict]:
        """Récupérer les rapports en attente"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM pending_reports WHERE status = 'EN_ATTENTE'")
        reports = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return reports
    
    def add_notification(self, notification_type: str, message: str):
        """Ajouter une notification"""
        notification_id = str(uuid.uuid4())
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO notifications (notification_id, notification_type, message)
            VALUES (?, ?, ?)
        ''', (notification_id, notification_type, message))
        conn.commit()
        conn.close()
    
    def get_unread_notifications(self) -> List[dict]:
        """Récupérer les notifications non lues"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM notifications WHERE is_read = 0 ORDER BY created_at DESC")
        notifications = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return notifications


class StageClient:
    """Client de gestion des stages"""
    
    def __init__(self, institution_id: str, institution_name: str, 
                 institution_type: str, region: str, city: str,
                 server_host: str = 'localhost', server_port: int = 8888):
        
        self.institution_id = institution_id
        self.institution_name = institution_name
        self.institution_type = institution_type
        self.region = region
        self.city = city
        
        self.server_host = server_host
        self.server_port = server_port
        self.server_socket: Optional[socket.socket] = None
        self.connected = False
        
        # Gestionnaire de données locales
        self.local_data = LocalDataManager(institution_id)
        
        # État
        self.running = False
        self.current_user_id = None
        self.current_user_role = None
        
        # Thread d'écoute
        self.listener_thread = None
    
    def connect_to_server(self) -> bool:
        """Se connecter au serveur"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.connect((self.server_host, self.server_port))
            
            # Enregistrer l'institution
            registration = {
                'type': 'register_institution',
                'institution_id': self.institution_id,
                'name': self.institution_name,
                'institution_type': self.institution_type,
                'region': self.region,
                'city': self.city,
                'contact_email': f"contact@{self.institution_id}.cm"
            }
            
            self.server_socket.send(json.dumps(registration).encode())
            response = json.loads(self.server_socket.recv(4096).decode())
            
            if response.get('status') == 'success':
                self.connected = True
                print(f"✅ Connecté au serveur de gestion des stages")
                
                # Démarrer l'écoute des messages
                self.listener_thread = threading.Thread(
                    target=self._message_listener,
                    daemon=True
                )
                self.listener_thread.start()
                
                return True
            else:
                print(f"❌ Échec de connexion: {response.get('message')}")
                return False
                
        except Exception as e:
            print(f"❌ Erreur de connexion: {e}")
            return False
    
    def _message_listener(self):
        """Écouter les messages du serveur"""
        while self.running and self.connected:
            try:
                self.server_socket.settimeout(5.0)
                data = self.server_socket.recv(8192)
                
                if not data:
                    self.connected = False
                    break
                
                message = json.loads(data.decode())
                self._handle_server_message(message)
                
            except socket.timeout:
                continue
            except Exception as e:
                logger.error(f"Erreur listener: {e}")
                break
    
    def _handle_server_message(self, message: dict):
        """Traiter les messages du serveur"""
        msg_type = message.get('type')
        
        if msg_type == 'heartbeat':
            response = {'type': 'heartbeat_response', 'timestamp': time.time()}
            self.server_socket.send(json.dumps(response).encode())
        elif msg_type == 'notification':
            self._handle_notification(message)
    
    def _handle_notification(self, notification: dict):
        """Gérer une notification"""
        self.local_data.add_notification(
            notification.get('notification_type', 'INFO'),
            notification.get('message', '')
        )
        print(f"\n🔔 {notification.get('message')}")
    
    def _send_request(self, request: dict) -> dict:
        """Envoyer une requête au serveur"""
        if not self.connected:
            return {'status': 'error', 'message': 'Non connecté au serveur'}
        
        try:
            self.server_socket.send(json.dumps(request).encode())
            self.server_socket.settimeout(30.0)
            response = self.server_socket.recv(65536)
            return json.loads(response.decode())
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    # ==================== GESTION DES STAGES ====================
    
    def create_stage(self, stage_data: dict) -> dict:
        """Créer un nouveau stage"""
        request = {
            'type': 'create_stage',
            'stage_data': stage_data
        }
        result = self._send_request(request)
        
        if result.get('success'):
            self.local_data.cache_stage(result['stage_id'], stage_data)
        
        return result
    
    def get_stage(self, stage_id: str) -> dict:
        """Récupérer les détails d'un stage"""
        request = {
            'type': 'get_stage',
            'stage_id': stage_id
        }
        result = self._send_request(request)
        
        if result.get('status') == 'success':
            self.local_data.cache_stage(stage_id, result['stage'])
        
        return result
    
    def list_stages(self, filters: dict = None, page: int = 1) -> dict:
        """Lister les stages"""
        request = {
            'type': 'list_stages',
            'filters': filters or {},
            'page': page,
            'page_size': 20
        }
        return self._send_request(request)
    
    def update_stage(self, stage_id: str, field: str, value: str) -> dict:
        """Mettre à jour un stage"""
        request = {
            'type': 'update_stage',
            'stage_id': stage_id,
            'field_name': field,
            'new_value': value,
            'updated_by': self.current_user_id or self.institution_id
        }
        return self._send_request(request)
    
    # ==================== GESTION DES ENCADREURS ====================
    
    def assign_supervisor(self, stage_id: str, supervisor_data: dict) -> dict:
        """Assigner un encadreur à un stage"""
        request = {
            'type': 'assign_supervisor',
            'stage_id': stage_id,
            'supervisor_data': supervisor_data
        }
        return self._send_request(request)
    
    # ==================== GESTION DES RAPPORTS ====================
    
    def submit_report(self, report_data: dict, file_path: str = None) -> dict:
        """Soumettre un rapport"""
        has_file = file_path and os.path.exists(file_path)
        
        request = {
            'type': 'submit_report',
            'report_data': report_data,
            'has_file': has_file
        }
        
        if has_file:
            request['file_size'] = os.path.getsize(file_path)
            request['filename'] = os.path.basename(file_path)
        
        # Envoyer la requête
        self.server_socket.send(json.dumps(request).encode())
        
        if has_file:
            # Attendre le signal de prêt
            response = json.loads(self.server_socket.recv(1024).decode())
            if response.get('status') == 'ready':
                # Envoyer le fichier
                with open(file_path, 'rb') as f:
                    while True:
                        chunk = f.read(8192)
                        if not chunk:
                            break
                        self.server_socket.send(chunk)
        
        # Recevoir la réponse finale
        self.server_socket.settimeout(30.0)
        final_response = json.loads(self.server_socket.recv(4096).decode())
        return final_response
    
    def list_reports(self, stage_id: str) -> dict:
        """Lister les rapports d'un stage"""
        request = {
            'type': 'list_reports',
            'stage_id': stage_id
        }
        return self._send_request(request)
    
    def review_report(self, report_id: str, score: float, feedback: str) -> dict:
        """Évaluer un rapport"""
        request = {
            'type': 'review_report',
            'report_id': report_id,
            'reviewer_id': self.current_user_id or self.institution_id,
            'score': score,
            'feedback': feedback
        }
        return self._send_request(request)
    
    # ==================== ÉVALUATIONS ====================
    
    def evaluate_stage(self, evaluation_data: dict) -> dict:
        """Évaluer un stage"""
        request = {
            'type': 'evaluate_stage',
            'evaluation_data': evaluation_data
        }
        return self._send_request(request)
    
    def get_evaluations(self, stage_id: str) -> dict:
        """Récupérer les évaluations d'un stage"""
        request = {
            'type': 'get_evaluations',
            'stage_id': stage_id
        }
        return self._send_request(request)
    
    # ==================== STATISTIQUES ====================
    
    def get_statistics(self, filters: dict = None) -> dict:
        """Obtenir les statistiques"""
        request = {
            'type': 'get_statistics',
            'filters': filters or {}
        }
        return self._send_request(request)
    
    def generate_certificate(self, stage_id: str) -> dict:
        """Générer une attestation de stage"""
        request = {
            'type': 'generate_certificate',
            'stage_id': stage_id
        }
        return self._send_request(request)
    
    # ==================== INTERFACE UTILISATEUR ====================
    
    def start_client(self):
        """Démarrer le client interactif"""
        self.running = True
        
        if not self.connect_to_server():
            print("❌ Impossible de se connecter au serveur")
            return
        
        self._show_welcome()
        self._command_loop()
    
    def _show_welcome(self):
        """Afficher le message de bienvenue"""
        print(f"\n{'='*70}")
        print(f"  SYSTÈME DE GESTION DES STAGES - {self.institution_name}")
        print(f"{'='*70}")
        print(f"📍 {self.city}, {self.region}")
        print(f"🏛️ Type: {self.institution_type}")
        print(f"{'='*70}")
        print("\nCOMMANDES DISPONIBLES:")
        print("  creer                    - Créer un nouveau stage")
        print("  liste [filtres]          - Lister les stages")
        print("  details <stage_id>       - Voir les détails d'un stage")
        print("  modifier <id> <champ>    - Modifier un stage")
        print("  encadreur <stage_id>     - Assigner un encadreur")
        print("  rapport <stage_id>       - Soumettre un rapport")
        print("  rapports <stage_id>      - Voir les rapports")
        print("  evaluer <stage_id>       - Évaluer un stage")
        print("  stats                    - Voir les statistiques")
        print("  attestation <stage_id>   - Générer une attestation")
        print("  notifications            - Voir les notifications")
        print("  aide                     - Afficher l'aide")
        print("  quit                     - Quitter")
        print(f"{'='*70}")
    
    def _command_loop(self):
        """Boucle principale de commandes"""
        while self.running:
            try:
                cmd_input = input(f"\n{self.institution_id}> ").strip()
                if not cmd_input:
                    continue
                
                parts = cmd_input.split()
                cmd = parts[0].lower()
                
                if cmd == 'quit':
                    break
                elif cmd == 'creer':
                    self._cmd_create_stage()
                elif cmd == 'liste':
                    self._cmd_list_stages(parts[1:])
                elif cmd == 'details' and len(parts) >= 2:
                    self._cmd_stage_details(parts[1])
                elif cmd == 'modifier' and len(parts) >= 3:
                    self._cmd_update_stage(parts[1], parts[2])
                elif cmd == 'encadreur' and len(parts) >= 2:
                    self._cmd_assign_supervisor(parts[1])
                elif cmd == 'rapport' and len(parts) >= 2:
                    self._cmd_submit_report(parts[1])
                elif cmd == 'rapports' and len(parts) >= 2:
                    self._cmd_list_reports(parts[1])
                elif cmd == 'evaluer' and len(parts) >= 2:
                    self._cmd_evaluate_stage(parts[1])
                elif cmd == 'stats':
                    self._cmd_statistics()
                elif cmd == 'attestation' and len(parts) >= 2:
                    self._cmd_generate_certificate(parts[1])
                elif cmd == 'notifications':
                    self._cmd_show_notifications()
                elif cmd == 'aide':
                    self._show_welcome()
                else:
                    print("❌ Commande inconnue. Tapez 'aide' pour la liste des commandes.")
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"❌ Erreur: {e}")
        
        self.disconnect()
    
    def _cmd_create_stage(self):
        """Commande: créer un stage"""
        print("\n📋 CRÉATION D'UN NOUVEAU STAGE")
        print("-" * 40)
        
        stage_data = {
            'student_id': input("ID Étudiant: ").strip() or str(uuid.uuid4())[:8],
            'student_name': input("Nom de l'étudiant: ").strip(),
            'student_email': input("Email: ").strip(),
            'student_phone': input("Téléphone: ").strip(),
            'university_id': self.institution_id if self.institution_type == 'UNIVERSITE' else input("ID Université: ").strip(),
            'university_name': self.institution_name if self.institution_type == 'UNIVERSITE' else input("Nom Université: ").strip(),
            'department': input("Département/Filière: ").strip(),
            'academic_level': input("Niveau (Licence/Master/etc): ").strip(),
            'company_id': input("ID Entreprise: ").strip() or str(uuid.uuid4())[:8],
            'company_name': input("Nom de l'entreprise: ").strip(),
            'company_address': input("Adresse entreprise: ").strip(),
            'company_city': input("Ville: ").strip(),
            'company_region': input("Région: ").strip(),
            'stage_title': input("Titre du stage: ").strip(),
            'stage_description': input("Description: ").strip(),
            'stage_type': input("Type (ACADEMIQUE/PROFESSIONNEL/PRE_EMPLOI): ").strip() or "ACADEMIQUE",
            'start_date': input("Date début (YYYY-MM-DD): ").strip(),
            'end_date': input("Date fin (YYYY-MM-DD): ").strip(),
            'created_by': self.institution_id
        }
        
        result = self.create_stage(stage_data)
        
        if result.get('success'):
            print(f"\n✅ Stage créé avec succès!")
            print(f"   ID: {result['stage_id']}")
        else:
            print(f"\n❌ Échec: {result.get('message')}")
    
    def _cmd_list_stages(self, args):
        """Commande: lister les stages"""
        filters = {}
        if args:
            if args[0] == 'encours':
                filters['status'] = 'EN_COURS'
            elif args[0] == 'termines':
                filters['status'] = 'TERMINE'
            elif args[0] == 'attente':
                filters['status'] = 'EN_ATTENTE'
        
        result = self.list_stages(filters)
        
        if result.get('status') == 'success':
            stages = result.get('stages', [])
            print(f"\n📋 STAGES ({result['total_count']} total)")
            print("=" * 80)
            
            for stage in stages:
                status_icon = {'EN_ATTENTE': '⏳', 'EN_COURS': '🔄', 'TERMINE': '✅', 'ANNULE': '❌'}.get(stage['status'], '❓')
                print(f"{status_icon} {stage['stage_title']}")
                print(f"   ID: {stage['stage_id'][:12]}...")
                print(f"   Étudiant: {stage['student_name']} | Entreprise: {stage['company_name']}")
                print(f"   Période: {stage['start_date']} → {stage['end_date']}")
                print(f"   Progrès: {stage.get('progress_percentage', 0):.1f}%")
                print()
        else:
            print(f"❌ Erreur: {result.get('message')}")
    
    def _cmd_stage_details(self, stage_id):
        """Commande: détails d'un stage"""
        result = self.get_stage(stage_id)
        
        if result.get('status') == 'success':
            stage = result['stage']
            print(f"\n📋 DÉTAILS DU STAGE")
            print("=" * 60)
            print(f"Titre: {stage['stage_title']}")
            print(f"ID: {stage['stage_id']}")
            print(f"Statut: {stage['status']}")
            print(f"\n👤 ÉTUDIANT:")
            print(f"   Nom: {stage['student_name']}")
            print(f"   Email: {stage.get('student_email', 'N/A')}")
            print(f"   Téléphone: {stage.get('student_phone', 'N/A')}")
            print(f"\n🎓 UNIVERSITÉ:")
            print(f"   {stage['university_name']}")
            print(f"   Département: {stage['department']}")
            print(f"\n🏢 ENTREPRISE:")
            print(f"   {stage['company_name']}")
            print(f"   {stage['company_city']}, {stage['company_region']}")
            print(f"\n📅 PÉRIODE:")
            print(f"   Début: {stage['start_date']}")
            print(f"   Fin: {stage['end_date']}")
            print(f"   Progrès: {stage.get('progress_percentage', 0):.1f}%")
            
            if stage.get('reports'):
                print(f"\n📄 RAPPORTS ({len(stage['reports'])}):")
                for r in stage['reports']:
                    print(f"   • {r['title']} ({r['report_type']}) - {r['status']}")
            
            if stage.get('evaluations'):
                print(f"\n📊 ÉVALUATIONS ({len(stage['evaluations'])}):")
                for e in stage['evaluations']:
                    print(f"   • Note: {e['final_score']:.2f}/20 - {e['grade']}")
        else:
            print(f"❌ Erreur: {result.get('message')}")
    
    def _cmd_update_stage(self, stage_id, field):
        """Commande: modifier un stage"""
        new_value = input(f"Nouvelle valeur pour '{field}': ").strip()
        result = self.update_stage(stage_id, field, new_value)
        
        if result.get('success'):
            print(f"✅ Stage mis à jour")
        else:
            print(f"❌ Erreur: {result.get('message')}")
    
    def _cmd_assign_supervisor(self, stage_id):
        """Commande: assigner un encadreur"""
        print("\n👨‍🏫 ASSIGNATION D'UN ENCADREUR")
        print("-" * 40)
        
        supervisor_data = {
            'supervisor_id': input("ID Encadreur: ").strip() or str(uuid.uuid4())[:8],
            'first_name': input("Prénom: ").strip(),
            'last_name': input("Nom: ").strip(),
            'email': input("Email: ").strip(),
            'phone': input("Téléphone: ").strip(),
            'supervisor_type': input("Type (ACADEMIQUE/ENTREPRISE): ").strip().upper(),
            'institution_id': self.institution_id,
            'department': input("Département/Service: ").strip(),
            'title': input("Titre (Dr/Pr/M./Mme): ").strip(),
            'assigned_by': self.institution_id
        }
        
        result = self.assign_supervisor(stage_id, supervisor_data)
        
        if result.get('success'):
            print(f"✅ Encadreur assigné avec succès")
        else:
            print(f"❌ Erreur: {result.get('message')}")
    
    def _cmd_submit_report(self, stage_id):
        """Commande: soumettre un rapport"""
        print("\n📄 SOUMISSION D'UN RAPPORT")
        print("-" * 40)
        
        report_data = {
            'stage_id': stage_id,
            'report_type': input("Type (HEBDOMADAIRE/MENSUEL/MI_PARCOURS/FINAL): ").strip().upper(),
            'title': input("Titre du rapport: ").strip(),
            'content': input("Résumé (optionnel): ").strip(),
            'week_number': int(input("Numéro de semaine (0 si N/A): ").strip() or "0"),
            'submitted_by': self.institution_id
        }
        
        file_path = input("Chemin du fichier (optionnel): ").strip()
        
        result = self.submit_report(report_data, file_path if file_path else None)
        
        if result.get('success'):
            print(f"✅ Rapport soumis avec succès")
            print(f"   ID: {result['report_id']}")
        else:
            print(f"❌ Erreur: {result.get('message')}")
    
    def _cmd_list_reports(self, stage_id):
        """Commande: lister les rapports"""
        result = self.list_reports(stage_id)
        
        if result.get('status') == 'success':
            reports = result.get('reports', [])
            print(f"\n📄 RAPPORTS ({len(reports)})")
            print("=" * 60)
            
            for r in reports:
                status_icon = {'SOUMIS': '📤', 'EVALUE': '✅', 'REJETE': '❌'}.get(r['status'], '❓')
                print(f"{status_icon} {r['title']}")
                print(f"   Type: {r['report_type']} | Date: {r['submission_date']}")
                if r.get('score'):
                    print(f"   Note: {r['score']}/20")
                if r.get('feedback'):
                    print(f"   Feedback: {r['feedback'][:50]}...")
                print()
        else:
            print(f"❌ Erreur: {result.get('message')}")
    
    def _cmd_evaluate_stage(self, stage_id):
        """Commande: évaluer un stage"""
        print("\n📊 ÉVALUATION DU STAGE")
        print("-" * 40)
        print("Notez chaque critère sur 20:")
        
        evaluation_data = {
            'stage_id': stage_id,
            'evaluator_id': self.current_user_id or self.institution_id,
            'evaluator_type': 'ACADEMIQUE' if self.institution_type == 'UNIVERSITE' else 'ENTREPRISE',
            'technical_skills_score': float(input("Compétences techniques: ").strip() or "0"),
            'soft_skills_score': float(input("Compétences relationnelles: ").strip() or "0"),
            'attendance_score': float(input("Assiduité: ").strip() or "0"),
            'initiative_score': float(input("Initiative: ").strip() or "0"),
            'report_quality_score': float(input("Qualité des rapports: ").strip() or "0"),
            'comments': input("Commentaires: ").strip(),
            'recommendation': input("Recommandation (EMBAUCHE/STAGE/FORMATION/AUCUNE): ").strip()
        }
        
        result = self.evaluate_stage(evaluation_data)
        
        if result.get('success'):
            print(f"\n✅ Évaluation enregistrée")
            print(f"   Note finale: {result['final_score']:.2f}/20")
            print(f"   Mention: {result['grade']}")
        else:
            print(f"❌ Erreur: {result.get('message')}")
    
    def _cmd_statistics(self):
        """Commande: afficher les statistiques"""
        result = self.get_statistics()
        
        if result.get('status') == 'success':
            stats = result['statistics']
            print(f"\n📊 STATISTIQUES")
            print("=" * 60)
            
            print("\n📈 Par statut:")
            for status, count in stats.get('by_status', {}).items():
                print(f"   {status}: {count}")
            
            print("\n🗺️ Par région:")
            for region, count in stats.get('by_region', {}).items():
                print(f"   {region}: {count}")
            
            print("\n🎓 Par université:")
            for univ, count in stats.get('by_university', {}).items():
                print(f"   {univ}: {count}")
            
            print(f"\n📊 Moyenne générale: {stats.get('average_score', 0):.2f}/20")
            print(f"📄 Total rapports: {stats.get('total_reports', 0)}")
            print(f"🔄 Stages actifs: {stats.get('active_stages', 0)}")
            
            if stats.get('server_stats'):
                ss = stats['server_stats']
                print(f"\n🖥️ Statistiques serveur:")
                print(f"   Institutions connectées: {ss.get('connected_institutions', 0)}")
                print(f"   Total stages créés: {ss.get('total_stages_created', 0)}")
        else:
            print(f"❌ Erreur: {result.get('message')}")
    
    def _cmd_generate_certificate(self, stage_id):
        """Commande: générer une attestation"""
        result = self.generate_certificate(stage_id)
        
        if result.get('success'):
            cert = result['certificate']
            print(f"\n📜 ATTESTATION DE STAGE GÉNÉRÉE")
            print("=" * 60)
            print(f"N° Attestation: {cert['certificate_id']}")
            print(f"\nCertifie que:")
            print(f"   {cert['student_name']}")
            print(f"   Étudiant(e) à {cert['university_name']}")
            print(f"\nA effectué un stage intitulé:")
            print(f"   \"{cert['stage_title']}\"")
            print(f"\nAu sein de:")
            print(f"   {cert['company_name']}")
            print(f"\nPériode: {cert['start_date']} au {cert['end_date']}")
            print(f"Mention obtenue: {cert['final_grade']}")
            print(f"\nGénérée le: {cert['generated_at']}")
        else:
            print(f"❌ Erreur: {result.get('message')}")
    
    def _cmd_show_notifications(self):
        """Commande: afficher les notifications"""
        notifications = self.local_data.get_unread_notifications()
        
        if notifications:
            print(f"\n🔔 NOTIFICATIONS ({len(notifications)})")
            print("=" * 60)
            for n in notifications:
                print(f"📌 [{n['notification_type']}] {n['message']}")
                print(f"   {n['created_at']}")
                print()
        else:
            print("\n✅ Aucune nouvelle notification")
    
    def disconnect(self):
        """Se déconnecter du serveur"""
        print("\n🔌 Déconnexion...")
        self.running = False
        
        if self.connected and self.server_socket:
            try:
                disconnect_msg = {
                    'type': 'disconnect',
                    'institution_id': self.institution_id
                }
                self.server_socket.send(json.dumps(disconnect_msg).encode())
            except:
                pass
        
        self.connected = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        
        print("✅ Déconnecté")


def main():
    """Fonction principale"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python stage_client.py <institution_id> [server_host] [server_port]")
        print("\nExemples:")
        print("  python stage_client.py univ_uy1 localhost 8888")
        print("  python stage_client.py ent_orange localhost 8888")
        print("\nTypes d'institutions:")
        print("  univ_* : Université")
        print("  ent_*  : Entreprise")
        print("  min_*  : Ministère")
        print("  coord_* : Coordinateur")
        return
    
    institution_id = sys.argv[1]
    server_host = sys.argv[2] if len(sys.argv) > 2 else "localhost"
    server_port = int(sys.argv[3]) if len(sys.argv) > 3 else 8888
    
    # Déterminer le type d'institution
    if institution_id.startswith('univ_'):
        inst_type = "UNIVERSITE"
        inst_name = f"Université {institution_id[5:].upper()}"
    elif institution_id.startswith('ent_'):
        inst_type = "ENTREPRISE"
        inst_name = f"Entreprise {institution_id[4:].upper()}"
    elif institution_id.startswith('min_'):
        inst_type = "MINISTERE"
        inst_name = f"Ministère {institution_id[4:].upper()}"
    else:
        inst_type = "COORDINATEUR"
        inst_name = f"Coordinateur {institution_id}"
    
    # Demander les informations supplémentaires
    print(f"\n🏛️ Configuration de {inst_name}")
    region = input("Région (ex: Centre, Littoral): ").strip() or "Centre"
    city = input("Ville (ex: Yaoundé, Douala): ").strip() or "Yaoundé"
    
    # Créer et démarrer le client
    client = StageClient(
        institution_id=institution_id,
        institution_name=inst_name,
        institution_type=inst_type,
        region=region,
        city=city,
        server_host=server_host,
        server_port=server_port
    )
    
    try:
        client.start_client()
    except KeyboardInterrupt:
        pass
    finally:
        client.disconnect()


if __name__ == "__main__":
    main()