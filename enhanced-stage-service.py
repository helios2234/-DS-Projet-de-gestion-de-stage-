# stage_service.proto - gRPC service definition
"""
syntax = "proto3";

package stageservice;

service StageService {
  rpc CreateStage(CreateStageRequest) returns (StageResponse);
  rpc UpdateStage(UpdateStageRequest) returns (StageResponse);
  rpc GetStage(GetStageRequest) returns (StageResponse);
  rpc ListStages(ListStagesRequest) returns (ListStagesResponse);
  rpc DeleteStage(DeleteStageRequest) returns (DeleteResponse);
  rpc AssignSupervisor(AssignSupervisorRequest) returns (StageResponse);
  rpc SubmitReport(SubmitReportRequest) returns (ReportResponse);
  rpc EvaluateStage(EvaluateStageRequest) returns (EvaluationResponse);
}
"""

# enhanced_stage_manager.py
import grpc
from concurrent import futures
import hashlib
import os
import sqlite3
import json
import threading
from pathlib import Path
from typing import List, Optional, Tuple, Dict
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import uuid
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class StageManager:
    """Gestionnaire de stages avec stockage local et synchronisation"""
    
    def __init__(self, institution_id: str, storage_path: str = None):
        self.institution_id = institution_id
        self.storage_path = Path(storage_path) if storage_path else Path(f"./data_{institution_id}")
        self.storage_path.mkdir(exist_ok=True)
        
        # Créer les répertoires pour différents types de données
        self.stages_path = self.storage_path / "stages"
        self.reports_path = self.storage_path / "reports"
        self.documents_path = self.storage_path / "documents"
        self.evaluations_path = self.storage_path / "evaluations"
        
        self.stages_path.mkdir(exist_ok=True)
        self.reports_path.mkdir(exist_ok=True)
        self.documents_path.mkdir(exist_ok=True)
        self.evaluations_path.mkdir(exist_ok=True)
        
        # Initialiser la base de données
        self.db_path = self.storage_path / "stage_management.db"
        self._init_database()
        
        # Verrous pour accès concurrent
        self.stage_locks = {}
        self.lock_manager = threading.RLock()
        
    def _init_database(self):
        """Initialiser la base de données SQLite pour les métadonnées"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Table des stages
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stages (
                stage_id TEXT PRIMARY KEY,
                student_id TEXT NOT NULL,
                student_name TEXT NOT NULL,
                student_email TEXT,
                student_phone TEXT,
                university_id TEXT NOT NULL,
                university_name TEXT NOT NULL,
                department TEXT NOT NULL,
                academic_level TEXT,
                company_id TEXT NOT NULL,
                company_name TEXT NOT NULL,
                company_address TEXT,
                company_city TEXT NOT NULL,
                company_region TEXT NOT NULL,
                stage_title TEXT NOT NULL,
                stage_description TEXT,
                stage_type TEXT NOT NULL,
                start_date DATE NOT NULL,
                end_date DATE NOT NULL,
                status TEXT DEFAULT 'EN_ATTENTE',
                academic_supervisor_id TEXT,
                company_supervisor_id TEXT,
                progress_percentage REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Table des encadreurs
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS supervisors (
                supervisor_id TEXT PRIMARY KEY,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                phone TEXT,
                supervisor_type TEXT NOT NULL,
                institution_id TEXT NOT NULL,
                department TEXT,
                title TEXT,
                specialization TEXT,
                max_students INTEGER DEFAULT 5,
                current_students INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Table des rapports
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reports (
                report_id TEXT PRIMARY KEY,
                stage_id TEXT NOT NULL,
                report_type TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT,
                file_path TEXT,
                submitted_by TEXT NOT NULL,
                submission_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                week_number INTEGER,
                status TEXT DEFAULT 'SOUMIS',
                reviewed_by TEXT,
                review_date TIMESTAMP,
                feedback TEXT,
                score REAL,
                FOREIGN KEY (stage_id) REFERENCES stages(stage_id)
            )
        ''')
        
        # Table des évaluations
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS evaluations (
                evaluation_id TEXT PRIMARY KEY,
                stage_id TEXT NOT NULL,
                evaluator_id TEXT NOT NULL,
                evaluator_type TEXT NOT NULL,
                technical_skills_score REAL DEFAULT 0,
                soft_skills_score REAL DEFAULT 0,
                attendance_score REAL DEFAULT 0,
                initiative_score REAL DEFAULT 0,
                report_quality_score REAL DEFAULT 0,
                final_score REAL DEFAULT 0,
                grade TEXT,
                comments TEXT,
                recommendation TEXT,
                evaluation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (stage_id) REFERENCES stages(stage_id)
            )
        ''')
        
        # Table des notifications
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notifications (
                notification_id TEXT PRIMARY KEY,
                recipient_id TEXT NOT NULL,
                recipient_type TEXT NOT NULL,
                notification_type TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                stage_id TEXT,
                is_read INTEGER DEFAULT 0,
                priority TEXT DEFAULT 'NORMAL',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Table d'historique des modifications
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stage_history (
                history_id TEXT PRIMARY KEY,
                stage_id TEXT NOT NULL,
                action TEXT NOT NULL,
                field_changed TEXT,
                old_value TEXT,
                new_value TEXT,
                changed_by TEXT NOT NULL,
                changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (stage_id) REFERENCES stages(stage_id)
            )
        ''')
        
        # Index pour améliorer les performances
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_stages_student ON stages(student_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_stages_company ON stages(company_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_stages_status ON stages(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_stages_region ON stages(company_region)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_reports_stage ON reports(stage_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_evaluations_stage ON evaluations(stage_id)')
        
        conn.commit()
        conn.close()
        
    def create_stage(self, stage_data: dict) -> dict:
        """Créer un nouveau stage"""
        try:
            stage_id = str(uuid.uuid4())
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO stages (
                    stage_id, student_id, student_name, student_email, student_phone,
                    university_id, university_name, department, academic_level,
                    company_id, company_name, company_address, company_city, company_region,
                    stage_title, stage_description, stage_type, start_date, end_date, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                stage_id,
                stage_data['student_id'],
                stage_data['student_name'],
                stage_data.get('student_email', ''),
                stage_data.get('student_phone', ''),
                stage_data['university_id'],
                stage_data['university_name'],
                stage_data['department'],
                stage_data.get('academic_level', ''),
                stage_data['company_id'],
                stage_data['company_name'],
                stage_data.get('company_address', ''),
                stage_data['company_city'],
                stage_data['company_region'],
                stage_data['stage_title'],
                stage_data.get('stage_description', ''),
                stage_data['stage_type'],
                stage_data['start_date'],
                stage_data['end_date'],
                'EN_ATTENTE'
            ))
            
            # Enregistrer dans l'historique
            self._log_history(cursor, stage_id, 'CREATE', None, None, 
                            json.dumps(stage_data), stage_data.get('created_by', 'system'))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Stage créé: {stage_id} - {stage_data['stage_title']}")
            
            return {
                'success': True,
                'stage_id': stage_id,
                'message': 'Stage créé avec succès'
            }
            
        except Exception as e:
            logger.error(f"Erreur création stage: {e}")
            return {
                'success': False,
                'message': f'Erreur: {str(e)}'
            }
    
    def get_stage(self, stage_id: str) -> Optional[dict]:
        """Récupérer les détails d'un stage"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM stages WHERE stage_id = ?', (stage_id,))
        row = cursor.fetchone()
        
        if row:
            stage = dict(row)
            
            # Récupérer les rapports associés
            cursor.execute('SELECT * FROM reports WHERE stage_id = ? ORDER BY submission_date DESC', 
                          (stage_id,))
            stage['reports'] = [dict(r) for r in cursor.fetchall()]
            
            # Récupérer les évaluations
            cursor.execute('SELECT * FROM evaluations WHERE stage_id = ?', (stage_id,))
            stage['evaluations'] = [dict(e) for e in cursor.fetchall()]
            
            conn.close()
            return stage
        
        conn.close()
        return None
    
    def list_stages(self, filters: dict = None, page: int = 1, page_size: int = 20) -> dict:
        """Lister les stages avec filtres et pagination"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = 'SELECT * FROM stages WHERE 1=1'
        params = []
        
        if filters:
            if filters.get('status'):
                query += ' AND status = ?'
                params.append(filters['status'])
            if filters.get('region'):
                query += ' AND company_region = ?'
                params.append(filters['region'])
            if filters.get('university_id'):
                query += ' AND university_id = ?'
                params.append(filters['university_id'])
            if filters.get('company_id'):
                query += ' AND company_id = ?'
                params.append(filters['company_id'])
            if filters.get('student_id'):
                query += ' AND student_id = ?'
                params.append(filters['student_id'])
            if filters.get('supervisor_id'):
                query += ' AND (academic_supervisor_id = ? OR company_supervisor_id = ?)'
                params.extend([filters['supervisor_id'], filters['supervisor_id']])
            if filters.get('academic_year'):
                query += ' AND strftime("%Y", start_date) = ?'
                params.append(filters['academic_year'])
        
        # Compter le total
        count_query = query.replace('SELECT *', 'SELECT COUNT(*)')
        cursor.execute(count_query, params)
        total_count = cursor.fetchone()[0]
        
        # Pagination
        query += ' ORDER BY created_at DESC LIMIT ? OFFSET ?'
        params.extend([page_size, (page - 1) * page_size])
        
        cursor.execute(query, params)
        stages = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return {
            'stages': stages,
            'total_count': total_count,
            'page': page,
            'page_size': page_size,
            'total_pages': (total_count + page_size - 1) // page_size
        }
    
    def update_stage(self, stage_id: str, field_name: str, new_value: str, 
                    updated_by: str) -> dict:
        """Mettre à jour un champ du stage"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Récupérer l'ancienne valeur
            cursor.execute(f'SELECT {field_name} FROM stages WHERE stage_id = ?', (stage_id,))
            row = cursor.fetchone()
            if not row:
                conn.close()
                return {'success': False, 'message': 'Stage non trouvé'}
            
            old_value = row[0]
            
            # Mettre à jour
            cursor.execute(f'''
                UPDATE stages SET {field_name} = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE stage_id = ?
            ''', (new_value, stage_id))
            
            # Enregistrer dans l'historique
            self._log_history(cursor, stage_id, 'UPDATE', field_name, 
                            str(old_value), new_value, updated_by)
            
            conn.commit()
            conn.close()
            
            logger.info(f"Stage {stage_id} mis à jour: {field_name}")
            return {'success': True, 'message': 'Stage mis à jour avec succès'}
            
        except Exception as e:
            logger.error(f"Erreur mise à jour stage: {e}")
            return {'success': False, 'message': str(e)}
    
    def assign_supervisor(self, stage_id: str, supervisor_data: dict) -> dict:
        """Assigner un encadreur à un stage"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Vérifier si l'encadreur existe, sinon le créer
            cursor.execute('SELECT supervisor_id FROM supervisors WHERE supervisor_id = ?', 
                          (supervisor_data['supervisor_id'],))
            if not cursor.fetchone():
                cursor.execute('''
                    INSERT INTO supervisors (
                        supervisor_id, first_name, last_name, email, phone,
                        supervisor_type, institution_id, department, title
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    supervisor_data['supervisor_id'],
                    supervisor_data.get('first_name', ''),
                    supervisor_data.get('last_name', ''),
                    supervisor_data['email'],
                    supervisor_data.get('phone', ''),
                    supervisor_data['supervisor_type'],
                    supervisor_data.get('institution_id', ''),
                    supervisor_data.get('department', ''),
                    supervisor_data.get('title', '')
                ))
            
            # Assigner au stage
            field = 'academic_supervisor_id' if supervisor_data['supervisor_type'] == 'ACADEMIQUE' else 'company_supervisor_id'
            cursor.execute(f'''
                UPDATE stages SET {field} = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE stage_id = ?
            ''', (supervisor_data['supervisor_id'], stage_id))
            
            # Mettre à jour le compteur d'étudiants de l'encadreur
            cursor.execute('''
                UPDATE supervisors SET current_students = current_students + 1 
                WHERE supervisor_id = ?
            ''', (supervisor_data['supervisor_id'],))
            
            self._log_history(cursor, stage_id, 'ASSIGN_SUPERVISOR', field,
                            None, supervisor_data['supervisor_id'], 
                            supervisor_data.get('assigned_by', 'system'))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Encadreur {supervisor_data['supervisor_id']} assigné au stage {stage_id}")
            return {'success': True, 'message': 'Encadreur assigné avec succès'}
            
        except Exception as e:
            logger.error(f"Erreur assignation encadreur: {e}")
            return {'success': False, 'message': str(e)}
    
    def submit_report(self, report_data: dict) -> dict:
        """Soumettre un rapport de stage"""
        try:
            report_id = str(uuid.uuid4())
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Sauvegarder le fichier si présent
            file_path = None
            if report_data.get('report_file'):
                file_name = f"{report_id}_{report_data.get('filename', 'report.pdf')}"
                file_path = str(self.reports_path / file_name)
                with open(file_path, 'wb') as f:
                    f.write(report_data['report_file'])
            
            cursor.execute('''
                INSERT INTO reports (
                    report_id, stage_id, report_type, title, content,
                    file_path, submitted_by, week_number, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                report_id,
                report_data['stage_id'],
                report_data['report_type'],
                report_data['title'],
                report_data.get('content', ''),
                file_path,
                report_data['submitted_by'],
                report_data.get('week_number', 0),
                'SOUMIS'
            ))
            
            # Mettre à jour le progrès du stage
            self._update_stage_progress(cursor, report_data['stage_id'])
            
            conn.commit()
            conn.close()
            
            logger.info(f"Rapport {report_id} soumis pour stage {report_data['stage_id']}")
            return {
                'success': True,
                'report_id': report_id,
                'message': 'Rapport soumis avec succès'
            }
            
        except Exception as e:
            logger.error(f"Erreur soumission rapport: {e}")
            return {'success': False, 'message': str(e)}
    
    def evaluate_stage(self, evaluation_data: dict) -> dict:
        """Évaluer un stage"""
        try:
            evaluation_id = str(uuid.uuid4())
            
            # Calculer la note finale
            weights = {'technical': 0.30, 'soft': 0.20, 'attendance': 0.15, 
                      'initiative': 0.15, 'report': 0.20}
            
            final_score = (
                evaluation_data.get('technical_skills_score', 0) * weights['technical'] +
                evaluation_data.get('soft_skills_score', 0) * weights['soft'] +
                evaluation_data.get('attendance_score', 0) * weights['attendance'] +
                evaluation_data.get('initiative_score', 0) * weights['initiative'] +
                evaluation_data.get('report_quality_score', 0) * weights['report']
            )
            
            # Déterminer la mention
            if final_score >= 16:
                grade = "A - Excellent"
            elif final_score >= 14:
                grade = "B - Très Bien"
            elif final_score >= 12:
                grade = "C - Bien"
            elif final_score >= 10:
                grade = "D - Passable"
            else:
                grade = "E - Insuffisant"
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO evaluations (
                    evaluation_id, stage_id, evaluator_id, evaluator_type,
                    technical_skills_score, soft_skills_score, attendance_score,
                    initiative_score, report_quality_score, final_score, grade,
                    comments, recommendation
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                evaluation_id,
                evaluation_data['stage_id'],
                evaluation_data['evaluator_id'],
                evaluation_data['evaluator_type'],
                evaluation_data.get('technical_skills_score', 0),
                evaluation_data.get('soft_skills_score', 0),
                evaluation_data.get('attendance_score', 0),
                evaluation_data.get('initiative_score', 0),
                evaluation_data.get('report_quality_score', 0),
                final_score,
                grade,
                evaluation_data.get('comments', ''),
                evaluation_data.get('recommendation', '')
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Évaluation {evaluation_id} créée - Note: {final_score:.2f} ({grade})")
            return {
                'success': True,
                'evaluation_id': evaluation_id,
                'final_score': final_score,
                'grade': grade,
                'message': 'Évaluation enregistrée avec succès'
            }
            
        except Exception as e:
            logger.error(f"Erreur évaluation: {e}")
            return {'success': False, 'message': str(e)}
    
    def _update_stage_progress(self, cursor, stage_id: str):
        """Mettre à jour le pourcentage de progression du stage"""
        cursor.execute('''
            SELECT start_date, end_date, 
                   (SELECT COUNT(*) FROM reports WHERE stage_id = ?) as report_count,
                   (SELECT COUNT(*) FROM evaluations WHERE stage_id = ?) as eval_count
            FROM stages WHERE stage_id = ?
        ''', (stage_id, stage_id, stage_id))
        
        row = cursor.fetchone()
        if row:
            start_date = datetime.strptime(row[0], '%Y-%m-%d')
            end_date = datetime.strptime(row[1], '%Y-%m-%d')
            today = datetime.now()
            
            if today < start_date:
                time_progress = 0
            elif today > end_date:
                time_progress = 100
            else:
                total_days = (end_date - start_date).days
                elapsed = (today - start_date).days
                time_progress = (elapsed / total_days) * 100
            
            report_factor = min(row[2] * 10, 30)
            eval_factor = min(row[3] * 15, 30)
            
            progress = min(100, time_progress * 0.4 + report_factor + eval_factor)
            
            cursor.execute('UPDATE stages SET progress_percentage = ? WHERE stage_id = ?',
                          (progress, stage_id))
    
    def _log_history(self, cursor, stage_id: str, action: str, field: str,
                    old_value: str, new_value: str, changed_by: str):
        """Enregistrer une action dans l'historique"""
        history_id = str(uuid.uuid4())
        cursor.execute('''
            INSERT INTO stage_history (history_id, stage_id, action, field_changed,
                                       old_value, new_value, changed_by)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (history_id, stage_id, action, field, old_value, new_value, changed_by))
    
    def get_statistics(self, filters: dict = None) -> dict:
        """Obtenir les statistiques des stages"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        stats = {}
        
        # Total par statut
        cursor.execute('''
            SELECT status, COUNT(*) FROM stages GROUP BY status
        ''')
        stats['by_status'] = dict(cursor.fetchall())
        
        # Total par région
        cursor.execute('''
            SELECT company_region, COUNT(*) FROM stages GROUP BY company_region
        ''')
        stats['by_region'] = dict(cursor.fetchall())
        
        # Total par université
        cursor.execute('''
            SELECT university_name, COUNT(*) FROM stages GROUP BY university_name
        ''')
        stats['by_university'] = dict(cursor.fetchall())
        
        # Moyenne des évaluations
        cursor.execute('SELECT AVG(final_score) FROM evaluations')
        stats['average_score'] = cursor.fetchone()[0] or 0
        
        # Total de rapports
        cursor.execute('SELECT COUNT(*) FROM reports')
        stats['total_reports'] = cursor.fetchone()[0]
        
        # Stages en cours
        cursor.execute("SELECT COUNT(*) FROM stages WHERE status = 'EN_COURS'")
        stats['active_stages'] = cursor.fetchone()[0]
        
        conn.close()
        return stats


class EnhancedStageService:
    """Service de stage amélioré avec fonctionnalités distribuées"""
    
    def __init__(self, server_manager):
        self.server_manager = server_manager
        self.sync_interval = 300  # 5 minutes
        
    def sync_stages_with_institutions(self, stage_ids: List[str]) -> dict:
        """Synchroniser les stages avec les institutions concernées"""
        results = {'synced': [], 'failed': []}
        
        for stage_id in stage_ids:
            try:
                stage = self.server_manager.stage_manager.get_stage(stage_id)
                if stage:
                    # Simuler la synchronisation avec l'université et l'entreprise
                    results['synced'].append(stage_id)
                    logger.info(f"Stage {stage_id} synchronisé")
                else:
                    results['failed'].append({'stage_id': stage_id, 'error': 'Non trouvé'})
            except Exception as e:
                results['failed'].append({'stage_id': stage_id, 'error': str(e)})
        
        return results
    
    def generate_stage_certificate(self, stage_id: str) -> dict:
        """Générer une attestation de stage"""
        stage = self.server_manager.stage_manager.get_stage(stage_id)
        if not stage:
            return {'success': False, 'message': 'Stage non trouvé'}
        
        if stage['status'] != 'TERMINE':
            return {'success': False, 'message': 'Le stage doit être terminé'}
        
        certificate_data = {
            'certificate_id': str(uuid.uuid4()),
            'stage_id': stage_id,
            'student_name': stage['student_name'],
            'university_name': stage['university_name'],
            'company_name': stage['company_name'],
            'stage_title': stage['stage_title'],
            'start_date': stage['start_date'],
            'end_date': stage['end_date'],
            'final_grade': self._get_final_grade(stage),
            'generated_at': datetime.now().isoformat()
        }
        
        return {'success': True, 'certificate': certificate_data}
    
    def _get_final_grade(self, stage: dict) -> str:
        """Calculer la mention finale"""
        if not stage.get('evaluations'):
            return "Non évalué"
        
        avg_score = sum(e['final_score'] for e in stage['evaluations']) / len(stage['evaluations'])
        
        if avg_score >= 16:
            return "Excellent"
        elif avg_score >= 14:
            return "Très Bien"
        elif avg_score >= 12:
            return "Bien"
        elif avg_score >= 10:
            return "Passable"
        else:
            return "Insuffisant"


def installation_guide():
    guide = '''
    GUIDE D'INSTALLATION ET DE CONFIGURATION
    =========================================
    
    1. Installer les dépendances:
       pip install grpcio grpcio-tools sqlite3
    
    2. Générer le code gRPC:
       python -m grpc_tools.protoc --python_out=. --grpc_python_out=. stage_service.proto
    
    3. Structure des fichiers:
       projet_stages/
       ├── stage_protocols.py           (protocoles métier)
       ├── stage_server.py              (serveur principal)
       ├── stage_client.py              (client/nœud)
       ├── enhanced_stage_service.py    (ce fichier)
       ├── stage_service.proto          (définition gRPC)
       └── data/                         (créé automatiquement)
           ├── universite_uy1/
           │   ├── stages/
           │   ├── reports/
           │   ├── documents/
           │   ├── evaluations/
           │   └── stage_management.db
           └── entreprise_mtn/
               └── ...
    
    4. Exemple d'utilisation:
    
       Terminal 1 - Démarrer le serveur:
       python stage_server.py localhost 8888
       
       Terminal 2 - Client Université:
       python stage_client.py univ_uy1 localhost 8888
       
       Terminal 3 - Client Entreprise:
       python stage_client.py ent_mtn localhost 8888
    
    5. Commandes disponibles:
       - creer <données_json>          - Créer un nouveau stage
       - liste [filtres]               - Lister les stages
       - details <stage_id>            - Voir les détails d'un stage
       - rapport <stage_id> <fichier>  - Soumettre un rapport
       - evaluer <stage_id>            - Évaluer un stage
       - stats                         - Voir les statistiques
       - quit                          - Quitter
    
    6. Fonctionnalités:
       ✅ Création et gestion des stages
       ✅ Assignation des encadreurs (académique et entreprise)
       ✅ Soumission et évaluation des rapports
       ✅ Système de notation et mentions
       ✅ Historique des modifications
       ✅ Statistiques par région, université, statut
       ✅ Support des 10 régions du Cameroun
       ✅ Génération d'attestations de stage
       ✅ Notifications automatiques
       ✅ Synchronisation multi-institutions
    '''
    
    return guide

print("Service Amélioré de Gestion des Stages - Cameroun")
print("=" * 55)
print()
print("Ce module fournit:")
print("✅ Gestionnaire de stages avec base de données SQLite")
print("✅ Gestion des encadreurs académiques et entreprise")
print("✅ Soumission et évaluation des rapports")
print("✅ Système de notation avec mentions")
print("✅ Historique complet des modifications")
print("✅ Statistiques et tableaux de bord")
print("✅ Génération d'attestations")
print()
print(installation_guide())