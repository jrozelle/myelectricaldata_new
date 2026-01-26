---
name: 07-commit
description: Commiter les modifications
prev_step: steps/06-docs.md
---

# Step 7/7 : Commiter

**Afficher au debut de cette etape :**

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💾 STEP 7/7 - COMMIT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**IMPORTANT : Respecter la convention Semantic Release. Voir `.claude/rules/commits.md`**

## Verification pre-commit

Avant de commiter, verifier que tout est pret :

- [ ] Lint passe (step 04)
- [ ] Code valide par l'utilisateur (step 05)
- [ ] Documentation mise a jour (step 06)
- [ ] Pas d'erreurs dans les logs

## Demander confirmation (OBLIGATOIRE)

**IMPORTANT : NE PAS commiter sans validation utilisateur.**

Utiliser `AskUserQuestion` pour demander :

```text
Question : "Souhaitez-vous commiter les modifications ?"

Options :
- "Oui, commiter" → Proceder au commit
- "Non, pas maintenant" → Terminer sans commit
```

**ATTENDRE la reponse avant de continuer.**

## Commit (Semantic Release)

Si l'utilisateur a confirme, executer le commit en respectant **Conventional Commits** :

```bash
git add <fichiers modifies>
git commit -m "<type>(<scope>): <description>

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

**Types et impact sur la version :**

| Type       | Usage                                       | Version   |
| ---------- | ------------------------------------------- | --------- |
| `feat`     | Nouvelle fonctionnalite                     | **MINOR** |
| `fix`      | Correction de bug                           | **PATCH** |
| `perf`     | Amelioration des performances               | **PATCH** |
| `docs`     | Documentation uniquement                    | Aucun     |
| `refactor` | Refactorisation sans changement fonctionnel | Aucun     |
| `style`    | Formatage, pas de changement de code        | Aucun     |
| `chore`    | Maintenance, config                         | Aucun     |

**Scope : utiliser le nom de la page (ex: `dashboard`, `tempo`, `contribute`, `admin-users`)**

## Recap Final

**Afficher a la fin :**

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎉 SKILL WEB TERMINE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Page          : <page_name>
Features      : <X> implementees
Fichiers      : <Y> modifies
Commit        : [✅ Effectue / ❌ Non demande]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
