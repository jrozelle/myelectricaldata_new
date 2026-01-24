---
name: 04-lint
description: Verifier la qualite du code
prev_step: steps/03-execute.md
next_step: steps/05-validate.md
---

# Step 4/7 : Lint et Qualite du Code

**Afficher au debut de cette etape :**

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔍 STEP 4/7 - LINT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**IMPORTANT : Cette etape est OBLIGATOIRE avant la validation utilisateur.**

## Executer le lint

```bash
make lint
```

Cette commande execute le lint sur le frontend ET le backend.

## Corriger les erreurs

**Si des erreurs sont detectees :**

1. Analyser les erreurs affichees
2. Corriger chaque erreur
3. Re-executer `make lint` jusqu'a ce qu'il passe

## Recap Step 4

**Afficher a la fin de cette etape :**

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ STEP 4/7 - LINT TERMINE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Resultat : [✅ Passe / ❌ Erreurs corrigees]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
→ Passage au Step 5 : Validation
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**NE PAS passer a l'etape suivante si des erreurs persistent.**
