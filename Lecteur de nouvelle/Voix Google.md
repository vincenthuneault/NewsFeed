# Registre des voix — Gemini 2.5 Pro TTS

> Source de vérité pour les voix disponibles, leur assignation, et les préférences de l'utilisateur.  
> Mis à jour par Claude ou l'Aftersales après chaque feedback vocal reçu.

---

## Voix actives

Une voix unique par journaliste. Changer une voix = modifier `config/config.yaml` section `voices_by_category`.

| Voix     | Journaliste                      | Catégorie DB        | Statut        | Notes utilisateur |
| -------- | -------------------------------- | ------------------- | ------------- | ----------------- |
| Achernar | Journaliste-PolitiqueCanada         | `politique_ca`      | ✅ Confirmée  | En production depuis M1 |
| Charon   | Journaliste-PolitiqueQuébec         | `politique_qc`      | ✅ Confirmée  | Validée 2026-05-18 |
| Erinome  | Journaliste-Montreal                | `evenements_mtl`    | ✅ Confirmée  | "Mieux" (testé Flash) |
| Fenrir   | Journaliste-Trending                | `youtube_trending`  | ✅ Confirmée  | Validée 2026-05-18 |
| Sulafat  | Journaliste-PolitiqueInternationale | `politique_intl`    | ✅ Confirmée  | "Parfait" (2026-05-18) |
| Kore     | Journaliste-YoutubeSub              | `youtube_subs`      | ✅ Confirmée  | Validée 2026-05-18 |
| Leda     | Journaliste-Contrecoeur             | `local_contrecoeur` | ✅ Confirmée  | "Ok" (testé Flash) |
| Puck     | Journaliste-ShortsTrending          | `viral`             | ✅ Confirmée  | Validée 2026-05-18 |

---

## Voix de remplacement (backup)

Disponibles si une voix active est rejetée. Toutes à tester avec `scripts/test_voices.py`.

| Voix        | Statut        | Notes utilisateur |
| ----------- | ------------- | ----------------- |
| Zephyr      | 🔵 À tester   | — |
| Orbit       | ❌ Non dispo  | 400 sur Gemini 2.5 Pro |
| Garux       | ❌ Non dispo  | 400 sur Gemini 2.5 Pro (fonctionne seulement sur Flash) |
| Ganymede    | ❌ Non dispo  | 400 sur Gemini 2.5 Pro |
| Despina     | 🔵 À tester   | — |
| Callirrhoe  | 🔵 À tester   | — |
| Aoede       | 🔵 À tester   | — |
| Fenrir      | 🔵 À tester   | — |

> **Légende** : ✅ Confirmée · 🔵 À tester · ❌ Rejetée

---

## Notes utilisateur par voix

> Section tenue à jour par l'Aftersales à chaque cycle où un commentaire vocal est reçu.
> Format : `YYYY-MM-DD — [Voix] — commentaire brut — décision`.

*(Aucun feedback enregistré — les 4 nouvelles voix sont à tester.)*

---

## Comment changer une voix

1. Écouter les candidats avec `python scripts/test_voices.py`
2. Identifier la nouvelle voix souhaitée
3. Modifier `config/config.yaml` :
   ```yaml
   voices_by_category:
     categorie_concernee: "NouvelleVoix"  # une ligne à changer
   ```
4. Ajouter le prompt de style dans `style_prompts_by_voice` si c'est une nouvelle voix
5. Mettre à jour ce registre (déplacer l'ancienne voix en backup, marquer la nouvelle comme active)
6. Vider le cache audio de la catégorie si nécessaire :
   ```bash
   # Les MP3 sont cachés par hash URL — ils ne seront pas regénérés automatiquement
   # Pour forcer : supprimer les fichiers static/audio/*.mp3 de la catégorie concernée
   ```

---

## Procédure de test d'une nouvelle voix

```bash
# Tester toutes les voix candidates (génère un MP3 de 15 secondes par voix)
python scripts/test_voices.py

# Tester une voix spécifique
python scripts/test_voices.py --voice Charon

# Écouter le résultat
ls static/audio/voice_tests/
```

---

## Références

- [[Agents/Narrateur]] — prompts de style et assignation active
- [[Agents/Aftersales]] — traitement des feedbacks vocaux

#voix #tts #registre #gemini
