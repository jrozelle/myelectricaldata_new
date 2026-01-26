---
globs:
  - apps/api/src/services/cache.py
  - "**/cache*.py"
---

# Chiffrement des donnees

**IMPORTANT : Pour toute modification du systeme de chiffrement, utiliser l'agent `backend-specialist` qui contient la documentation complete.**

## Rappel

- Algorithme : **Fernet** (AES-128-CBC + HMAC-SHA256)
- Cle : Derivee du `client_secret` utilisateur via SHA256
- Fichier : `apps/api/src/services/cache.py`

## Pattern obligatoire

```python
# Donnees utilisateur : TOUJOURS chiffrer
await cache_service.get(key, current_user.client_secret)
await cache_service.set(key, data, current_user.client_secret)

# Donnees publiques : raw (sans chiffrement)
await cache_service.get_raw(key)
await cache_service.set_raw(key, value)
```
