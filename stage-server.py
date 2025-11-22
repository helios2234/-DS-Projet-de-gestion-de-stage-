# stage_server.py
"""
Serveur principal de gestion des stages au Cameroun
Gère les connexions des universités, entreprises et coordinateurs
"""

import threading
import socket
import time
import uuid
import queue
import json
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum, auto
import hashlib
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ConnectionStatus(Enum):
    CONNECTED = "CONNECTE"
    DISCONNECTED = "DECONNECTE"
    PENDING = "EN_ATTENTE"

class InstitutionType(Enum):
    UNIVERSITY = "UNIVERSITE"
    COMPANY = "ENTREPRISE"
    MINISTRY = "MINISTERE"
    COORDINATOR = "COORDINATEUR"

@dataclass
class ConnectedInstitution:
    """Représente une institution connectée au serveur"""
    institution_id: str
    name: str
    institution_type: InstitutionType
    region: str
    city: str
    contact_email: str
    status: ConnectionStatus = ConnectionStatus.PENDING
    connected_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    active_stages: int = 0

class StageServerManager:
    """Gestionnaire du serveur de stages"""
    
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.running = False
        self.server_socket = None
        
        # Gestion des connexions
        self.connected_institutions: Dict[str, ConnectedInstitution] = {}
        self.institution_sockets: Dict[str, socket.socket] = {}
        self.connection_lock = threading.RLock()
        
        # Files de messages
        self.message_queue = queue.Queue()
        self.notification_queue = queue.Queue()
        
        # Statistiques
        self.total_stages_created = 0
        self.total_reports_submitted = 0
        self.total_evaluations = 0
        
        # Service de stages
        from enhanced_stage_service import StageManager, EnhancedStageService
        self.stage_manager = StageManager("central_server")
        self.stage_service = EnhancedStageService(self)
        
    def start_server(self):
        """Démarrer le serveur"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(20)
            self.running = True
            
            print(f"\n{'='*70}")
            print("  SERVEUR DE GESTION DES STAGES - CAMEROUN")
            print(f"{'='*70}")
            print(f"🖥️  Serveur démarré sur {self.host}:{self.port}")
            print("📡 En attente de connexions des institutions...")
            print(f"{'='*70}")
            
            # Démarrer les threads de service
            monitor_thread = threading.Thread(target=self._status_monitor, daemon=True)
            monitor_thread.start()
            
            health_thread = threading.Thread(target=self._connection_health_monitor, daemon=True)
            health_thread.start()
            
            notification_thread = threading.Thread(target=self._notification_dispatcher, daemon=True)
            notification_thread.start()
            
            # Accepter les connexions
            while self.running:
                try:
                    client_socket, address = self.server_socket.accept()
                    print(f"🔌 Nouvelle connexion de {address}")
                    
                    conn_thread = threading.Thread(
                        target=self._handle_institution_connection,
                        args=(client_socket, address),
                        daemon=True
                    )
                    conn_thread.start()
                    
                except Exception as e:
                    if self.running:
                        print(f"❌ Erreur de connexion: {e}")
                        
        except Exception as e:
            print(f"❌ Échec du démarrage du serveur: {e}")
    
    def _handle_institution_connection(self, client_socket: socket.socket, address):
        """Gérer la connexion d'une institution"""
        institution_id = None
        try:
            while self.running:
                try:
                    client_socket.settimeout(60.0)
                    data = client_socket.recv(16384)
                    
                    if not data:
                        print(f"🔌 Connexion fermée: {address}")
                        break
                        
                    message = json.loads(data.decode())
                    response = self._process_message(message, client_socket)
                    
                    if message.get('type') == 'register_institution':
                        institution_id = message.get('institution_id')
                    
                    if response and response.get('send_response', True):
                        client_socket.send(json.dumps(response).encode())
                        
                except socket.timeout:
                    try:
                        heartbeat = {'type': 'heartbeat', 'timestamp': time.time()}
                        client_socket.send(json.dumps(heartbeat).encode())
                    except:
                        print(f"💔 Heartbeat échoué pour {address}")
                        break
                        
                except json.JSONDecodeError:
                    print(f"⚠️ JSON invalide de {address}")
                    continue
                    
                except Exception as e:
                    print(f"❌ Erreur de traitement {address}: {e}")
                    break
                    
        except Exception as e:
            print(f"❌ Erreur connexion {address}: {e}")
        finally:
            if institution_id:
                self._cleanup_disconnected_institution(institution_id)
            client_socket.close()
    
    def _process_message(self, message: dict, client_socket: socket.socket) -> dict:
        """Traiter les messages reçus"""
        msg_type = message.get('type')
        
        # Messages de connexion
        if msg_type == 'register_institution':
            return self._register_institution(message, client_socket)
        elif msg_type == 'disconnect':
            return self._handle_disconnect(message)
        elif msg_type == 'heartbeat_response':
            return {'status': 'success', 'send_response': False}
        
        # Messages de gestion des stages
        elif msg_type == 'create_stage':
            return self._handle_create_stage(message)
        elif msg_type == 'update_stage':
            return self._handle_update_stage(message)
        elif msg_type == 'get_stage':
            return self._handle_get_stage(message)
        elif msg_type == 'list_stages':
            return self._handle_list_stages(message)
        elif msg_type == 'delete_stage':
            return self._handle_delete_stage(message)
        
        # Messages d'encadrement
        elif msg_type == 'assign_supervisor':
            return self._handle_assign_supervisor(message)
        elif msg_type == 'list_supervisors':
            return self._handle_list_supervisors(message)
        
        # Messages de rapports
        elif msg_type == 'submit_report':
            return self._handle_submit_report(message, client_socket)
        elif msg_type == 'list_reports':
            return self._handle_list_reports(message)
        elif msg_type == 'review_report':
            return self._handle_review_report(message)
        
        # Messages d'évaluation
        elif msg_type == 'evaluate_stage':
            return self._handle_evaluate_stage(message)
        elif msg_type == 'get_evaluations':
            return self._handle_get_evaluations(message)
        
        # Messages de statistiques
        elif msg_type == 'get_statistics':
            return self._handle_get_statistics(message)
        elif msg_type == 'generate_certificate':
            return self._handle_generate_certificate(message)
        
        else:
            return {'status': 'error', 'message': f'Type de message inconnu: {msg_type}'}
    
    def _register_institution(self, message: dict, client_socket: socket.socket) -> dict:
        """Enregistrer une nouvelle institution"""
        institution_id = message.get('institution_id')
        
        institution = ConnectedInstitution(
            institution_id=institution_id,
            name=message.get('name', ''),
            institution_type=InstitutionType(message.get('institution_type', 'UNIVERSITE')),
            region=message.get('region', ''),
            city=message.get('city', ''),
            contact_email=message.get('contact_email', ''),
            status=ConnectionStatus.CONNECTED
        )
        
        with self.connection_lock:
            self.connected_institutions[institution_id] = institution
            self.institution_sockets[institution_id] = client_socket
        
        print(f"✅ Institution enregistrée: {institution.name} ({institution.institution_type.value})")
        print(f"   📍 {institution.city}, {institution.region}")
        
        return {
            'status': 'success',
            'message': 'Institution enregistrée avec succès',
            'institution_id': institution_id
        }
    
    def _handle_create_stage(self, message: dict) -> dict:
        """Créer un nouveau stage"""
        stage_data = message.get('stage_data', {})
        result = self.stage_manager.create_stage(stage_data)
        
        if result['success']:
            self.total_stages_created += 1
            
            # Notifier les institutions concernées
            self._send_notification(
                stage_data.get('university_id'),
                'STAGE_CREATED',
                f"Nouveau stage créé: {stage_data.get('stage_title')}"
            )
            
            print(f"📋 Stage créé: {stage_data.get('stage_title')}")
            print(f"   🎓 Étudiant: {stage_data.get('student_name')}")
            print(f"   🏢 Entreprise: {stage_data.get('company_name')}")
        
        return result
    
    def _handle_update_stage(self, message: dict) -> dict:
        """Mettre à jour un stage"""
        return self.stage_manager.update_stage(
            message.get('stage_id'),
            message.get('field_name'),
            message.get('new_value'),
            message.get('updated_by')
        )
    
    def _handle_get_stage(self, message: dict) -> dict:
        """Récupérer les détails d'un stage"""
        stage = self.stage_manager.get_stage(message.get('stage_id'))
        if stage:
            return {'status': 'success', 'stage': stage}
        return {'status': 'error', 'message': 'Stage non trouvé'}
    
    def _handle_list_stages(self, message: dict) -> dict:
        """Lister les stages"""
        filters = message.get('filters', {})
        page = message.get('page', 1)
        page_size = message.get('page_size', 20)
        
        result = self.stage_manager.list_stages(filters, page, page_size)
        return {'status': 'success', **result}
    
    def _handle_delete_stage(self, message: dict) -> dict:
        """Supprimer un stage (soft delete)"""
        return self.stage_manager.update_stage(
            message.get('stage_id'),
            'status',
            'ANNULE',
            message.get('requester_id')
        )
    
    def _handle_assign_supervisor(self, message: dict) -> dict:
        """Assigner un encadreur"""
        result = self.stage_manager.assign_supervisor(
            message.get('stage_id'),
            message.get('supervisor_data', {})
        )
        
        if result['success']:
            supervisor_data = message.get('supervisor_data', {})
            print(f"👨‍🏫 Encadreur assigné: {supervisor_data.get('first_name')} {supervisor_data.get('last_name')}")
            print(f"   Type: {supervisor_data.get('supervisor_type')}")
        
        return result
    
    def _handle_list_supervisors(self, message: dict) -> dict:
        """Lister les encadreurs disponibles"""
        conn = self.stage_manager._get_connection()
        cursor = conn.cursor()
        
        query = 'SELECT * FROM supervisors WHERE current_students < max_students'
        if message.get('supervisor_type'):
            query += f" AND supervisor_type = '{message['supervisor_type']}'"
        if message.get('institution_id'):
            query += f" AND institution_id = '{message['institution_id']}'"
        
        cursor.execute(query)
        supervisors = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return {'status': 'success', 'supervisors': supervisors}
    
    def _handle_submit_report(self, message: dict, client_socket: socket.socket) -> dict:
        """Soumettre un rapport"""
        report_data = message.get('report_data', {})
        
        # Si un fichier est envoyé, le recevoir
        if message.get('has_file'):
            file_size = message.get('file_size', 0)
            client_socket.send(json.dumps({'status': 'ready'}).encode())
            
            file_data = b''
            while len(file_data) < file_size:
                chunk = client_socket.recv(min(8192, file_size - len(file_data)))
                if not chunk:
                    break
                file_data += chunk
            
            report_data['report_file'] = file_data
            report_data['filename'] = message.get('filename', 'rapport.pdf')
        
        result = self.stage_manager.submit_report(report_data)
        
        if result['success']:
            self.total_reports_submitted += 1
            print(f"📄 Rapport soumis: {report_data.get('title')}")
            print(f"   Type: {report_data.get('report_type')}")
        
        return result
    
    def _handle_list_reports(self, message: dict) -> dict:
        """Lister les rapports d'un stage"""
        import sqlite3
        conn = sqlite3.connect(self.stage_manager.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        stage_id = message.get('stage_id')
        cursor.execute('SELECT * FROM reports WHERE stage_id = ? ORDER BY submission_date DESC',
                      (stage_id,))
        reports = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return {'status': 'success', 'reports': reports}
    
    def _handle_review_report(self, message: dict) -> dict:
        """Évaluer un rapport"""
        import sqlite3
        conn = sqlite3.connect(self.stage_manager.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE reports SET 
                status = 'EVALUE',
                reviewed_by = ?,
                review_date = CURRENT_TIMESTAMP,
                feedback = ?,
                score = ?
            WHERE report_id = ?
        ''', (
            message.get('reviewer_id'),
            message.get('feedback', ''),
            message.get('score', 0),
            message.get('report_id')
        ))
        
        conn.commit()
        conn.close()
        
        print(f"✅ Rapport évalué: {message.get('report_id')[:8]}... - Note: {message.get('score')}/20")
        return {'status': 'success', 'message': 'Rapport évalué'}
    
    def _handle_evaluate_stage(self, message: dict) -> dict:
        """Évaluer un stage"""
        result = self.stage_manager.evaluate_stage(message.get('evaluation_data', {}))
        
        if result['success']:
            self.total_evaluations += 1
            print(f"📊 Évaluation enregistrée")
            print(f"   Note finale: {result['final_score']:.2f}/20 - {result['grade']}")
        
        return result
    
    def _handle_get_evaluations(self, message: dict) -> dict:
        """Récupérer les évaluations d'un stage"""
        import sqlite3
        conn = sqlite3.connect(self.stage_manager.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM evaluations WHERE stage_id = ?',
                      (message.get('stage_id'),))
        evaluations = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return {'status': 'success', 'evaluations': evaluations}
    
    def _handle_get_statistics(self, message: dict) -> dict:
        """Obtenir les statistiques"""
        stats = self.stage_manager.get_statistics(message.get('filters'))
        stats['server_stats'] = {
            'total_stages_created': self.total_stages_created,
            'total_reports_submitted': self.total_reports_submitted,
            'total_evaluations': self.total_evaluations,
            'connected_institutions': len(self.connected_institutions)
        }
        return {'status': 'success', 'statistics': stats}
    
    def _handle_generate_certificate(self, message: dict) -> dict:
        """Générer une attestation de stage"""
        return self.stage_service.generate_stage_certificate(message.get('stage_id'))
    
    def _send_notification(self, recipient_id: str, notification_type: str, message: str):
        """Envoyer une notification à une institution"""
        notification = {
            'type': 'notification',
            'notification_type': notification_type,
            'message': message,
            'timestamp': datetime.now().isoformat()
        }
        
        with self.connection_lock:
            if recipient_id in self.institution_sockets:
                try:
                    self.institution_sockets[recipient_id].send(json.dumps(notification).encode())
                except:
                    pass
    
    def _cleanup_disconnected_institution(self, institution_id: str):
        """Nettoyer une institution déconnectée"""
        print(f"🧹 Nettoyage de l'institution: {institution_id}")
        
        with self.connection_lock:
            if institution_id in self.connected_institutions:
                self.connected_institutions[institution_id].status = ConnectionStatus.DISCONNECTED
                del self.connected_institutions[institution_id]
            if institution_id in self.institution_sockets:
                del self.institution_sockets[institution_id]
    
    def _handle_disconnect(self, message: dict) -> dict:
        """Gérer la déconnexion explicite"""
        institution_id = message.get('institution_id')
        self._cleanup_disconnected_institution(institution_id)
        return {'status': 'success', 'message': 'Déconnecté'}
    
    def _connection_health_monitor(self):
        """Surveiller la santé des connexions"""
        while self.running:
            time.sleep(30)
            
            with self.connection_lock:
                for inst_id, sock in list(self.institution_sockets.items()):
                    try:
                        heartbeat = {'type': 'heartbeat', 'timestamp': time.time()}
                        sock.send(json.dumps(heartbeat).encode())
                    except:
                        print(f"💔 Connexion perdue: {inst_id}")
                        self._cleanup_disconnected_institution(inst_id)
    
    def _notification_dispatcher(self):
        """Dispatcher les notifications"""
        while self.running:
            try:
                notification = self.notification_queue.get(timeout=5)
                recipient_id = notification.get('recipient_id')
                
                with self.connection_lock:
                    if recipient_id in self.institution_sockets:
                        try:
                            self.institution_sockets[recipient_id].send(
                                json.dumps(notification).encode()
                            )
                        except:
                            pass
            except queue.Empty:
                continue
    
    def _status_monitor(self):
        """Afficher le statut périodiquement"""
        while self.running:
            time.sleep(60)
            
            print(f"\n📊 STATUT SERVEUR - {datetime.now().strftime('%H:%M:%S')}")
            print(f"   Institutions connectées: {len(self.connected_institutions)}")
            print(f"   Stages créés: {self.total_stages_created}")
            print(f"   Rapports soumis: {self.total_reports_submitted}")
            print(f"   Évaluations: {self.total_evaluations}")
            print("-" * 50)
    
    def stop_server(self):
        """Arrêter le serveur"""
        print("\n🛑 Arrêt du serveur...")
        self.running = False
        
        if self.server_socket:
            self.server_socket.close()
        
        with self.connection_lock:
            for sock in self.institution_sockets.values():
                try:
                    sock.close()
                except:
                    pass
        
        print("✅ Serveur arrêté")


def main():
    """Fonction principale"""
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python stage_server.py <host> <port>")
        print("Exemple: python stage_server.py localhost 8888")
        return
    
    host = sys.argv[1]
    port = int(sys.argv[2])
    
    server = StageServerManager(host, port)
    
    try:
        server_thread = threading.Thread(target=server.start_server, daemon=True)
        server_thread.start()
        
        print("\n" + "="*70)
        print(" CONSOLE D'ADMINISTRATION DU SERVEUR")
        print("="*70)
        print("Commandes disponibles:")
        print("  status     - Afficher le statut du serveur")
        print("  stats      - Afficher les statistiques")
        print("  institutions - Lister les institutions connectées")
        print("  stages     - Lister les stages récents")
        print("  quit       - Arrêter le serveur")
        print("="*70)
        
        while True:
            try:
                cmd = input("\nServeur> ").strip().lower()
                
                if cmd == 'quit':
                    break
                elif cmd == 'status':
                    print(f"\n📊 Statut du serveur:")
                    print(f"   En cours d'exécution: {server.running}")
                    print(f"   Institutions: {len(server.connected_institutions)}")
                    print(f"   Stages: {server.total_stages_created}")
                elif cmd == 'stats':
                    stats = server.stage_manager.get_statistics()
                    print(f"\n📈 Statistiques:")
                    print(f"   Par statut: {stats.get('by_status', {})}")
                    print(f"   Par région: {stats.get('by_region', {})}")
                    print(f"   Moyenne des notes: {stats.get('average_score', 0):.2f}/20")
                elif cmd == 'institutions':
                    print(f"\n🏛️ Institutions connectées ({len(server.connected_institutions)}):")
                    for inst_id, inst in server.connected_institutions.items():
                        print(f"   • {inst.name} ({inst.institution_type.value})")
                        print(f"     {inst.city}, {inst.region}")
                elif cmd == 'stages':
                    result = server.stage_manager.list_stages(page_size=10)
                    print(f"\n📋 Stages récents ({result['total_count']} total):")
                    for stage in result['stages'][:10]:
                        print(f"   • {stage['stage_title']}")
                        print(f"     {stage['student_name']} - {stage['status']}")
                else:
                    print("Commande inconnue")
                    
            except KeyboardInterrupt:
                break
                
    except KeyboardInterrupt:
        pass
    finally:
        server.stop_server()


if __name__ == "__main__":
    main()
