-- Activer le bot avec l'ID spécifié
-- Exécuter avec: sqlite3 database.db < activate_bot.sql

-- Afficher l'état actuel
SELECT 'État AVANT modification:' as status;
SELECT id, name, status, model_name, capital 
FROM bots 
WHERE id = 'ed640bbf-289b-4352-ab1c-c0d8039d8e29';

-- Mettre à jour le statut
UPDATE bots 
SET status = 'active' 
WHERE id = 'ed640bbf-289b-4352-ab1c-c0d8039d8e29';

-- Afficher l'état après
SELECT 'État APRÈS modification:' as status;
SELECT id, name, status, model_name, capital 
FROM bots 
WHERE id = 'ed640bbf-289b-4352-ab1c-c0d8039d8e29';

-- Afficher tous les bots actifs
SELECT 'TOUS les bots ACTIFS:' as status;
SELECT id, name, status, model_name, capital 
FROM bots 
WHERE status = 'active';