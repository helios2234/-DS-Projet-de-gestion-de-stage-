import random
import hashlib
import time
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from enum import Enum
from datetime import datetime, timedelta

class StageStatus(Enum):
    """Statuts possibles d'un stage"""
    PENDING = "EN_ATTENTE"
    APPROVED = "APPROUVE"
    IN_PROGRESS = "EN_COURS"
    COMPLETED = "TERMINE"
    CANCELLED = "ANNULE"
    SUSPENDED = "SUSPENDU"

class ReportType(Enum):
    """Types de rapports de stage"""
    WEEKLY = "HEBDOMADAIRE"
    MONTHLY = "MENSUEL"
    MIDTERM = "MI_PARCOURS"
    FINAL = "FINAL"
    ACTIVITY = "ACTIVITE"

class UserRole(Enum):
    """Rôles des utilisateurs"""
    STUDENT = "ETUDIANT"
    ACADEMIC_SUPERVISOR = "ENCADREUR_ACADEMIQUE"
    COMPANY_SUPERVISOR = "ENCADREUR_ENTREPRISE"
    ADMIN = "ADMINISTRATEUR"
    COORDINATOR = "COORDINATEUR"

class Region(Enum):
    """Régions du Cameroun"""
    ADAMAOUA = "Adamaoua"
    CENTRE = "Centre"
    EST = "Est"
    EXTREME_NORD = "Extrême-Nord"
    LITTORAL = "Littoral"
    NORD = "Nord"
    NORD_OUEST = "Nord-Ouest"
    OUEST = "Ouest"
    SUD = "Sud"
    SUD_OUEST = "Sud-Ouest"

@dataclass
class University:
    """Représente une université camerounaise"""
    university_id: str
    name: str
    acronym: str
    city: str
    region: Region
    departments: List[str] = field(default_factory=list)
    contact_email: str = ""
    contact_phone: str = ""
    
    def __post_init__(self):
        if not self.university_id:
            self.university_id = hashlib.md5(f"{self.name}{self.city}".encode()).hexdigest()[:12]

@dataclass
class Company:
    """Représente une entreprise d'accueil"""
    company_id: str
    name: str
    sector: str
    address: str
    city: str
    region: Region
    contact_name: str = ""
    contact_email: str = ""
    contact_phone: str = ""
    is_verified: bool = False
    partnership_status: str = "STANDARD"
    
    def __post_init__(self):
        if not self.company_id:
            self.company_id = hashlib.md5(f"{self.name}{self.city}".encode()).hexdigest()[:12]

@dataclass
class Student:
    """Représente un étudiant stagiaire"""
    student_id: str
    matricule: str
    first_name: str
    last_name: str
    email: str
    phone: str
    university_id: str
    department: str
    academic_level: str
    academic_year: str
    date_of_birth: str = ""
    gender: str = ""
    address: str = ""
    
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"
    
    def __post_init__(self):
        if not self.student_id:
            self.student_id = hashlib.md5(f"{self.matricule}{self.email}".encode()).hexdigest()[:12]

@dataclass
class Supervisor:
    """Représente un encadreur (académique ou entreprise)"""
    supervisor_id: str
    first_name: str
    last_name: str
    email: str
    phone: str
    supervisor_type: str
    institution_id: str
    department: str = ""
    title: str = ""
    specialization: str = ""
    max_students: int = 5
    current_students: int = 0
    
    @property
    def full_name(self) -> str:
        return f"{self.title} {self.first_name} {self.last_name}".strip()
    
    @property
    def is_available(self) -> bool:
        return self.current_students < self.max_students
    
    def __post_init__(self):
        if not self.supervisor_id:
            self.supervisor_id = hashlib.md5(f"{self.email}{self.supervisor_type}".encode()).hexdigest()[:12]

@dataclass
class StageReport:
    """Représente un rapport de stage"""
    report_id: str
    stage_id: str
    report_type: ReportType
    title: str
    content: str
    submitted_by: str
    submission_date: datetime
    week_number: int = 0
    file_path: str = ""
    status: str = "SOUMIS"
    reviewed_by: str = ""
    review_date: Optional[datetime] = None
    feedback: str = ""
    score: float = 0.0
    
    def __post_init__(self):
        if not self.report_id:
            self.report_id = str(hashlib.md5(
                f"{self.stage_id}{self.report_type.value}{time.time()}".encode()
            ).hexdigest()[:12])

@dataclass
class StageEvaluation:
    """Représente une évaluation de stage"""
    evaluation_id: str
    stage_id: str
    evaluator_id: str
    evaluator_type: str
    evaluation_date: datetime
    technical_skills_score: float = 0.0
    soft_skills_score: float = 0.0
    attendance_score: float = 0.0
    initiative_score: float = 0.0
    report_quality_score: float = 0.0
    comments: str = ""
    recommendation: str = ""
    
    @property
    def final_score(self) -> float:
        weights = {
            'technical': 0.30,
            'soft': 0.20,
            'attendance': 0.15,
            'initiative': 0.15,
            'report': 0.20
        }
        return (
            self.technical_skills_score * weights['technical'] +
            self.soft_skills_score * weights['soft'] +
            self.attendance_score * weights['attendance'] +
            self.initiative_score * weights['initiative'] +
            self.report_quality_score * weights['report']
        )
    
    @property
    def grade(self) -> str:
        score = self.final_score
        if score >= 16:
            return "A - Excellent"
        elif score >= 14:
            return "B - Très Bien"
        elif score >= 12:
            return "C - Bien"
        elif score >= 10:
            return "D - Passable"
        else:
            return "E - Insuffisant"
    
    def __post_init__(self):
        if not self.evaluation_id:
            self.evaluation_id = hashlib.md5(
                f"{self.stage_id}{self.evaluator_id}{time.time()}".encode()
            ).hexdigest()[:12]

@dataclass
class Stage:
    """Représente un stage complet"""
    stage_id: str
    student: Student
    company: Company
    university: University
    title: str
    description: str
    start_date: datetime
    end_date: datetime
    stage_type: str
    status: StageStatus = StageStatus.PENDING
    academic_supervisor: Optional[Supervisor] = None
    company_supervisor: Optional[Supervisor] = None
    reports: List[StageReport] = field(default_factory=list)
    evaluations: List[StageEvaluation] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    @property
    def duration_weeks(self) -> int:
        delta = self.end_date - self.start_date
        return delta.days // 7
    
    @property
    def progress_percentage(self) -> float:
        if self.status == StageStatus.COMPLETED:
            return 100.0
        elif self.status in [StageStatus.PENDING, StageStatus.CANCELLED]:
            return 0.0
        
        today = datetime.now()
        if today < self.start_date:
            return 0.0
        elif today > self.end_date:
            return 100.0
        
        total_days = (self.end_date - self.start_date).days
        elapsed_days = (today - self.start_date).days
        return min(100.0, (elapsed_days / total_days) * 100)
    
    @property
    def final_grade(self) -> Optional[str]:
        if not self.evaluations:
            return None
        avg_score = sum(e.final_score for e in self.evaluations) / len(self.evaluations)
        if avg_score >= 16:
            return "A - Excellent"
        elif avg_score >= 14:
            return "B - Très Bien"
        elif avg_score >= 12:
            return "C - Bien"
        elif avg_score >= 10:
            return "D - Passable"
        else:
            return "E - Insuffisant"
    
    def __post_init__(self):
        if not self.stage_id:
            self.stage_id = hashlib.md5(
                f"{self.student.student_id}{self.company.company_id}{time.time()}".encode()
            ).hexdigest()[:16]

class StageValidationProtocol:
    """Protocole de validation des stages"""
    
    MINIMUM_DURATION_WEEKS = 4
    MAXIMUM_DURATION_WEEKS = 26
    REQUIRED_REPORTS_PER_MONTH = 1
    MINIMUM_EVALUATION_SCORE = 10.0
    
    @staticmethod
    def validate_stage_creation(stage_data: dict) -> tuple:
        """Valide les données de création d'un stage"""
        errors = []
        warnings = []
        
        # Vérification des dates
        start_date = stage_data.get('start_date')
        end_date = stage_data.get('end_date')
        
        if start_date and end_date:
            if isinstance(start_date, str):
                start_date = datetime.fromisoformat(start_date)
            if isinstance(end_date, str):
                end_date = datetime.fromisoformat(end_date)
            
            duration_weeks = (end_date - start_date).days // 7
            
            if duration_weeks < StageValidationProtocol.MINIMUM_DURATION_WEEKS:
                errors.append(f"Durée minimale: {StageValidationProtocol.MINIMUM_DURATION_WEEKS} semaines")
            
            if duration_weeks > StageValidationProtocol.MAXIMUM_DURATION_WEEKS:
                errors.append(f"Durée maximale: {StageValidationProtocol.MAXIMUM_DURATION_WEEKS} semaines")
            
            if start_date < datetime.now():
                warnings.append("La date de début est dans le passé")
        
        # Vérification des champs obligatoires
        required_fields = ['student_id', 'company_id', 'university_id', 'title', 'stage_type']
        for field in required_fields:
            if not stage_data.get(field):
                errors.append(f"Champ obligatoire manquant: {field}")
        
        return len(errors) == 0, errors, warnings
    
    @staticmethod
    def validate_report_submission(stage: Stage, report_type: ReportType) -> tuple:
        """Valide la soumission d'un rapport"""
        errors = []
        
        if stage.status not in [StageStatus.IN_PROGRESS, StageStatus.APPROVED]:
            errors.append("Le stage doit être en cours pour soumettre un rapport")
        
        if report_type == ReportType.FINAL:
            progress = stage.progress_percentage
            if progress < 80:
                errors.append("Le rapport final ne peut être soumis qu'à partir de 80% d'avancement")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def calculate_completion_requirements(stage: Stage) -> dict:
        """Calcule les exigences de complétion du stage"""
        duration_months = stage.duration_weeks / 4
        required_reports = int(duration_months * StageValidationProtocol.REQUIRED_REPORTS_PER_MONTH)
        
        return {
            'required_weekly_reports': required_reports,
            'required_midterm_report': stage.duration_weeks >= 8,
            'required_final_report': True,
            'required_evaluations': 2,
            'minimum_attendance': 80,
            'submitted_reports': len(stage.reports),
            'submitted_evaluations': len(stage.evaluations)
        }

class NotificationProtocol:
    """Protocole de notification pour le système de stage"""
    
    NOTIFICATION_TYPES = {
        'STAGE_CREATED': "Nouveau stage créé",
        'STAGE_APPROVED': "Stage approuvé",
        'STAGE_STARTED': "Stage démarré",
        'SUPERVISOR_ASSIGNED': "Encadreur assigné",
        'REPORT_SUBMITTED': "Rapport soumis",
        'REPORT_REVIEWED': "Rapport évalué",
        'EVALUATION_COMPLETED': "Évaluation complétée",
        'STAGE_COMPLETED': "Stage terminé",
        'DEADLINE_REMINDER': "Rappel d'échéance",
        'STAGE_CANCELLED': "Stage annulé"
    }
    
    @staticmethod
    def generate_notification(notification_type: str, stage: Stage, 
                            recipient_role: UserRole, additional_data: dict = None) -> dict:
        """Génère une notification"""
        notification = {
            'id': hashlib.md5(f"{notification_type}{stage.stage_id}{time.time()}".encode()).hexdigest()[:12],
            'type': notification_type,
            'title': NotificationProtocol.NOTIFICATION_TYPES.get(notification_type, "Notification"),
            'stage_id': stage.stage_id,
            'stage_title': stage.title,
            'recipient_role': recipient_role.value,
            'created_at': datetime.now().isoformat(),
            'is_read': False,
            'priority': 'NORMAL'
        }
        
        # Définir la priorité et le message selon le type
        if notification_type == 'DEADLINE_REMINDER':
            notification['priority'] = 'HIGH'
            notification['message'] = f"Rappel: Échéance proche pour le stage '{stage.title}'"
        elif notification_type == 'STAGE_CANCELLED':
            notification['priority'] = 'HIGH'
            notification['message'] = f"Le stage '{stage.title}' a été annulé"
        elif notification_type == 'EVALUATION_COMPLETED':
            notification['message'] = f"Une nouvelle évaluation a été soumise pour '{stage.title}'"
        else:
            notification['message'] = f"{NotificationProtocol.NOTIFICATION_TYPES.get(notification_type)} - {stage.title}"
        
        if additional_data:
            notification.update(additional_data)
        
        return notification
    
    @staticmethod
    def get_recipients_for_notification(notification_type: str, stage: Stage) -> List[str]:
        """Détermine les destinataires d'une notification"""
        recipients = []
        
        # L'étudiant reçoit toutes les notifications concernant son stage
        recipients.append(stage.student.email)
        
        # Les encadreurs reçoivent certaines notifications
        supervisor_notifications = [
            'REPORT_SUBMITTED', 'STAGE_STARTED', 'STAGE_COMPLETED', 
            'DEADLINE_REMINDER', 'STAGE_CANCELLED'
        ]
        
        if notification_type in supervisor_notifications:
            if stage.academic_supervisor:
                recipients.append(stage.academic_supervisor.email)
            if stage.company_supervisor:
                recipients.append(stage.company_supervisor.email)
        
        return recipients

# Données de référence pour le Cameroun
CAMEROON_UNIVERSITIES = [
    University("UY1", "Université de Yaoundé I", "UY1", "Yaoundé", Region.CENTRE,
               ["Informatique", "Mathématiques", "Physique", "Chimie", "Biologie"]),
    University("UY2", "Université de Yaoundé II", "UY2", "Yaoundé", Region.CENTRE,
               ["Droit", "Sciences Économiques", "Gestion", "Sciences Politiques"]),
    University("UD", "Université de Douala", "UD", "Douala", Region.LITTORAL,
               ["Génie Civil", "Génie Électrique", "Informatique", "Commerce"]),
    University("UDs", "Université de Dschang", "UDs", "Dschang", Region.OUEST,
               ["Agronomie", "Sciences Économiques", "Informatique", "Lettres"]),
    University("UN", "Université de Ngaoundéré", "UN", "Ngaoundéré", Region.ADAMAOUA,
               ["Génie Alimentaire", "Informatique", "Chimie", "Mathématiques"]),
    University("UB", "Université de Buea", "UB", "Buea", Region.SUD_OUEST,
               ["Sciences de la Santé", "Sciences Sociales", "Informatique", "Communication"]),
    University("UM", "Université de Maroua", "UM", "Maroua", Region.EXTREME_NORD,
               ["Sciences", "Lettres", "Sciences Humaines"]),
    University("UBa", "Université de Bamenda", "UBa", "Bamenda", Region.NORD_OUEST,
               ["Sciences de l'Éducation", "Sciences", "Technologie"]),
]

CAMEROON_MAJOR_CITIES = {
    Region.CENTRE: ["Yaoundé", "Mbalmayo", "Obala", "Monatélé"],
    Region.LITTORAL: ["Douala", "Edéa", "Nkongsamba", "Loum"],
    Region.OUEST: ["Bafoussam", "Dschang", "Mbouda", "Bafang"],
    Region.NORD_OUEST: ["Bamenda", "Kumbo", "Wum", "Ndop"],
    Region.SUD_OUEST: ["Buea", "Limbe", "Kumba", "Tiko"],
    Region.SUD: ["Ebolowa", "Kribi", "Sangmélima"],
    Region.EST: ["Bertoua", "Batouri", "Yokadouma"],
    Region.ADAMAOUA: ["Ngaoundéré", "Meiganga", "Tibati"],
    Region.NORD: ["Garoua", "Guider", "Poli"],
    Region.EXTREME_NORD: ["Maroua", "Kousseri", "Mokolo"]
}

print("Protocoles de Gestion de Stages - Cameroun")
print("=" * 50)
print()
print("Ce module fournit:")
print("✅ Classes de données pour étudiants, entreprises, universités")
print("✅ Protocoles de validation des stages")
print("✅ Système de notification")
print("✅ Gestion des évaluations et rapports")
print("✅ Support des 10 régions du Cameroun")
print("✅ Référentiel des universités camerounaises")
