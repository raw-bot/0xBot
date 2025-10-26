-- Migration manuelle: Ajout du champ initial_capital
-- À exécuter si alembic ne fonctionne pas

-- Vérifier si la colonne existe déjà
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name='bots' AND column_name='initial_capital'
    ) THEN
        -- Ajouter la colonne comme nullable
        ALTER TABLE bots ADD COLUMN initial_capital NUMERIC(20, 2);
        
        -- Copier les valeurs de capital vers initial_capital
        UPDATE bots SET initial_capital = capital;
        
        -- Rendre la colonne NOT NULL
        ALTER TABLE bots ALTER COLUMN initial_capital SET NOT NULL;
        
        RAISE NOTICE 'Colonne initial_capital ajoutée avec succès';
    ELSE
        RAISE NOTICE 'Colonne initial_capital existe déjà';
    END IF;
END $$;