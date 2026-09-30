# AGENT.md

Ce document guide les agents et contributeurs travaillant sur ce dépôt.

## Portée
- S’applique à l’ensemble du dépôt.
- Couvre les agents IA (Codex, Lovable, Copilot, etc.) et tout contributeur humain.

## Principes obligatoires
- Toujours lire et respecter `CONTEXT.md` avant d’écrire du code ou des documents.
- L’application est une **PWA Flutter orientée web mobile (mobile-first)**.  
  Le desktop n’est pas prioritaire pour le MVP.
- **UI 100 % en français** : traduire systématiquement tout libellé, texte, message ou placeholder.
- Respecter la **Direction Artistique Plogo** :
  - Fond blanc
  - Texte noir
  - Accents bleu `#2C75FF` et jaune `#FFB347`
  - Bleu secondaire `#3B5AFF`
  - Une seule famille d’icônes cohérente dans tout le projet.
- Backend : **Supabase** (auth, base de données, stockage).  
  Aucun secret en dur — utiliser `--dart-define` ou les fichiers de configuration IDE.

## Style et structure de code
- Composants Flutter réutilisables et isolés.
- Thèmes et styles centralisés.
- Respect des conventions de nommage et de hiérarchie de dossiers.
- Accessibilité obligatoire : contrastes suffisants, tailles lisibles, labels explicites.
- Nommez clairement les pages selon le rôle utilisateur : `owner_*` pour les propriétaires, `driver_*` pour les conducteurs.

## Bonnes pratiques IA (Codex, Lovable, etc.)
- Ne pas scanner inutilement le projet entier.  
  Limiter l’analyse aux fichiers **directement concernés** par la demande ou la modification.  
  Éviter tout parcours des dossiers `/build`, `/lib`, `/node_modules`, `/assets`, etc. sauf instruction explicite.
- Ne pas utiliser de tokens pour défaire un changement.  
  Si une modification ne fonctionne pas, **utiliser la fonction “Undo” de l’éditeur** (Ctrl+Z / Cmd+Z) plutôt qu’un rollback par prompts.
- Privilégier la **modification ciblée** plutôt que la réécriture complète d’un fichier.
- Ne pas reformater, restructurer ou renommer des fichiers si cela n’est pas explicitement demandé.
- S’assurer que chaque changement reste conforme aux règles décrites dans `CONTEXT.md`.

## Gestion des textes et accents
- Tous les labels, placeholders et champs doivent être affichés **en français**, mais **les clés et identifiants de variables, modèles ou colonnes ne doivent pas contenir d’accents ni de caractères spéciaux**.  
  Exemple :  
  - Nom de champ : `prenom` ✅ au lieu de `prénom` ❌  
  - Texte affiché : `"Prénom"` ✅ dans l’interface, via une clé `prenom_label`.
- En cas de doute, conserver des noms **compatibles UTF-8 simples** pour les structures de données et **afficher les accents uniquement dans l’UI**.
- Si les accents posent problème dans l'écriture du code alors remplacer le caractère avec accent en caractère sans accent (exemple : é devient e).

## Vérifications rapides avant PR
- Textes et labels : en français uniquement.
- Responsive mobile validé (petites largeurs).
- Aucun secret, clé ou identifiant sensible en dur.
- Couleurs, icônes et styles conformes à `CONTEXT.md`.
- Code lisible, cohérent, sans duplication inutile.
- Tests de base manuels effectués sur les principaux parcours utilisateurs.

## Références
- `CONTEXT.md` : définition produit et technique complète.  
  Ce fichier prévaut sur toute autre consigne ou hypothèse implicite.