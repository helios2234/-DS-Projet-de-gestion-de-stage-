# SYSTÈME DE GESTION ET SUIVI DES STAGES AU CAMEROUN
# ===================================================

## Description

Système distribué de gestion des stages académiques et professionnels
au Cameroun. Permet la coordination entre universités, entreprises,
étudiants et encadreurs pour le suivi complet du cycle de stage.

## Fonctionnalités Principales

✅ Création et gestion des conventions de stage
✅ Affectation des encadreurs (académique et entreprise)
✅ Soumission et évaluation des rapports de stage
✅ Système de notation avec calcul automatique des mentions
✅ Génération d'attestations de stage
✅ Statistiques et tableaux de bord
✅ Notifications en temps réel
✅ Support des 10 régions du Cameroun
✅ Gestion multi-institutions

## Structure des Fichiers

```
projet_stages_cameroun/
├── stage_service.proto          # Définition gRPC du service
├── stage_service_pb2.py         # Code protobuf généré
├── stage_service_pb2_grpc.py    # Code gRPC généré
├── stage_protocols.py           # Protocoles et classes métier
├── enhanced_stage_service.py    # Service de gestion amélioré
├── stage_server.py              # Serveur principal
├── stage_client.py              # Client pour institutions
├── config_cameroun.txt          # Configuration système
├── test_data.txt                # Données de test
└── README.txt                   # Ce fichier
```

## Installation

1. Installer Python 3.8+

2. Installer les dépendances:
   ```
   pip install grpcio grpcio-tools
   ```

3. Générer le code gRPC (optionnel si déjà généré):
   ```
   python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. stage_service.proto
   ```

## Utilisation

### Démarrer le Serveur

```bash
python stage_server.py localhost 8888
```

### Connecter une Université

```bash
python stage_client.py univ_uy1 localhost 8888
```

### Connecter une Entreprise

```bash
python stage_client.py ent_orange localhost 8888
```

## Commandes Client

| Commande                  | Description                      |
|---------------------------|----------------------------------|
| creer                     | Créer un nouveau stage           |
| liste [filtres]           | Lister les stages                |
| details <stage_id>        | Voir détails d'un stage          |
| modifier <id> <champ>     | Modifier un stage                |
| encadreur <stage_id>      | Assigner un encadreur            |
| rapport <stage_id>        | Soumettre un rapport             |
| rapports <stage_id>       | Voir les rapports d'un stage     |
| evaluer <stage_id>        | Évaluer un stage                 |
| stats                     | Afficher les statistiques        |
| attestation <stage_id>    | Générer une attestation          |
| notifications             | Voir les notifications           |
| aide                      | Afficher l'aide                  |
| quit                      | Quitter                          |

## Système de Notation

### Barème des Mentions
- A - Excellent : 16/20 et plus
- B - Très Bien : 14-15.99/20
- C - Bien : 12-13.99/20
- D - Passable : 10-11.99/20
- E - Insuffisant : moins de 10/20

### Critères d'Évaluation
- Compétences techniques : 30%
- Compétences relationnelles : 20%
- Assiduité : 15%
- Initiative : 15%
- Qualité des rapports : 20%

## Types de Stages Supportés

- ACADEMIQUE : Stage obligatoire du cursus
- PROFESSIONNEL : Stage d'insertion professionnelle
- PRE_EMPLOI : Stage pré-embauche
- RECHERCHE : Stage de recherche (Master/Doctorat)

## Types de Rapports

- HEBDOMADAIRE : Rapport de suivi hebdomadaire
- MENSUEL : Rapport mensuel d'activités
- MI_PARCOURS : Rapport intermédiaire
- FINAL : Rapport de fin de stage
- ACTIVITE : Rapport d'activité spécifique

## Régions Couvertes

1. Adamaoua (Ngaoundéré)
2. Centre (Yaoundé)
3. Est (Bertoua)
4. Extrême-Nord (Maroua)
5. Littoral (Douala)
6. Nord (Garoua)
7. Nord-Ouest (Bamenda)
8. Ouest (Bafoussam)
9. Sud (Ebolowa)
10. Sud-Ouest (Buea)

## Universités Supportées

- UY1 : Université de Yaoundé I
- UY2 : Université de Yaoundé II
- UD : Université de Douala
- UDs : Université de Dschang
- UN : Université de Ngaoundéré
- UB : Université de Buea
- UM : Université de Maroua
- UBa : Université de Bamenda

## Support

Pour toute question ou assistance technique, contactez:
- Email: support@stages-cameroun.cm
- Tél: +237 600 000 000

## Licence

Ce système est développé pour la gestion des stages au Cameroun.
Tous droits réservés.

## Version

Version: 1.0.0
Date: 2025
